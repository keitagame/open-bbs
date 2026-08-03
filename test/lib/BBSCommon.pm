package BBSCommon;

# =========================================================================
#  BBSCommon.pm
#  bbs.cgi / read.cgi で共有する処理をまとめたモジュール。
#  - HTMLエスケープ
#  - setting.txt 読み込み
#  - 板ID / スレッドキーのバリデーション（ディレクトリトラバーサル対策）
#  - dat / subject.txt の排他制御つき読み書き
#  - 本文のリンク化（URL・画像・>>アンカー）
#  - 板トップ(index.html)のHTML生成
# =========================================================================

use strict;
use warnings;
use Fcntl qw(:flock);
use Digest::MD5 qw(md5_hex);
use Exporter 'import';

our @EXPORT_OK = qw(
    escape_html
    read_setting
    valid_bbs_id
    valid_key
    now_timecol
    read_lines_locked
    write_lines_locked
    append_line_locked
    load_subjects
    save_subjects
    linkify_body
    render_board_html
    html_header
);

# ------------------------------------------------------------------
# HTMLエスケープ
# ------------------------------------------------------------------
sub escape_html {
    my $text = shift;
    return '' unless defined $text;
    $text =~ s/&/&amp;/g;
    $text =~ s/</&lt;/g;
    $text =~ s/>/&gt;/g;
    $text =~ s/"/&quot;/g;
    $text =~ s/'/&#39;/g;
    return $text;
}

# ------------------------------------------------------------------
# setting.txt ( KEY=VALUE ) を読み込む
# ------------------------------------------------------------------
sub read_setting {
    my ($setting_path) = @_;
    my %config;

    if (-e $setting_path) {
        open my $fh, '<', $setting_path or return %config;
        while (my $line = <$fh>) {
            chomp $line;
            next if $line =~ /^\s*#/ || $line =~ /^\s*$/;
            my ($key, $val) = split(/=/, $line, 2);
            if (defined $key && defined $val) {
                $key =~ s/^\s+|\s+$//g;
                $val =~ s/^\s+|\s+$//g;
                $config{$key} = $val;
            }
        }
        close $fh;
    }
    return %config;
}

# ------------------------------------------------------------------
# 板ID / スレッドキーのバリデーション
# （これが無いとパス操作でサーバ上の任意ファイルにアクセスされ得る）
# ------------------------------------------------------------------
sub valid_bbs_id {
    my ($bbs) = @_;
    return 0 unless defined $bbs && length $bbs;
    return $bbs =~ /^[A-Za-z0-9_\-]+$/ ? 1 : 0;
}

sub valid_key {
    my ($key) = @_;
    return 0 unless defined $key && length $key;
    return $key =~ /^\d+$/ ? 1 : 0;
}

# ------------------------------------------------------------------
# "YYYY/MM/DD(曜) HH:MM:SS ID:XXXXXXXX" 形式の時刻文字列と
# IDの元になる日付(YYYYMMDD)を返す
# ------------------------------------------------------------------
sub now_timecol {
    my ($ip) = @_;
    $ip ||= '0.0.0.0';
    my @t = localtime();
    my $time = sprintf(
        '%04d/%02d/%02d(%s) %02d:%02d:%02d',
        $t[5] + 1900, $t[4] + 1, $t[3],
        (qw(日 月 火 水 木 金 土))[$t[6]],
        $t[2], $t[1], $t[0]
    );
    my $date = sprintf('%04d%02d%02d', $t[5] + 1900, $t[4] + 1, $t[3]);
    my $id = uc substr(md5_hex("$ip$date"), 0, 8);
    return "$time ID:$id";
}

# ------------------------------------------------------------------
# ファイルの排他制御つき入出力
# ------------------------------------------------------------------
sub read_lines_locked {
    my ($path) = @_;
    return () unless -e $path;
    open my $fh, '<', $path or return ();
    flock($fh, LOCK_SH);
    my @lines = <$fh>;
    close $fh;
    return @lines;
}

# 上書き保存（新規作成 or 全置換）。$mode は '>' か '>>'
sub write_lines_locked {
    my ($path, $mode, @lines) = @_;
    open my $fh, $mode, $path or die "Cannot open $path: $!";
    flock($fh, LOCK_EX);
    print $fh @lines;
    close $fh;
    return 1;
}

