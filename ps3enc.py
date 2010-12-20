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
import sys
import shlex

verbose=0
bitrate=2000
no_crop=False
test=False
language=None
subtitle=None


mplayer_bin="/usr/bin/mplayer"
mencoder_bin="/usr/bin/mencoder"
mp4box_bin="/usr/bin/MP4Box"

me=os.path.basename(sys.argv[0])
passes=3
skip_encode=False

temp_files = []

def guess_best_crop(file):
    """
    Calculate the best cropping parameters to use by looking over the whole file
    """
    size = os.path.getsize(file)
    potential_crops = {}
    for i in range(0, size-size/20, size/20):
        crop_cmd = mplayer_bin+" -nosound -vo null -sb "+str(i)+" -frames 10 -vf cropdetect '"+file+"'"
#        crop_cmd = mplayer_bin+" -nosound -sb "+str(i)+" -frames 10 -vf cropdetect "+file
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

def run_mencoder_command(command, dst_file):
    if skip_encode and os.path.exists(dst_file):
        print "Skipping generation of: "+dst_file
    else:
        print "Running: "+command
        args = shlex.split(command)
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        while p.returncode == None:
            status = p.stdout.readlines(4096)
            if status:
                line = status[-1]
                if line.startswith("Pos:"):
                    line.rstrip()
                    sys.stdout.write("\r"+line)
                    sys.stdout.flush()
            else:
                break
            
        # Grab final bits
        (out, err) = p.communicate()
        if p.returncode != 0:
            print "Failed (%d/%s)" % (p.returncode, out)
            return None

    if os.path.exists(dst_file):
        return dst_file
    else:
        print "No resulting file "+dst_file
        return None

def create_mencoder_cmd(src_file, dst_file, crop, encode_audio=False, epass=1):
    """
    return a mencoder command string
    >>> create_mencoder_cmd('fileA', 'fileB', 'copy', 'pass=1')
    """
    cmd = mencoder_bin+" '"+src_file+"'"
    # position
    if test:
        cmd = cmd + " -ss 20:00 -endpos 120 "
    if subtitle:
        cmd = cmd + " -sid "+subtitle
    else:
        cmd = cmd + " -nosub "
    if language:
        cmd = cmd + " -aid "+language
    # audio encoding
    # cmd = cmd + " -oac " + oac_args
    if encode_audio:
        cmd = cmd + " -oac faac -faacopts mpeg=4:object=2:br=128 "
    else:
        cmd = cmd + " -oac copy "
    # crop params
    cmd = cmd + " " + crop
    # harddump for remuxed streams
    cmd = cmd + " -vf softskip,harddup"
    # x264 video encoding...
# x264_encode_opts="-x264encopts subq=6:bframes=3:partitions=p8x8,b8x8,i4x4:weight_b:threads=1:nopsnr:nossim:frameref=3:mixed_refs:level_idc=41:direct_pred=auto:trellis=1"
    cmd = cmd + " -ovc x264 -x264encopts bitrate="+str(bitrate)
    cmd = cmd + ":me=hex:nodct_decimate:nointerlaced:no8x8dct:nofast_pskip:trellis=1:partitions=p8x8,b8x8,i4x4"
    cmd = cmd + ":mixed_refs:keyint=300:keyint_min=30:psy_rd=0.8,0.2:frameref=3"
    cmd = cmd + ":bframes=3:b_adapt=2:b_pyramid=none:weight_b:weightp=1:direct_pred=spatial:subq=6"
    cmd = cmd + ":nombtree:chroma_me:cabac:aud:aq_mode=2:deblock:vbv_maxrate=20000:vbv_bufsize=20000:level_idc=41:threads=auto:ssim:psnr"
    cmd = cmd + ":pass="+str(epass)
    cmd = cmd + " -o '" + dst_file + "'"

    return cmd


def do_turbo_pass(src_file, dst_file, crop):
    """
    Do a fast turbo pass encode of the file
    """
