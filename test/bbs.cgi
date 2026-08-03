#!/usr/bin/perl
# =========================================================================
#  bbs.cgi - 新規スレッド作成 / レス投稿を処理する
# =========================================================================
use strict;
use CGI::Carp qw(fatalsToBrowser);
use warnings;
use CGI;
use FindBin qw($Bin);
use lib "$Bin/lib";
use BBSCommon qw(
    escape_html read_setting valid_bbs_id valid_key now_timecol
    read_lines_locked write_lines_locked append_line_locked
    load_subjects save_subjects render_board_html html_header
);

my $q = CGI->new;

# -------------------------------------------------------------------
# 共通エラー表示
# -------------------------------------------------------------------
sub error_exit {
    my ($message) = @_;
    print html_header();
    print <<"EOF";
<html><head><title>エラー</title><meta charset="Shift_JIS"></head>
<body>
<b>エラー: $message</b><br>
<br>
[<a href="../">トップに戻る</a>]
</body></html>
EOF
    exit;
}

# -------------------------------------------------------------------
# POST 以外は受け付けない
# -------------------------------------------------------------------
if (uc($ENV{REQUEST_METHOD} || '') ne 'POST') {
    error_exit('不正なリクエストです。');
}

# -------------------------------------------------------------------
# 入力取得・バリデーション（ここで板ID/キーを検証しないと
# ディレクトリトラバーサルでサーバ上の任意ファイルを操作されうる）
# -------------------------------------------------------------------
my $bbs     = $q->param('bbs')     || '';
my $key     = $q->param('key')     || '';
my $subject = $q->param('subject') || '';
$subject =~ s/^\s+|\s+$//g;

error_exit('掲示板IDが不正です。') unless valid_bbs_id($bbs);
error_exit('スレッドキーが不正です。') if ($key ne '' && !valid_key($key));

my $dir = "../$bbs";
error_exit('指定された掲示板は存在しません。') unless -d $dir;
mkdir "$dir/dat" unless -d "$dir/dat";

my %setting = read_setting("$dir/setting.txt");
my $max_threads = $setting{BBS_MAX_THREADS} || 100;
my $max_res     = $setting{BBS_RES_MAX}     || 1000;
my $noname      = $setting{BBS_NONAME_NAME} || '名無しさん';

my $name = escape_html($q->param('FROM'));
$name = $noname unless length $name;
my $mail = escape_html($q->param('mail')) || '';

my $body = escape_html($q->param('MESSAGE'));
$body = '' unless defined $body;
$body =~ s/\r\n/\n/g;
$body =~ s/\r/\n/g;
$body =~ s/\x{3000}/&#x3000;/g;   # 全角スペース
$body =~ s/\n/<br>/g;
$body =~ s/^(?:<br>)+//;
$body =~ s/(?:<br>)+$//;

error_exit('本文を入力してください。') unless length $body;
error_exit('本文が長すぎます。') if length($body) > 4000;
error_exit('名前が長すぎます。') if length($name) > 100;

my $ip = $ENV{REMOTE_ADDR} || '0.0.0.0';
my $timecol = now_timecol($ip);

my $is_new_thread = (length $subject) ? 1 : 0;

# =====================================================================
#  新規スレッド作成
# =====================================================================
if ($is_new_thread) {
    error_exit('スレッドタイトルが長すぎます。') if length($subject) > 100;

    # key未指定なら現在時刻から生成。衝突する場合は1秒ずつずらす。
    if (!length $key) {
        $key = time();
        while (-e "$dir/dat/$key.dat") {
            $key++;
        }
    }
    my $dat = "$dir/dat/$key.dat";
    error_exit('同じキーのスレッドが既に存在します。') if -e $dat;

    my $first_line = join('<>', $name, $mail, $timecol, $body, $subject) . "\n";
    write_lines_locked($dat, '>', $first_line);

    my $subject_file = "$dir/subject.txt";
    my $subjects = load_subjects($subject_file);
    unshift @$subjects, { file => "$key.dat", title => $subject, count => 1 };

    # 上限を超えたスレッドは一覧から外す（dat落ち）
    if (scalar(@$subjects) > $max_threads) {
        $#$subjects = $max_threads - 1;
    }
    save_subjects($subject_file, $subjects);

    my $html = render_board_html(dir => $dir, bbs => $bbs, setting => \%setting, subjects => $subjects);
    write_lines_locked("$dir/index.html", '>', $html);

    print "Status: 302 Found\n";
    print html_header();
    print <<"EOF";
<html><head><title>スレ立て完了</title><meta charset="Shift_JIS">
<meta http-equiv="refresh" content="2;URL=../$bbs/"></head>
<body>
<b>スレッドを立てました。</b><br>
画面を切り替えるまでしばらくお待ち下さい。<br><br>
[<a href="../$bbs/">掲示板に戻る</a>]
[<a href="read.cgi/$bbs/$key">スレッドを見る</a>]
</body></html>
EOF
    exit;
}

