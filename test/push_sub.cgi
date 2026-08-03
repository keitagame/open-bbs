#!/usr/bin/perl
use strict;
use warnings;
use CGI;
use JSON;

my $q = CGI->new;
my $json = $q->param('POSTDATA');
my $data = decode_json($json);

my $bbs = $data->{bbs};
my $key = $data->{key};
my $sub = $data->{subscription};

my $file = "../$bbs/dat/$key.sub.json";

my @subs;
@subs = @{ decode_json(do { local(@ARGV,$/) = $file; <> }) } if -e $file;

push @subs, $sub;

open my $fh, '>', $file;
print $fh encode_json(\@subs);
close $fh;

print "Content-Type: text/plain\n\nOK";
