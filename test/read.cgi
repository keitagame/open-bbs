#!/usr/bin/perl
use strict;
use warnings;
use File::Spec;

print "Content-Type: text/html; charset=Shift_JIS\n\n";

my $path_info = $ENV{'PATH_INFO'} || '';

my @params = grep { $_ ne '' } split('/', $path_info);
my $anchor = $ENV{'QUERY_STRING'} || '';
$anchor =~ s/anchor=//;

my $bbs_id    = $params[0];
my $thread_id = $params[1];
my $range_str = $params[2] || '';

my $dat_path = File::Spec->catfile('..', $bbs_id, 'dat', "$thread_id.dat");


unless (-f $dat_path) {
    print "<html><body>dat がありません: $dat_path</body></html>";
    exit;
}



open my $fh, '<', $dat_path
    or die "Cannot open dat: $!";

my @lines = <$fh>;
close $fh;


my $thread_title = '無題';
if (@lines) {
    my @first = split(/<>/, $lines[0]);
    $thread_title = $first[4] if defined $first[4] && $first[4] ne '';
}


print <<"HTML_HEAD";
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
    "http://www.w3.org/TR/html4/loose.dtd">
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=Shift_JIS">
<title>$thread_title | $bbs_id</title>
</head>
<body bgcolor="#F0F0F0">
<br>
<a target="_blank" href="http://shinte.tech"><strong>トップへ</strong></a>&ensp;<a href="http://shinte.tech/$bbs_id/"><strong>■掲示板に戻る</strong></a>
<hr>
<font size="5" color="red">$thread_title</font>
<br><br>
HTML_HEAD

my $total_res = scalar @lines;
my $start_idx = 0;
my $end_idx   = $total_res - 1;

if ($range_str =~ /^l(\d+)$/i) {
    # 最新のN件を取得 (例: l50)
    my $count = $1;
    $start_idx = $total_res - $count;
    $start_idx = 0 if $start_idx < 0;
} elsif ($range_str =~ /^(\d+)-(\d+)$/) {
    # 範囲指定 (例: 1-50)
    $start_idx = $1 - 1;
    $end_idx   = $2 - 1;
    $start_idx = 0 if $start_idx < 0;
    $end_idx   = $total_res - 1 if $end_idx >= $total_res;
} elsif ($range_str =~ /^(\d+)-$/) {
    # N番目以降すべて (例: 50-)
    $start_idx = $1 - 1;
    $start_idx = 0 if $start_idx < 0;
} elsif ($range_str =~ /^(\d+)$/) {
    # 単一レス指定 (例: 5)
    $start_idx = $1 - 1;
    $end_idx   = $1 - 1;
}
for (my $i = $start_idx; $i <= $end_idx; $i++) {
    next if $i < 0 || $i >= $total_res; # 配列の範囲外セーフティ
    
    my $line = $lines[$i];
    chomp $line;

    my @fields = split(/<>/, $line);

    my $name    = $fields[0] // '名無し';
    my $mail    = $fields[1] // '';
    my $date    = $fields[2] // '';
    my $body    = $fields[3] // '';
    my $other   = $fields[4] // '';

    $body =~ s/\r?\n/<br>&emsp;&emsp;&ensp;/g;
    $body =~ s/\r?&lt;br&gt;/<br>&emsp;&emsp;&ensp;/g;
    $body =~ s/\r?<br>/<br>&emsp;&emsp;&ensp;/g;
    
    $body =~ s{(https?://[\w\.\-_/:%#\?\=&]+)}{<a href="$1" target="_blank">$1</a>}gi;


    $body =~ s{>>(\d+)}{<a href="#res$1">>>$1</a>}g;
    $body =~ s{&gt;&gt;(\d+)}{<a href="?anchor=$1#res$1">>>$1</a>}g;
    my $num = $i + 1; # 配列のインデックスに1を足してレス番号にする
    my $highlight = ($anchor && $anchor == $num) ? "background-color:#FFFFCC;" : "";

    print "<div id='res$num' style='margin-bottom:1em; $highlight'>$num：\n";

    # print "<div style='margin-bottom:1em;'>$num：\n";
    print "<b style='color:green;'>$name</b>：\n";
    print "<span>$date</span><br>\n";
    print "&emsp;&emsp;&ensp;$body<br>\n";
    print "</div>\n";
}
print << "HTML_BT";
<br>
<hr>
<br>
<br>
<form action="/test/bbs.cgi" method="post">
<input name="bbs" type="hidden" value="$bbs_id">
<input name="key" type="hidden" value="$thread_id">
<button type="submit">書き込む</button>
<label for="username">名前：</label>
<input type="text" id="username" width="100" name="FROM" placeholder="名無し"> 
<label for="useremail">メアド：</label>
<input type="text" id="useremail" name="mail"> 
<br>
<br>
<textarea id="usermessage" name="MESSAGE" rows="5" cols="65" required></textarea>
</form>
<a href="."><strong>リロード</strong></a>&ensp;<a href="/"><strong>板のトップ</strong></a>
HTML_BT
print "</body></html>\n";
exit;
