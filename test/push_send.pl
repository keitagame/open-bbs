#!/usr/bin/perl
use strict;
use warnings;
use Web::Push;

my $file = shift @ARGV or die "subscription file required";

my $subscription = do $file;

my $wp = Web::Push->new(
    public_key  => 'BB1Y7YLU6yPzprmmpD8wM8oLIB9bhX1rWxwsvBw4FPV2HAEWWO8X7pL4jllckhhVAM5aR5-JRyFRkn4brcHD1WQ',
    private_key => 'MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgOZE9hk7fgD3EzklSufu74doPg_hC21hpvCho6LIz7xChRANCAAQdWO2C1Osj86a5pqQ_MDPKCyAfW4V9a1scLLwcOBT1dhwBFljvF-6S-I5ZXJIYVQDOWkefiUchUZJ-G63Bw9Vk'
);

my $payload = '{"title":"スレ更新","body":"新しいレスがあります"}';

my $res = $wp->send($subscription, $payload);

print "Result: $res\n";