# =====================================================================
#  レス投稿
# =====================================================================
error_exit('スレッドキーが指定されていません。') unless length $key;
my $dat = "$dir/dat/$key.dat";
error_exit('指定されたスレッドが見つかりません。') unless -e $dat;

my @lines = read_lines_locked($dat);
my $no = scalar(@lines) + 1;

# レス数上限チェック（dat落ち）
if (scalar(@lines) >= $max_res) {
    my $subject_file = "$dir/subject.txt";
    my $subjects = load_subjects($subject_file);
    @$subjects = grep { $_->{file} ne "$key.dat" } @$subjects;
    save_subjects($subject_file, $subjects);

    print html_header();
    print <<"EOF";
<html><head><title>エラー</title><meta charset="Shift_JIS"></head>
<body>
<b>このスレッドは $max_res レスを超えたため書込できません。(dat落ち)</b><br><br>
[<a href="../$bbs/">掲示板に戻る</a>]
</body></html>
EOF
    exit;
}

my $newline = join('<>', $name, $mail, $timecol, $body, '') . "\n";
append_line_locked($dat, $newline);

my $subject_file = "$dir/subject.txt";
my $subjects = load_subjects($subject_file);

my ($entry) = grep { $_->{file} eq "$key.dat" } @$subjects;
if (!$entry) {
    # subject.txt に無い（dat落ち後の再投稿等）場合は末尾に補完
    $entry = { file => "$key.dat", title => '無題', count => 0 };
    push @$subjects, $entry;
}
$entry->{count} = $no;

my $is_sage = ($mail =~ /sage/i) ? 1 : 0;
unless ($is_sage) {
    # age: 該当スレッドを先頭に移動
    @$subjects = ($entry, grep { $_ != $entry } @$subjects);
}
save_subjects($subject_file, $subjects);

my $html = render_board_html(dir => $dir, bbs => $bbs, setting => \%setting, subjects => $subjects);
write_lines_locked("$dir/index.html", '>', $html);

# =====================================================================
# Push通知（購読者に一度だけ通知）
# =====================================================================
my $sub_file = "$dir/dat/$key.sub.pl";   # JSONではなく .pl にする
my $notify_file = "$dir/dat/$key.notify";

my $last = 0;
$last = do { local(@ARGV,$/) = $notify_file; <> } if -e $notify_file;

if ($no > $last && -e $sub_file) {

    # JSON.pm は使わない
    my $subs = do $sub_file;   # Perl構造として読み込む

    foreach my $s (@$subs) {
        # JSONエンコードも不要
        my $tmp = "$dir/dat/sub.tmp.pl";
        open my $fh, '>', $tmp;
        print $fh Data::Dumper->new([$s])->Terse(1)->Dump;
        close $fh;

        system("perl push_send.pl $tmp");
    }

    open my $nf, '>', $notify_file;
    print $nf $no;
    close $nf;
}




print "Status: 302 Found\n";
print html_header();
print <<"EOF";
<html><head><title>書き込み完了</title><meta charset="Shift_JIS">
<meta http-equiv="refresh" content="2;URL=read.cgi/$bbs/$key"></head>
<body>
<b>書き込みが終わりました。</b><br>
画面を切り替えるまでしばらくお待ち下さい。<br><br>
[<a href="../$bbs/">掲示板に戻る</a>]
[<a href="read.cgi/$bbs/$key">スレッドに戻る</a>]
</body></html>
EOF
exit;
