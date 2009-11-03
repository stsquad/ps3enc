#!/usr/bin/perl
#
# Encode DVD's (and other sources) into a version of MP4 that a PS3 can use
#
# Based on Carlos Rivero's GPL bash script (http://subvida.com/2007/06/18/convert-divx-xvid-to-ps3-format-mpeg4-on-linux/)
#
# (c)opyright 2008,2009 Alex Bennee <alex@bennee.com>
#
# Licenced under the GPL version 3 Which means no warrenty! Break it
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
my $no_crop;

# Files
my $source;
my ($name, $path, $ext);
my $output;

# Control parameters
my $test;
my $skip_encode;

my $mplayer_bin=`which mplayer`;
my $mencoder_bin=`which mencoder`;
my $mp4box_bin=`which MP4Box`;

chomp($mplayer_bin, $mencoder_bin, $mp4box_bin);

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
    'nc|nocrop'  => \$no_crop,
    'b|bitrate=s'=> \$bitrate,

    # Output file
    'o|output=s' => \$name,
    
    # Tweaks
    't|test'     => \$test,
    's|skip'     => \$skip_encode,
    );

if ( defined $help ) { &usage; }

($source) = @ARGV;
die "Can't see $source" if ! -f $source;

# If we haven't defined an output file make it from the input file
if (!defined $name)
{
    ($name, $path, $ext) = fileparse($source,  qr/\.[^.]*/);
}

if (defined $no_crop)
{
    $crop_opts=" ";
}


die "Can't see mplayer binary @ $mplayer_bin\n" if ! -f $mplayer_bin;

#
# First thing we need to do is crop detect (unless we have defined by hand)
#
unless (defined $crop_opts || defined $skip_encode)
{

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
}

#
# Run the mencoder phase
#
my $avi_file = "$name".".avi";

if (defined $skip_encode)
{
    die "Can't see $avi_file so can't skip encode step" if ! -f $avi_file;
}
else
{
# If we are doing a multipass encode we do first stage specially
    my $pass_opt = "pass=1";
    if ($passes > 1)
    {
	my $pass1_cmd = "$mencoder_bin \"$source\" -ovc $ovc -oac copy $crop_opts $x264_encode_opts:bitrate=$bitrate:pass=1:turbo=1 -o $avi_file";
	print "Running: $pass1_cmd\n" unless $quiet;
	system($pass1_cmd) unless $test;

	# Set passes for next run
	$passes--;
	$pass_opt="pass=3";
    }

    while ($passes>0)
    {
	my $men_cmd = "$mencoder_bin \"$source\" -ovc $ovc -oac $oac $crop_opts $x264_encode_opts:bitrate=$bitrate:$pass_opt -o $avi_file";
	print "Running: $men_cmd\n" unless $quiet;
	system($men_cmd) unless $test;
	$passes--;
    }
}

#
# Now multiplex into an MP4 stream
# cho "Now converting avi to MP4, due to limitations."
# MP4Box -aviraw video $2.avi
# MP4Box -aviraw audio $2.avi
# mv $2_audio.raw $2_audio.aac
# MP4Box -add $2_audio.aac -add $2_video.h264 $2.mp4
#

my $mp4_cmd;

$mp4_cmd = "$mp4box_bin -aviraw video $avi_file";
print "Running: $mp4_cmd\n" unless $quiet;
system($mp4_cmd);
    
$mp4_cmd = "$mp4box_bin -aviraw audio $avi_file";
print "Running: $mp4_cmd\n" unless $quiet;
system($mp4_cmd);
rename("$name"."_audio.raw", "$name"."_audio.aac");

$mp4_cmd = "$mp4box_bin -add $name"."_audio.aac -add $name"."_video.h264 $name.mp4";
print "Running: $mp4_cmd\n" unless $quiet;
system($mp4_cmd);


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
