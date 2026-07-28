#!/usr/bin/perl
use strict;
use warnings;
use File::Spec;

print "Content-Type: text/html; charset=Shift_JIS\n\n";

my $path_info = $ENV{'PATH_INFO'} || '';

my @params = grep { $_ ne '' } split('/', $path_info);

my $bbs_id    = $params[0];
my $thread_id = $params[1];


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
<title>$thread_id</title>
</head>
<body>
<br>
<a href="http://keitagames.com"><strong>トップへ</strong></a>&ensp;<a href="http://keitagames.com/$bbs_id/"><strong>■掲示板に戻る</strong></a>
<hr>
<font size="5" color="red">$thread_title</font>
<br><br>
HTML_HEAD

my $num = 1;

foreach my $line (@lines) {
    chomp $line;

    my @fields = split(/<>/, $line);

    my $name    = $fields[0] // '名無し';
    my $mail    = $fields[1] // '';
    my $date    = $fields[2] // '';
    my $body    = $fields[3] // '';
    my $other   = $fields[4] // '';

   
    $body =~ s/\r?\n/<br>&emsp;&emsp;&ensp;/g;
    $body =~ s/\r?<br>/<br>&emsp;&emsp;&ensp;/g;

    print "<div style='margin-bottom:1em;'>$num：\n";
    print "<b style='color:green;'>$name</b>：\n";
    print "<span>$date</span><br>\n";
    print "&emsp;&emsp;&ensp;$body<br>\n";
    print "</div>\n";
    $num++;
}
print << "HTML_BT";
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
