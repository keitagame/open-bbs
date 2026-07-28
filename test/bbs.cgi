#!/usr/bin/perl
use strict;
use warnings;
use CGI;
use Digest::MD5 qw(md5_hex);
my $q = CGI->new;

my $bbs  = $q->param('bbs');
my $key  = $q->param('key');
my $name = $q->param('FROM') || '名無しさん';
my $mail = $q->param('mail') || '';
my $body = $q->param('MESSAGE') || '';
# 改行コード統一
$body =~ s/\r\n/\n/g;
$body =~ s/\r/\n/g;

$body =~ s/ / /g;

# 全角スペース（U+3000）を &#x3000; に変換
$body =~ s/\x{3000}/&#x3000;/g;

# 複数行を行内に埋め込む（\n を <br> に置換）
$body =~ s/\n/<br>/g;



my $dir = "../$bbs";
my $dat = "$dir/dat/$key.dat";


if (!-e $dat) {
    print "Content-Type: text/html; charset=UTF-8\n\n";
    print "<html><body>スレッドがありません。</body></html>";
    exit;
}


open my $fh, "<", $dat or die "Cannot open dat: $!";
my @lines = <$fh>;
close $fh;

my $no = scalar(@lines) + 1;

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

foreach my $line (@newsubjects) {
    $line =~ s/\r\n/\n/g;
    $line =~ s/\r/\n/g;

    
    $line =~ s/\n$//;
    print $sfh2 $line . "\n";
}

close $sfh2;

close $sfh2;


print "Status: 302 Found\n";
print "Location: read.cgi/$bbs/$key/\n\n";
# 3. ブラウザへのレスポンス用ヘッダーを出力（500エラー回避に必須）
print "Content-Type: text/html; charset=Shift_JIS\n\n";


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
<font size="4">&emsp;<strong>テストAnyChBBS</strong></font>
<br>
<br>&emsp;テスト用の板です。何でも書いてください。
<br></td>
</tr>
<tr>
<td align="center"><a href="m"><small>書き込む前に読んでね</small></a>&emsp;<a href="k"><small>ガイドライン</small></a></td>
</tr>
</table>
<br>
</body>
</html>

EOF

open(my $fh, '>', $filename) or die "ファイルを開けませんでした '$filename': $!";
print $fh $html_content;
close($fh);
