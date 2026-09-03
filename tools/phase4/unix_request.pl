#!/usr/bin/env perl

use strict;
use warnings;
use Socket qw(AF_UNIX SOCK_STREAM sockaddr_un);

use constant MAXIMUM_BYTES => 65_536;

sub fail_request {
    print STDERR "request failed\n";
    exit 1;
}

@ARGV == 1 or fail_request();
my $socket_path = $ARGV[0];
defined($socket_path)
    && $socket_path =~ m{^/}
    && length($socket_path) <= 1_024
    && $socket_path !~ /[\0\r\n]/
    or fail_request();

my $payload = q{};
while (1) {
    my $chunk = q{};
    my $count = sysread(STDIN, $chunk, 8_192);
    defined($count) or fail_request();
    last if $count == 0;
    $payload .= $chunk;
    length($payload) <= MAXIMUM_BYTES or fail_request();
}
$payload =~ s/\n\z//;
length($payload) > 0 or fail_request();

socket(my $socket, AF_UNIX, SOCK_STREAM, 0) or fail_request();
connect($socket, sockaddr_un($socket_path)) or fail_request();

my $offset = 0;
while ($offset < length($payload)) {
    my $count = syswrite($socket, $payload, length($payload) - $offset, $offset);
    defined($count) && $count > 0 or fail_request();
    $offset += $count;
}
shutdown($socket, 1) or fail_request();

my $response = q{};
while (1) {
    my $chunk = q{};
    my $count = sysread($socket, $chunk, 8_192);
    defined($count) or fail_request();
    last if $count == 0;
    $response .= $chunk;
    length($response) <= MAXIMUM_BYTES or fail_request();
}
length($response) > 0 or fail_request();
print STDOUT $response or fail_request();
close($socket) or fail_request();

exit 0;
