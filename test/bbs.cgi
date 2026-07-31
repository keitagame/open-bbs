#!/usr/bin/perl
use warnings;
use CGI;
use Digest::MD5 qw(md5_hex);
my $q = CGI->new;

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

sub read_setting {
    my ($setting_path) = @_;
    my %config;

    if (-e $setting_path) {
        open my $fh, "<", $setting_path or return %config;
        while (my $line = <$fh>) {
            chomp $line;
            # 空行やコメント行（#から始まる行）をスキップ
            next if $line =~ /^\s*#/ || $line =~ /^\s*$/;
            
            # KEY=VALUE 形式を分割
            my ($key, $val) = split(/=/, $line, 2);
            if (defined $key && defined $val) {
                # 前後の空白を除去
                $key =~ s/^\s+|\s+$//g;
                $val =~ s/^\s+|\s+$//g;
                $config{$key} = $val;
            }
        }
        close $fh;
    }

    return %config;
}

my $bbs  = $q->param('bbs');
my $key  = $q->param('key');
my $subject = $q->param('subject') || 'none';
my $dir = "../$bbs";
my $dat = "$dir/dat/$key.dat";

my %setting = read_setting("$dir/setting.txt");
my $name = escape_html($q->param('FROM')) || $setting{'BBS_NONAME_NAME'};
my $mail = escape_html($q->param('mail')) || '';
my $body = escape_html($q->param('MESSAGE')) || '';
# 改行コード統一

$body =~ s/\r\n/\n/g;
$body =~ s/\r/\n/g;
$body =~ s/ / /g;
$body =~ s/\x{3000}/&#x3000;/g;

$body =~ s/\r\n/\n/g;
$body =~ s/\r/\n/g;

$body =~ s/ / /g;

# 全角スペース（U+3000）を &#x3000; に変換
$body =~ s/\x{3000}/&#x3000;/g;

# 複数行を行内に埋め込む（\n を <br> に置換）
$body =~ s/\n/<br>/g;





my $is_new_thread = ($subject ne 'none') ? 1 : 0;