#    	my $pass1_cmd = "$mencoder_bin \"$source\" -ovc $ovc -oac copy $crop_opts $x264_encode_opts:bitrate=$bitrate:pass=1:turbo=1 -o $avi_file";
    turbo_cmd = create_mencoder_cmd(src_file, dst_file, crop, False, 1)
    return run_mencoder_command(turbo_cmd, dst_file)

def do_encoding_pass(src_file, dst_file, crop, epass=1):
    """
    Normal multi-stage encoding pass
    """
    encode_cmd = create_mencoder_cmd(src_file, dst_file, crop, True, epass)
    return run_mencoder_command(encode_cmd, dst_file)

def package_mp4(src_file):
    """
    Package a given AVI file into clean MP4
    """
    (dir, file) = os.path.split(src_file)
    (base, extension) = os.path.splitext(file)

    if verbose: print "package_mp4: (%s:%s) -> (%s:%s)\n" % (dir, file, base, extension)

    # Do this all in the work directory
    os.chdir(dir)
    
    # Final file names
    video_file = base+"_video.h264"
    audio_file = base+"_audio.aac"
    final_file = base+".mp4"

    # Get video
    mp4_video_cmd = mp4box_bin+" -aviraw video '"+src_file+"'";
    if verbose:
        print "Running: "+mp4_video_cmd
    p = subprocess.Popen(mp4_video_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    (out, err) = p.communicate()


    # Get Audio
    mp4_audio_cmd = mp4box_bin+" -aviraw audio '"+src_file+"'";
    if verbose:
        print "Running: "+mp4_audio_cmd
    p = subprocess.Popen(mp4_audio_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    (out, err) = p.communicate()
    if p.returncode != 0:
        print "Failed (%d/%s)" % (p.returncode, out)
        exit(-1)
    os.rename(base+"_audio.raw", audio_file);


    # Join the two together
    mp4_join_cmd = mp4box_bin+" -add '"+audio_file+"' -add '"+video_file+"' '"+final_file+"'"
    if verbose:
        print "Running: "+mp4_join_cmd
    p = subprocess.Popen(mp4_join_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    (out, err) = p.communicate()
    if p.returncode != 0:
        print "Failed (%d/%s)" % (p.returncode, out)
        exit(-1)

    os.unlink(video_file)
    os.unlink(audio_file)

    return



def process_input(file):
    if verbose:
        print "Handling: "+a

    if no_crop:
        crop = ""
    else:
        crop = guess_best_crop(file)

    if passes>1:
        do_turbo_pass(file, file+".TURBO.AVI", crop)
        for i in range(2, passes+1):
            ff = do_encoding_pass(file, file+".PASS"+str(i)+".AVI", crop, 3)
    else:
        ff = do_encoding_pass(file, file+".SINGLEPASS.AVI", crop)


    if os.path.exists(ff):
        print "Final file is:"+ff
        package_mp4(ff)
    else:
        print "Cannot package, no file encoded"

    for file in temp_files:
        os.unlink(file)
        
    
    


def usage():
    print """
Usage:

"""  + me + """ [options] filename

-h, --help         Display usage test
-v, -verbose       Be verbose in output
-n, --no-crop      Don't try and crop
-s, --skip-encode  Skip steps if file present
-p, --passes       Number of encoding passes
-t, --test         Do a test segment
-a, --alang=<id>   Audio channel
    --slang=<id>   Bake in subtitles
    
This script is a fairly dump wrapper to mencoder to encode files
that are compatibile with the PS3 system media playback software
"""

# Start of code
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hvnst:p:a:", ["help", "verbose", "no-crop", "skip-encode", "passes=", "test", "slang=", "alang="])
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
        if o in ("-p", "--passes"):
            passes=int(a)
        if o in ("--test"):
            test=True
        if o in ("--slang"):
            subtitle=a
        if o in ("--alang"):
            language=a

    for a in args:
        process_input(os.path.abspath(a))
        