sub append_line_locked {
    my ($path, $line) = @_;
    return write_lines_locked($path, '>>', $line);
}

# ------------------------------------------------------------------
# subject.txt の読み書き
# 戻り値/引数は [ { file => '123.dat', title => 'スレタイ', count => 3 }, ... ]
# ------------------------------------------------------------------
sub load_subjects {
    my ($path) = @_;
    my @out;
    for my $line (read_lines_locked($path)) {
        chomp $line;
        next unless length $line;
        my ($file, $title_with_count) = split(/<>/, $line, 2);
        next unless defined $file && defined $title_with_count;
        my $count = 1;
        my $title = $title_with_count;
        if ($title_with_count =~ /^(.*?)\s*\((\d+)\)\s*$/) {
            $title = $1;
            $count = $2;
        }
        push @out, { file => $file, title => $title, count => $count };
    }
    return \@out;
}

sub save_subjects {
    my ($path, $subjects) = @_;
    my @lines = map { sprintf("%s<>%s (%d)\n", $_->{file}, $_->{title}, $_->{count}) } @$subjects;
    write_lines_locked($path, '>', @lines);
    return 1;
}

# ------------------------------------------------------------------
# 本文のリンク化: URL / 画像URL / >>アンカー
# $anchor_tmpl は sprintf テンプレート。%d が2箇所あるレス番号用テンプレート。
#   例) read.cgi 内部から: '?anchor=%d#res%d'
#       板トップから他スレへ: '../test/read.cgi/BBSID/THREADKEY/?anchor=%d#res%d'
# 呼び出し前提: $body はすでに escape_html 済み、改行は <br> に変換済み。
# ------------------------------------------------------------------
sub linkify_body {
    my ($body, $anchor_tmpl) = @_;
    return '' unless defined $body;

    $body =~ s{(https?://[\w.\-_/:%#?=&;]+)}{
        my $url = $1;
        if ($url =~ /\.(jpe?g|png|gif|webp)$/i) {
            qq{<a href="$url" target="_blank"><img src="$url" style="max-width:50%;height:auto;display:block;"></a>};
        } else {
            qq{<a href="$url" target="_blank">$url</a>};
        }
    }gie;

    $body =~ s{&gt;&gt;(\d+)}{
        my $n = $1;
        my $href = sprintf($anchor_tmpl, $n, $n);
        qq{<a href="$href">&gt;&gt;$n</a>};
    }ge;

    return $body;
}

# ------------------------------------------------------------------
# 共通HTMLヘッダ
# ------------------------------------------------------------------
sub html_header {
    return "Content-Type: text/html; charset=Shift_JIS\n\n";
}

# ------------------------------------------------------------------
# 板トップ(index.html)のHTMLを1つの文字列として組み立てる。
# bbs.cgi の新規スレ作成／レス投稿どちらからも同じ関数を呼ぶことで
# コードの二重化を無くしている。
# ------------------------------------------------------------------
sub render_board_html {
    my (%a) = @_;
    my $dir      = $a{dir};
    my $bbs      = $a{bbs};
    my $setting  = $a{setting};
    my $subjects = $a{subjects};

    my $thread_list_html = '';
    my $threads_html      = '';

    for my $s (@$subjects) {
        my ($th_key) = $s->{file} =~ /^(\d+)\.dat$/;
        next unless $th_key;
        my $title_with_count = sprintf('%s (%d)', $s->{title}, $s->{count});

        $thread_list_html .= sprintf(
            '<a target="_top" href="../test/read.cgi/%s/%s/">%s</a>' . "\n",
            $bbs, $th_key, $title_with_count
        );

        my $target_dat = "$dir/dat/$s->{file}";
        next unless -e $target_dat;

        my @dat_lines = read_lines_locked($target_dat);
        my $responses_html = '';
        my $res_num = 1;
        my $anchor_tmpl = "../test/read.cgi/$bbs/$th_key/?anchor=%d#res%d";

        for my $res (@dat_lines) {
            chomp $res;
            next unless length $res;
            my ($r_name, $r_mail, $r_time, $r_body) = split(/<>/, $res);
            $r_name //= '';
            $r_body //= '';

            my $name_disp = $r_mail
                ? qq(<a href="mailto:$r_mail"><b>$r_name</b></a>)
                : qq(<b><font color="green">$r_name</font></b>);

            $r_body =~ s{<br>}{<br>}g;
            $r_body = linkify_body($r_body, $anchor_tmpl);

            $responses_html .= sprintf(
                "<dt>%d ：%s：%s</dt><dd> %s <br><br></dd>\n",
                $res_num, $name_disp, $r_time // '', $r_body
            );
            $res_num++;
        }

        $threads_html .= <<"THREAD_END";
<div class="thread-container">
<dl>
<table align="center" border="1" width="97%" cellpadding="2" cellspacing="7" bgcolor="#F0F0F0" style="word-break: break-all; word-wrap: break-word;"><tr><td>
<button onclick="subscribePush('$bbs', '$th_key')">
    このスレを通知購読する
</button><br>
<script src="/subscribe.js"></script>

<font color="red" size="5">$title_with_count</font>
<br><br>
$responses_html
</dl>
<br><br>
<form action="../test/bbs.cgi" method="post">
<input name="bbs" type="hidden" value="$bbs">
<input name="key" type="hidden" value="$th_key">
<button type="submit">書き込む</button>
<label for="username">名前：</label>
<input type="text" id="username" width="100" name="FROM" placeholder="名無し">
<label for="useremail">メアド：</label>
<input type="text" id="useremail" name="mail">
<br><br>
<textarea id="usermessage" name="MESSAGE" rows="5" cols="65" maxlength="4000" required></textarea>
</form>
<a href="."><strong>リロード</strong></a>&ensp;<a href="."><strong>板のトップ</strong></a>
</td></tr></table><br>
THREAD_END
    }

    $thread_list_html ||= "現在スレッドはありません。\n";

    my $bbs_title = escape_html($setting->{BBS_TITLE} // $bbs);

    my $html = <<"EOF";
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
 "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<meta charset="Shift_JIS">
<title>$bbs</title>
<style type="text/css">
body {
    background-image: url("ba.gif");
    background-repeat: repeat;
    background-position: left top;
    background-attachment: scroll;
}
</style>
</head>
<body>
<div align="center"><img src="banana.gif"></div>
<table align="center" bgcolor="#C4FFCA" border="1" width="97%" cellpadding="2" cellspacing="7">
<tr><td>
<font size="4">&emsp;<strong>$bbs_title</strong></font>
<br><br><br><br><br><br>
</td></tr>
<tr><td align="center"><a target="_top" href="https://shinte.tech"><small>トップへ</small></a>&emsp;<a href="/test/headline.cgi?bbs=$bbs"><small>ヘッドライン</small></a></td></tr>
</table>
<br>
<table align="center" bgcolor="#C4FFCA" border="1" height="150" width="97%" cellpadding="2" cellspacing="7">
<tr><td>
<iframe width="100%" height="150" src="rtview.html" name="rtview"></iframe></td></tr></table>
<br>
<table align="center" bgcolor="#C4FFCA" border="1" width="97%" cellpadding="2" cellspacing="7">
<tr><td>
$thread_list_html
</td></tr>
</table>
$threads_html
<table align="center" bgcolor="#C4FFCA" border="1" width="97%" cellpadding="2" cellspacing="7">
<tr><td>
<div>新規スレ立て</div>
<form action="../test/bbs.cgi" method="post">
<input name="bbs" type="hidden" value="$bbs">
<button type="submit">スレ立て</button>
<label for="subject">名前（スレ）：</label>
<input type="text" id="subject" width="100" name="subject" placeholder="スレタイ" maxlength="100" required>
<label for="name2">名前：</label>
<input type="text" id="name2" width="100" name="FROM" placeholder="名無し">
<label for="useremail2">メアド：</label>
<input type="text" id="useremail2" name="mail">
<br><br>
<textarea id="usermessage2" name="MESSAGE" rows="5" cols="65" maxlength="4000" required></textarea>
</form>
</td></tr>
</table><br>
<div align="center"><script src="https://adm.shinobi.jp/s/505bc828d288f41d560a3369733fc6c5"></script></div>
</body>
</html>
EOF

    return $html;
}

1;