if ($is_new_thread) {
    # key が指定されていない場合は現在時刻（Epoch seconds）から生成
    if (!$key) {
        $key = int(time());
    }

    my $dat = "$dir/dat/$key.dat";

    # 時刻表記の生成
    my @t = localtime();
    my $time = sprintf(
        "%04d/%02d/%02d(%s) %02d:%02d:%02d",
        $t[5]+1900, $t[4]+1, $t[3],
        (qw(日 月 火 水 木 金 土))[$t[6]],
        $t[2], $t[1], $t[0]
    );
    my $ip = $ENV{'REMOTE_ADDR'} || "0.0.0.0";
    my $date = sprintf("%04d%02d%02d", $t[5]+1900, $t[4]+1, $t[3]);
    my $id = uc substr(md5_hex("$ip$date"), 0, 8);
    my $timecol = "$time ID:$id";

    # 新規 dat 作成（1レス目の末尾にスレッド名を付与する2ch互換形式）
    my $first_line = join("<>",
        $name,
        $mail,
        $timecol,
        $body,
        $subject # 1レス目のみ5番目の要素にスレッド名が入る
    ) . "\n";

    open my $fh, ">", $dat or die "Cannot create dat: $!";
    print $fh $first_line;
    close $fh;

    # subject.txt の読み込みと先頭への挿入
    my $subject_file = "$dir/subject.txt";
    my @subjects;
    if (-e $subject_file) {
        open my $sfh, "<", $subject_file;
        @subjects = <$sfh>;
        close $sfh;
    }

    # 一番上（先頭）に新しいスレッドを追加（レス数は 1）
    unshift @subjects, "$key.dat<>$subject (1)\n";

    # subject.txt の更新保存
    # --- [追加] 最大スレッド数の上限判定とdat落ち処理 ---
    my $max_threads = $setting{'BBS_MAX_THREADS'} || 100; # setting.txt等で未設定なら100スレを上限に設定
    if (scalar(@subjects) > $max_threads) {
        # 上限を超えた分（配列の末尾＝一番古いスレッド）を切り捨てることでdat落ちさせる
        $#subjects = $max_threads - 1;
    }
    # --------------------------------------------------
    open my $sfh2, ">", $subject_file or die "Cannot write subject.txt: $!";
    foreach my $line (@subjects) {
        $line =~ s/\r\n/\n/g;
        $line =~ s/\r/\n/g;
        $line =~ s/\n$//;
        print $sfh2 $line . "\n";
    }
    close $sfh2;

    # スレッド作成後のリダイレクト
    print "Status: 302 Found\n";
    
    

print "Content-Type: text/html; charset=Shift_JIS\n";
# --- [追加] 新規スレッド作成時の index.html 再生成処理 ---
    my $thread_list_html = "";
    foreach my $line (@subjects) {
        chomp $line;
        next unless $line;
        my ($file, $title_with_count) = split(/<>/, $line, 2);
        next unless ($file && $title_with_count);
        my ($th_key) = $file =~ /^(\d+)\.dat$/;
        next unless $th_key;
       
        $thread_list_html .= sprintf(
            '<a target="_blank" href="../test/read.cgi/%s/%s/">%s</a></li>' . "\n",
            $bbs,
            $th_key,
            $title_with_count
        );
    }
    if (!$thread_list_html) {
        $thread_list_html = "<li>現在スレッドはありません。</li>\n";
    }

    my $threads_html = "";
    foreach my $line (@subjects) {
        chomp $line;
        next unless $line;

        my ($file, $title_with_count) = split(/<>/, $line, 2);
        next unless ($file && $title_with_count);

        my ($th_key) = $file =~ /^(\d+)\.dat$/;
        next unless $th_key;

        my $target_dat = "$dir/dat/$file";
        next unless -e $target_dat;

        open my $dfh, "<", $target_dat or next;
        my @dat_lines = <$dfh>;
        close $dfh;

        my $responses_html = "";
        my $res_num = 1;

        foreach my $res (@dat_lines) {
            chomp $res;
            next unless $res;
            my ($r_name, $r_mail, $r_time, $r_body) = split(/<>/, $res);

            my $name_disp = $r_name;
            if ($r_mail) {
                $name_disp = qq(<a href="mailto:$r_mail"><b>$r_name</b></a>);
            } else {
                $name_disp = qq(<b><font color="green">$r_name</font></b>);
            }
            $r_body =~ s/\r?\n/<br>&emsp;&emsp;&ensp;/g;
            $r_body =~ s/\r?<br>/<br>/g;
            $r_body =~ s{(https?://[\w\.\-_/:%#\?\=&]+)}{<a href="$1" target="_blank">$1</a>}gi;
            $r_body =~ s{>>(\d+)}{<a target="_blank" href="../test/read.cgi/$bbs/$th_key/?anchor=$1#res$1">>>$1</a>}g;
            $r_body =~ s{&gt;&gt;(\d+)}{<a target="_blank" href="../test/read.cgi/$bbs/$th_key/?anchor=$1#res$1">>>$1</a>}g;

            $responses_html .= sprintf(
                '<dt>%d ：%s：%s</dt><dd> %s <br><br></dd>' . "\n",
                $res_num,
                $name_disp,
                $r_time,
                $r_body
            );
            $res_num++;
        }

        $threads_html .= <<"THREAD_END";
<div class="thread-container">
<dl>
<table align="center" border="1" width="97%" cellpadding="2" cellspacing="7" bgcolor="#F0F0F0" style="word-break: break-all; word-wrap: break-word;"><tr><td>
<font color="red" size="5">$title_with_count</font>
<br><br>
$responses_html
</dl>
<br><br>
<form action="/test/bbs.cgi" method="post">
<input name="bbs" type="hidden" value="$bbs">
<input name="key" type="hidden" value="$th_key">
<button type="submit">書き込む</button>
<label for="username">名前：</label>
<input type="text" id="username" width="100" name="FROM" placeholder="名無し"> 
<label for="useremail">メアド：</label>
<input type="text" id="useremail" name="mail"> 
<br><br>
<textarea id="usermessage" name="MESSAGE" rows="5" cols="65" required></textarea>
</form>
<a href="."><strong>リロード</strong></a>&ensp;<a href="."><strong>板のトップ</strong></a>
</td></tr></table><br>
THREAD_END
    }

    my $filename = "$dir/index.html";
    my $html_content = <<"EOF";
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
<div align="center"><img src="banana.gif"/></div>
<table align="center" bgcolor="#C4FFCA" border="1" width="97%" cellpadding="2" cellspacing="7">
<tr>
<td>
<font size="4">&emsp;<strong>$setting{'BBS_TITLE'}</strong></font>
<br>
<br>
<br>
<br>
<br>
<br></td>
</tr>
<tr>
<td align="center"><a href="m"><small>書き込む前に読んでね</small></a>&emsp;<a href="k"><small>ガイドライン</small></a></td>
</tr>
</table>
<br>
<table align="center" bgcolor="#C4FFCA" border="1" width="97%" cellpadding="2" cellspacing="7">
<tr>
<td>
$thread_list_html
</td>
</tr>
</table>
$threads_html
<table align="center" bgcolor="#C4FFCA" border="1" width="97%" cellpadding="2" cellspacing="7">
<tr>
<td>
<div>新規スレ立て</div>
<form action="/test/bbs.cgi" method="post">
<input name="bbs" type="hidden" value="$bbs">
<button type="submit">スレ立て</button>
<label for="username">名前（スレ）：</label>
<input type="text" id="username" width="100" name="subject" placeholder="スレタイ">
<label for="name">名前：</label>
<input type="text" id="name" width="100" name="FROM" placeholder="名無し">  
<label for="useremail">メアド：</label>
<input type="text" id="useremail" name="mail"> 
<br><br>
<textarea id="usermessage" name="MESSAGE" rows="5" cols="65" required></textarea>
</form>
</td>
</tr>
</body>
</html>
EOF

    open(my $html_fh, '>', $filename);
    print $html_fh $html_content;
    close($html_fh);
    # --------------------------------------------------
print "Refresh: 2; URL=../$bbs/\n"; 
print "\n"; # ヘッダーとボディを区切る空行

print << "EOF";
<html>
<head>
<title>書き込み完了</title>
<meta charset=Shift_JIS">

</head>
<body>

<b>書き込みが終わりました。</b><br>
画面を切り替えるまでしばらくお待ち下さい。<br>
<br>
[<a href="../$bbs/">掲示板に戻る</a>] 
[<a href="../read.cgi/$bbs/$key">スレッドに戻る</a>]

</body>
</html>
EOF
    exit;
}

open my $fh, "<", $dat or die "Cannot open dat: $!";
my @lines = <$fh>;
close $fh;

my $no = scalar(@lines) + 1;
# --- [追加] レス数上限チェック（dat落ち判定） ---
    my $max_res = $setting{'BBS_RES_MAX'} || 1000; # 規定レス数（デフォルト1000）
    if (scalar(@lines) >= $max_res) {
        # 1. subject.txt から該当スレッドを削除（一覧から消してdat落ち状態にする）
        my $subject_file = "$dir/subject.txt";
        if (-e $subject_file) {
            open my $sfh, "<", $subject_file;
            my @sub_lines = <$sfh>;
            close $sfh;

            open my $sfh2, ">", $subject_file;
            foreach my $s_line (@sub_lines) {
                print $sfh2 $s_line unless $s_line =~ /^\Q$key.dat\E<>/;
            }
            close $sfh2;
        }

        # 2. 画面にストップメッセージを表示して処理中断
        print "Content-Type: text/html; charset=Shift_JIS\n\n";
        print << "EOF";
<html>
<head><title>エラー</title><meta charset="Shift_JIS"></head>
<body>
<b>このスレッドは $max_res レスを超えたため書込できません。(dat落ち)</b><br>
<br>
[<a href="../$bbs/">掲示板に戻る</a>]
</body>
</html>
EOF
        exit;
    }
   
my @t = localtime();
my $time = sprintf(
    "%04d/%02d/%02d(%s) %02d:%02d:%02d",
    $t[5]+1900, $t[4]+1, $t[3],
    (qw(日 月 火 水 木 金 土))[$t[6]],
    $t[2], $t[1], $t[0]
);
my $ip = $ENV{'REMOTE_ADDR'} || "0.0.0.0";

my ($sec,$min,$hour,$mday,$mon,$year) = localtime;
my $date = sprintf("%04d%02d%02d", $year + 1900, $mon + 1, $mday);

my $id = uc substr(md5_hex("$ip$date"), 0, 8);

my $timecol = "$time ID:$id";

my @c = split(/<>/, $lines[0]);



my $newline = join("<>",
    $name,
    $mail,
    $timecol,
    $body,
    ""
) . "\n";

open my $fh2, ">>", $dat or die "Cannot write dat: $!";
print $fh2 $newline;
close $fh2;


my $subject = "$dir/subject.txt";
my @subjects;

if (-e $subject) {
    open my $sfh, "<", $subject;
    @subjects = <$sfh>;
    close $sfh;
}
my $title = '';
# --- [追加] 最大スレッド数の上限判定とdat落ち処理 ---

# --------------------------------------------------
foreach my $line (@subjects) {
    chomp $line;
    my ($dat, $t) = split(/<>/, $line, 2);
    next unless $t;

    if ($dat eq "$key.dat") {

        # ★ ここで既存の (数字) を除去する
        $t =~ s/\s*\(\d+\)$//;

        $title = $t;
        last;
    }
}

$title ||= '無題';


my @newsubjects;

my $is_sage = ($mail =~ /sage/i) ? 1 : 0;


if ($is_sage) {
    
    foreach my $line (@subjects) {
        if ($line =~ /^$key\.dat<>\Q$title\E/) {
            push @newsubjects, "$key.dat<>$title ($no)\n";
        } else {
            push @newsubjects, $line;
        }
    }
} else {
    
    push @newsubjects, "$key.dat<>$title ($no)\n";

    foreach my $line (@subjects) {
        next if $line =~ /^$key\.dat<>\Q$title\E/;
        push @newsubjects, $line;
    }
}

open my $sfh2, ">", $subject;
# print $sfh2 @newsubjects;
open my $sfh2, ">", $subject or die "Cannot write subject.txt: $!";

print "Status: 302 Found\n";

print "Content-Type: text/html; charset=Shift_JIS\n";
print "Refresh: 2; URL=read.cgi/$bbs/$key\n"; 
print "\n"; # ヘッダーとボディを区切る空行

print << "EOF";
<html>
<head>
<title>書き込み完了</title>
<meta charset=Shift_JIS">

</head>
<body>

<b>書き込みが終わりました。</b><br>
画面を切り替えるまでしばらくお待ち下さい。<br>
<br>
[<a href="../$bbs/">掲示板に戻る</a>] 
[<a href="test/read.cgi/$bbs/$key">スレッドに戻る</a>]

</body>
</html>
EOF

# 3. ブラウザへのレスポンス用ヘッダーを出力（500エラー回避に必須）
# print "Content-Type: text/html; charset=Shift_JIS\n\n";

foreach my $line (@newsubjects) {
    $line =~ s/\r\n/\n/g;
    $line =~ s/\r/\n/g;

 
    $line =~ s/\n$//;
    print $sfh2 $line . "\n";
}

close $sfh2;

close $sfh2;


my $thread_list_html = "";

foreach my $line (@subjects) {
    chomp $line;
    next unless $line;
    my ($file, $title_with_count) = split(/<>/, $line, 2);
    next unless ($file && $title_with_count);
    my ($th_key) = $file =~ /^(\d+)\.dat$/;
    next unless $th_key;
   
    $thread_list_html .= sprintf(
        '<a target="_blank" href="../test/read.cgi/%s/%s/">%s</a></li>' . "\n",
        $bbs,
        $th_key,
        $title_with_count
    );
}

# リストが空だった場合のフォールバック
if (!$thread_list_html) {
    $thread_list_html = "<li>現在スレッドはありません。</li>\n";
}



# --- 各スレッドの書き込み（DAT）を読み込んでHTML化する処理 ---
my $threads_html = "";

# subject.txt の上から順にスレッドを取得（最大10スレッド分など制限も可能）
foreach my $line (@subjects) {
    chomp $line;
    next unless $line;

    my ($file, $title_with_count) = split(/<>/, $line, 2);
    next unless ($file && $title_with_count);

    my ($th_key) = $file =~ /^(\d+)\.dat$/;
    next unless $th_key;

    # DATファイルの存在確認と読み込み
    my $target_dat = "$dir/dat/$file";
    next unless -e $target_dat;

    open my $dfh, "<", $target_dat or next;
    my @dat_lines = <$dfh>;
    close $dfh;

    # スレッド内のレス表示用HTMLを作成
    my $responses_html = "";
    my $res_num = 1;

    foreach my $res (@dat_lines) {
        chomp $res;
        next unless $res;
        my ($r_name, $r_mail, $r_time, $r_body) = split(/<>/, $res);

        
        my $name_disp = $r_name;
        if ($r_mail) {
            $name_disp = qq(<a href="mailto:$r_mail"><b>$r_name</b></a>);
        } else {
            $name_disp = qq(<b><font color="green">$r_name</font></b>);
        }
        $r_body =~ s/\r?\n/<br>&emsp;&emsp;&ensp;/g;
        $r_body =~ s/\r?<br>/<br>/g;
        $r_body =~ s{(https?://[\w\.\-_/:%#\?\=&]+)}{<a href="$1" target="_blank">$1</a>}gi;


        $r_body =~ s{>>(\d+)}{<a target="_blank" href="../test/read.cgi/$bbs/$th_key/?anchor=$1#res$1">>>$1</a>}g;
        $r_body =~ s{&gt;&gt;(\d+)}{<a target="_blank" href="../test/read.cgi/$bbs/$th_key/?anchor=$1#res$1">>>$1</a>}g;

        $responses_html .= sprintf(
            '<dt>%d ：%s：%s</dt><dd> %s <br><br></dd>' . "\n",
            $res_num,
            $name_disp,
            $r_time,
            $r_body
        );
        $res_num++;
    }


    $threads_html .= <<"THREAD_END";
<div class="thread-container">

<dl>
<table align="center" border="1" width="97%"  cellpadding="2" cellspacing="7" bgcolor="#F0F0F0" style="word-break: break-all; word-wrap: break-word;"><tr><td>
<font color="red" size="5">$title_with_count</font>
<br><br>
$responses_html

</dl>

<br>
<br>
<form action="/test/bbs.cgi" method="post">
<input name="bbs" type="hidden" value="$bbs">
<input name="key" type="hidden" value="$th_key">
<button type="submit">書き込む</button>
<label for="username">名前：</label>
<input type="text" id="username" width="100" name="FROM" placeholder="名無し"> 
<label for="useremail">メアド：</label>
<input type="text" id="useremail" name="mail"> 
<br>
<br>
<textarea id="usermessage" name="MESSAGE" rows="5" cols="65" required></textarea>
</form>
<a href="."><strong>リロード</strong></a>&ensp;<a href="."><strong>板のトップ</strong></a>
</td></tr></table><br>

THREAD_END
}


my $filename = "$dir/index.html";

my $html_content = <<"EOF";
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
<div align="center"><img src="banana.gif"/></div>
<table align="center" bgcolor="#C4FFCA" border="1" width="97%"  cellpadding="2" cellspacing="7">
<tr>
<td>
<font size="4">&emsp;<strong>$setting{'BBS_TITLE'}</strong></font>
<br>
<br>
<br>
<br>
<br>
<br></td>
</tr>
<tr>
<td align="center"><a href="m"><small>書き込む前に読んでね</small></a>&emsp;<a href="k"><small>ガイドライン</small></a></td>
</tr>
</table>
<br>
<table align="center" bgcolor="#C4FFCA" border="1" width="97%"  cellpadding="2" cellspacing="7">
<tr>
<td>
$thread_list_html

</td>
</tr>

</table>
$threads_html
<table align="center" bgcolor="#C4FFCA" border="1" width="97%"  cellpadding="2" cellspacing="7">
<tr>
<td>
<div>新規スレ立て</div>
<form action="/test/bbs.cgi" method="post">
<input name="bbs" type="hidden" value="$bbs">
<button type="submit">スレ立て</button>
<label for="username">名前（スレ）：</label>
<input type="text" id="username" width="100" name="subject" placeholder="スレタイ">
<label for="name">名前：</label>
<input type="text" id="name" width="100" name="FROM" placeholder="名無し">  
<label for="useremail">メアド：</label>
<input type="text" id="useremail" name="mail"> 
<br>
<br>
<textarea id="usermessage" name="MESSAGE" rows="5" cols="65" required></textarea>
</form>
</td>
</tr>
</body>
</html>

EOF

open(my $fh, '>', $filename) or die "ファイルを開けませんでした '$filename': $!";
print $fh $html_content;
close($fh);
