#!/usr/bin/perl
use strict;
use warnings;

# Shift_JIS のまま出力
print "Content-Type: text/html; charset=Shift_JIS\n\n";


my $query = $ENV{'QUERY_STRING'} || '';
my %params;

for my $pair (split /&/, $query) {
    my ($k, $v) = split /=/, $pair, 2;
    $params{$k} = $v;
}

my $bbs = $params{'bbs'} || 'test';   
my $MAX_LINES = 10;


my $BBS_DIR      = "../$bbs";
my $SUBJECT_FILE = "$BBS_DIR/subject.txt";


open my $fh, '<', $SUBJECT_FILE
  or do {
      print "<p>subject.txt が開けません: $SUBJECT_FILE</p>\n";
      exit;
  };

my @lines = <$fh>;
close $fh;

# -----------------------------
# HTML 出力（Shift_JIS）
# -----------------------------
print "<html><head><title>ヘッドライン</title></head><body>\n";
print "<div style='background:#C4FFCA;padding:1px;'><font size='5'><strong>Anyちゃんねる 新着スレッドヘッドライン</strong></font></div>\n";
print "<strong>$bbs 板</strong>\n";
print "<a href='../$bbs'>トップへ</a><br>\n";

my $count = 0;
print "<div style='border-radius:10px;border:2px dashed orange;padding:5px;background:#fff7e8;'>\n";
for my $line (@lines) {
    last if $count >= $MAX_LINES;

    chomp $line;
    my ($dat, $title) = split /<>/, $line, 2;
    next unless defined $dat && defined $title;
    my $dat_file = "../$bbs/dat/$dat";
    $dat =~ s/\.dat$//;

    my $url = "./read.cgi/$bbs/$dat";

    

    open my $fh, '<', $dat_file or die "dat が開けません";

    my $first = <$fh>;
    close $fh;
  
    my @fields = split /<>/, $first;
    my $datetime = $fields[2];

    $datetime =~ s/\s*ID:.*$//;

    $title =~ s/\s*\(\d+\)\s*$//;

    print qq{ <font size="1">$datetime</font><a href="$url">★$title</a><br>\n};

    $count++;
}

print "</div>\n";
print "</body></html>\n";
