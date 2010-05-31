#!/usr/bin/python
#
# Encode DVD's (and other sources) into a version of MP4 that a PS3 can use
#
# Based on my ps3enc.pl (perl version) which was...
# Based on Carlos Rivero's GPL bash script
# (http://subvida.com/2007/06/18/convert-divx-xvid-to-ps3-format-mpeg4-on-linux/)
#
# (C)opyright 2010 Alex Bennee <alex@bennee.com>
#
# Licenced under the GPL version 3 Which means no warrenty! Break it
# you get to keep both pieces, fix it then please send me the glue :-)
#

import os
import sys
import getopt
import subprocess
import re

verbose=0
x264_encode_opts="-x264encopts subq=6:bframes=3:partitions=p8x8,b8x8,i4x4:weight_b:threads=1:nopsnr:nossim:frameref=3:mixed_refs:level_idc=41:direct_pred=auto:trellis=1"
bitrate=2000
no_crop=False

# What codecs?
ovc="x264";
oac="faac";


mplayer_bin="/usr/bin/mplayer"
mencoder_bin="/usr/bin/mencoder"

me=os.path.basename(sys.argv[0])
passes=3
skip_encode=False

def guess_best_crop(file):
    """
    Calculate the best cropping parameters to use by looking over the whole file
    """
    size = os.path.getsize(file)
    potential_crops = {}
    for i in range(0, size-size/10, size/10):
        crop_cmd = mplayer_bin+" -nosound -vo null -sb "+str(i)+" -frames 10 -vf cropdetect "+file
        if verbose:
            print "Running: "+crop_cmd
        try:
            p = subprocess.Popen(crop_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            (out, err) = p.communicate()
            m = re.search("\-vf crop=[-0123456789:]*", out)
            try:
                potential_crops[m.group(0)]+=1
            except KeyError:
                potential_crops[m.group(0)]=1
                if verbose:
                    print "Found:"+m.group(0)
        except OSError:
            print "Failed to spawn: "+crop_cmd

    # most common crop?
    crop_count = 0
    for crop  in potential_crops:
        if potential_crops[crop] > crop_count:
            crop_count = potential_crops[crop]
            crop_to_use = crop

    if verbose:
        print "Crop to use is:"+crop_to_use

    return crop_to_use

def do_turbo_pass(src_file, dst_file, crop):
    """
    Do a fast turbo pass encode of the file
    """
#    	my $pass1_cmd = "$mencoder_bin \"$source\" -ovc $ovc -oac copy $crop_opts $x264_encode_opts:bitrate=$bitrate:pass=1:turbo=1 -o $avi_file";
    turbo_cmd = mencoder_bin+" "+src_file+" -ovc "+ovc+" -oac copy "+crop+" "+x264_encode_opts+":bitrate="+str(bitrate)+":pass=1:turbo=1 -o "+dst_file
    print "turbo_cmd:"+turbo_cmd
    if skip_encode and os.path.exists(dst_file):
        print "Skipping generation of: "+dst_file
    else:
        p = subprocess.Popen(turbo_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        (out, err) = p.communicate()

    return dst_file

def do_encoding_pass(src_file, dst_file, crop, epass=1):
    """
    Normal multi-stage encoding pass
    """
    encode_cmd = mencoder_bin+" "+src_file+" -ovc "+ovc+" -oac "+oac+" "+crop+" "+x264_encode_opts+":bitrate="+str(bitrate)+":pass="+str(epass)+" -o "+dst_file
    print "encode_cmd:"+encode_cmd
    if skip_encode and os.path.exists(dst_file):
        print "Skipping generation of: "+dst_file
    else:
        p = subprocess.Popen(encode_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        (out, err) = p.communicate()
        

    return dst_file


def process_input(file):
    if verbose:
        print "Handling: "+a

    if no_crop:
        crop = ""
    else:
        crop = guess_best_crop(file)

    if passes>1:
        do_turbo_pass(file, file+".TURBO.AVI", crop)
        for i in range(2, passes):
            ff = do_encoding_pass(file, file+".PASS"+str(i)+".AVI", crop, 3)
    else:
        ff = do_encoding_pass(file, file+".SINGLEPASS.AVI", crop)


    print "Final file is:"+ff

        
    
    


def usage():
    print "Usage:"
    print "  " + me + " [options] filename"
    print "  -h, --help:   Display usage test"
    print "  -v, -verbose: Be verbose in output"
    print "  -n, --no-crop: Don't try and crop"
    print "  -s, --skip-encode: Skip steps if file present"
    print ""
    print "This script is a fairly dump wrapper to mencoder to encode files"
    print "that are compatibile with the PS3 system media playback software"

# Start of code
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hvns", ["help", "verbose", "no-crop", "skipp-encode"])
    except getopt.GetoptError, err:
        usage()

    create_log=None

    for o,a in opts:
        if o in ("-h", "--help"):
            usage()
            exit
        if o in ("-v", "--verbose"):
            verbose=1
        if o in ("-n", "--no-crop"):
            no_crop=True
        if o in ("-s", "--skip-encode"):
            skip_encode=True

    for a in args:
        process_input(os.path.abspath(a))
        
