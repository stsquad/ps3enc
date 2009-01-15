#!/usr/bin/perl
#
# Encode DVD's (and other sources) into a version of MP4 that a PS3 can use
#
# Based on Carlos Rivero's GPL bash script (www.subvida.com)
#
# (c)opyright 2008 Alex Bennee <alex@bennee.com>
#
# Licenced under the GPL version 2 Which means no warrenty! Break it
# you get to keep both pieces, fix it then please send me the glue :-)
#

use strict;

#Use Time::localtime;
use File::Basename;
use Getopt::Long;

(my $me = $0) =~ s|.*/(.*)|$1|;

# Options
my ($help, $verbose, $quiet);

# This is for -ovc x264, break it down later
my $x264_encode_opts="-x264encopts subq=6:bframes=3:partitions=p8x8,b8x8,i4x4:weight_b:threads=auto:nopsnr:nossim:frameref=3:mixed_refs:level_idc=41:direct_pred=auto:trellis=1";
#pass=1:bitrate=$3:

my $ovc="x264";
my $oac="faac";

# General Encode Paramters

my $bitrate=2000;
my $passes=2;
my $crop_opts;
my $source;
my $output;
my $test;

my $mplayer_bin="/usr/bin/mplayer";
my $mencoder_bin="/usr/bin/mencoder";

# Get all appropraite options
GetOptions (
    # Basic Usage
    'h|?|help'   => \$help,
    'v|verbose'  => \$verbose,
    'q|quiet'    => \$quiet,
    # Alt mplayer binary
    'm|mplayer=s' => \$mplayer_bin,
    
    # Encode Params
    'p|passes=i' => \$passes,
    'c|crop=s'   => \$crop_opts,
    
    # Tweaks
    't|test'     => \$test 
    );

if ( defined $help ) { &usage; }

my ($source) = @ARGV;
die "Can't see $source" if ! -f $source;

die "Can't see mplayer binary @ $mplayer_bin\n" if ! -f $mplayer_bin;

#
# First thing we need to do is crop detect
#
print "Running crop detection phase\n" unless $quiet;
my $pos = "-ss 20:00 -frames 10";
my $cmd = "$mplayer_bin -nosound -vo null ".$pos." -vf cropdetect ".$source;

print "  cmd=$cmd\n" if $verbose;

open (CD, "$cmd 2> /dev/null |");
while (<CD>)
{
    chomp;
    my $line = $_;
    print "    mplayer: $line\n" if $verbose;
    if ($line =~ m#vf crop#)
    {
	($crop_opts) = $line =~ m/(-vf crop=[0123456789:]+)/; 
    }
}
close CD;

print "  crop_opts = $crop_opts\n" unless $quiet;

#
# Run the mencoder phase
#
my $avi_file = $source;
$avi_file =~ s/\.vob/\.avi/;

# If we are doing a multipass encode we do first stage specially
my $pass_opt = "pass=1";
if ($passes > 1)
{
    my $pass1_cmd = "$mencoder_bin $source -ovc $ovc -oac copy $crop_opts $x264_encode_opts:bitrate=$bitrate:pass=1:turbo=1 -o $avi_file";
    print "Running: $pass1_cmd\n" unless $quiet;
    system($pass1_cmd) unless $test;

    # Set passes for next run
    $passes--;
    $pass_opt="pass=3";
}

while ($passes>0)
{
    my $men_cmd = "$mencoder_bin $source -ovc $ovc -oac $oac $crop_opts $x264_encode_opts:bitrate=$bitrate:$pass_opt -o $avi_file";
    print "Running: $men_cmd\n" unless $quiet;
    system($men_cmd) unless $test;
    $passes--;
}

exit 0;

####################
# Subroutines
####################

# Print usage information
sub usage {
    print STDERR <<EOF;
Usage: $me [options] <vob file>

    options
	-h, --help  display usage information

	-m, --mplayer=/path/to/mplayer

    encode parameter
        -p, --passes number of passes
        -c, --crop   crop operations

EOF
    exit 1;
}
