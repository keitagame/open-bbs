#!/usr/bin/perl
# =========================================================================
#  read.cgi - スレッドを表示する
#  URL例: read.cgi/BBSID/THREADKEY/        (全レス)
#         read.cgi/BBSID/THREADKEY/l50     (最新50)
#         read.cgi/BBSID/THREADKEY/1-50    (範囲)
#         read.cgi/BBSID/THREADKEY/50-     (50番目以降)
#         read.cgi/BBSID/THREADKEY/5       (単一レス)
# =========================================================================
use strict;
use warnings;
use CGI;
use FindBin qw($Bin);
use lib "$Bin/lib";
use BBSCommon qw(valid_bbs_id valid_key read_lines_locked linkify_body html_header);

my $q = CGI->new;



my $path_info = $ENV{PATH_INFO} || '';
my @params = grep { $_ ne '' } split('/', $path_info);

my $bbs_id    = $params[0] || '';
my $thread_id = $params[1] || '';
my $range_str = $params[2] || '';
my $anchor    = $q->param('anchor') || '';

unless (valid_bbs_id($bbs_id)) {
print html_header();
    print "<html><body>不正な掲示板IDです。</body></html>";
    exit;
}
unless (valid_key($thread_id)) {
print html_header();
    print "<html><body>不正なスレッドキーです。</body></html>";
    exit;
}

my $dat_path = "../$bbs_id/dat/$thread_id.dat";
unless (-f $dat_path) {
print html_header();
    print "<html><body>スレッドが見つかりません（dat落ち、または削除された可能性があります）。</body></html>";
    exit;
}

my @lines = read_lines_locked($dat_path);

my $thread_title = '無題';
if (@lines) {
    my @first = split(/<>/, $lines[0]);
    $thread_title = $first[4] if defined $first[4] && $first[4] ne '';
}
my $ua = $ENV{'HTTP_USER_AGENT'} || '';


if ($ua =~ /iPhone|Android/i) {

    
    my $uri = $ENV{'REQUEST_URI'};  
    $uri =~ s/[^\/]+$//;             

    if ($ENV{'REQUEST_URI'} !~ /sm\.html$/) {

        print "Status: 302 Found\n";
        print "Location: /board.html?board=$bbs_id&title=$thread_title\n\n";
        exit;
    }
}
print html_header();
print <<"HTML_HEAD";
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
    "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=Shift_JIS">
<meta property="og:title" content="$thread_title">
<meta property="og:type" content="article">
<meta property="og:description" content="Anyちゃんねるのスレ">
<meta property="og:url" content="https://shinte.tech/test/read.cgi/$bbs_id/$thread_id/">
<meta property="og:image" content="https://shinte.tech/ogp.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="$thread_title">
<meta name="twitter:image" content="https://shinte.tech/ogp.png">

<title>$thread_title | $bbs_id</title>
</head>
<body bgcolor="#F0F0F0">
<br>
<a target="_top" href="/"><strong>トップへ</strong></a>&ensp;<a href="/$bbs_id/"><strong>■掲示板に戻る</strong></a>
<hr>
<button onclick="subscribePush('$bbs_id', '$thread_id')">
    このスレを通知購読する
</button>
<script src="https://shinte.tech/subscribe.js"></script>
<br>
<font size="5" color="red">$thread_title</font>
<br><br>
HTML_HEAD

my $total_res = scalar @lines;
my $start_idx = 0;
my $end_idx   = $total_res - 1;

if ($range_str =~ /^l(\d+)$/i) {
    my $count = $1;
    $start_idx = $total_res - $count;
    $start_idx = 0 if $start_idx < 0;
} elsif ($range_str =~ /^(\d+)-(\d+)$/) {
    $start_idx = $1 - 1;
    $end_idx   = $2 - 1;
    $start_idx = 0 if $start_idx < 0;
    $end_idx   = $total_res - 1 if $end_idx >= $total_res;
} elsif ($range_str =~ /^(\d+)-$/) {
    $start_idx = $1 - 1;
    $start_idx = 0 if $start_idx < 0;
} elsif ($range_str =~ /^(\d+)$/) {
    $start_idx = $1 - 1;
    $end_idx   = $1 - 1;
}

my $anchor_tmpl = '?anchor=%d#res%d';

for (my $i = $start_idx; $i <= $end_idx; $i++) {
    next if $i < 0 || $i >= $total_res;

    my $line = $lines[$i];
    chomp $line;
    my @fields = split(/<>/, $line);

    my $name = $fields[0] // '名無し';
    my $mail = $fields[1] // '';
    my $date = $fields[2] // '';
    my $body = $fields[3] // '';
$body =~ s/:([A-Za-z0-9_]+)/<img src="\/emoji\/$1" style="height:2.5em; vertical-align:middle;">/g;


    $body =~ s{<br>}{<br>&emsp;&emsp;&ensp;}g;

    $body = linkify_body($body, $anchor_tmpl);
  


    my $num = $i + 1;
    my $highlight = ($anchor && $anchor eq $num) ? 'background-color:#FFFFCC;' : '';

    my $name_disp = $mail
        ? qq(<a href="mailto:$mail"><b style="color:green;">$name</b></a>)
        : qq(<b style="color:green;">$name</b>);

    print "<div id='res$num' style='margin-bottom:1em; word-break: break-all; word-wrap: break-word;$highlight'>$num：\n";
    print "$name_disp：\n";
    print "<span>$date</span><br>\n";
    print "&emsp;&emsp;&ensp;$body<br>\n";
    print "</div>\n";
}

if ($total_res == 0) {
    print "<p>レスがありません。</p>\n";
}

print <<"HTML_BT";
<br>
<hr>
<br><br>
<form action="/test/bbs.cgi" method="post">
<input name="bbs" type="hidden" value="$bbs_id">
<input name="key" type="hidden" value="$thread_id">
<button type="submit">書き込む</button>
<label for="username">名前：</label>
<input type="text" id="username" width="100" name="FROM" placeholder="名無し">
<label for="useremail">メアド：</label>
<input type="text" id="useremail" name="mail">
<br><br>
<textarea id="usermessage" name="MESSAGE" rows="5" cols="65" maxlength="4000" required></textarea>
</form>
<a href="."><strong>リロード</strong></a>&ensp;<a href="/"><strong>板のトップ</strong></a>
HTML_BT

print "<br><br><div align='center'><script src='https://adm.shinobi.jp/s/505bc828d288f41d560a3369733fc6c5'></script></div></body></html>\n";
exit;
