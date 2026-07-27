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

print "<html><body>\n";
print "<h2>$thread_id </h2>\n";
print "<hr>\n";

# dat の各行を表示（2ch 形式：名前<>メール<>日付<>本文<>その他）
foreach my $line (@lines) {
    chomp $line;

    my @fields = split(/<>/, $line);

    my $name    = $fields[0] // '名無し';
    my $mail    = $fields[1] // '';
    my $date    = $fields[2] // '';
    my $body    = $fields[3] // '';
    my $other   = $fields[4] // '';

    # 改行を <br> に変換（最小構成）
    $body =~ s/\r?\n/<br>/g;

    print "<div style='margin-bottom:1em;'>\n";
    print "<b style='color:green;'>$name</b>\n";
    print "<span>$date</span><br>\n";
    print "$body<br>\n";
    print "</div>\n";
}

print "</body></html>\n";
exit;

