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
import shutil
import tempfile

# Handy for running in place
from os.path import realpath,dirname
script=realpath(sys.argv[0])
devlibs=dirname(script)+"/lib"
if os.path.exists(devlibs):
    print "Adding "+devlibs+" to path"
    sys.path.insert(0, devlibs)
else:
    print "sys.argv[0] is %s" % (realpath(dirname(sys.argv[0])))

from video_source_factory import get_video_source

verbose=False
verbose_level=0

audio_bitrate=128
video_bitrate=2000
no_crop=False
test=False
progress=False
debug=False

audio_id=None
language=None
subtitle=None

package_only=False
cartoon=False

mplayer_bin="/usr/bin/mplayer"
mencoder_bin="/usr/bin/mencoder"
mp4box_bin="/usr/bin/MP4Box"

me=os.path.basename(sys.argv[0])
passes=3
skip_encode=False

# Some exceptions
class MencoderError(Exception):
    def __init__(self, reason):
        self.reason = reason
    def __str__(self):
        return repr(self.reason)

def calc_temp_pathspec(src_file, stage, temp_dir):
    """
    >>> calc_temp_pathspec('/home/alex/tmp/video/something.vob', 'turbo.avi', '/tmp/tmpdir_xxx')
    '/tmp/tmpdir_xxx/something.turbo.avi'
    """
    (dir, file) = os.path.split(src_file)
    (base, extension) = os.path.splitext(file)
    final_path = temp_dir+"/"+base+"."+stage
    return final_path


def run_mencoder_command(command, dst_file):
    if skip_encode and os.path.exists(dst_file):
        print "Skipping generation of: "+dst_file
    else:
        print "Running: %s (progress is %s)" % (command, str(progress))
        args = shlex.split(command)
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
        while p.returncode == None:
            status = p.stdout.readlines(4096)

            if status and progress==True:
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
            raise MencoderError("mencoder failed ((%d/%s)" % (p.returncode, out))

    if os.path.exists(dst_file):
        return dst_file
    else:
        raise MencoderError("Missing output file: %s" % dst_file)

def create_mencoder_cmd(src_file, dst_file, crop, encode_audio=False, epass=1):
    """
    return a mencoder command string
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
        cmd = cmd + " -oac faac -faacopts mpeg=4:object=2:br="+str(audio_bitrate)
    else:
        cmd = cmd + " -oac copy "
    # crop params
    cmd = cmd + " " + crop
    # harddump for remuxed streams
    cmd = cmd + " -vf softskip,harddup"

    # For cartoons post-processing median deinterlacer seems to help
    if cartoon:
        cmd = cmd + ",pp=md"

    if audio_id:
        cmd = cmd + " -aid "+audio_id
        
    # x264 video encoding...
# x264_encode_opts="-x264encopts subq=6:bframes=3:partitions=p8x8,b8x8,i4x4:weight_b:threads=1:nopsnr:nossim:frameref=3:mixed_refs:level_idc=41:direct_pred=auto:trellis=1"
    cmd = cmd + " -ovc x264 -x264encopts bitrate="+str(video_bitrate)
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

def package_mp4(src_file, temp_dir, dest_dir, fps=None):
    """
    Package a given AVI file into clean MP4
    """
    (dir, file) = os.path.split(src_file)
    (base, extension) = os.path.splitext(file)

    if verbose: print "package_mp4: (%s:%s) -> (%s:%s)\n" % (dir, file, base, extension)

    # Do this all in the work directory
    os.chdir(temp_dir)
    
    # Final file names
    video_file = calc_temp_pathspec(src_file, "video.h264", temp_dir)
    audio_file = calc_temp_pathspec(src_file, "audio.aac", temp_dir)
    final_file = dest_dir+"/"+base+".mp4"

    # Get video
    mp4_video_cmd = mp4box_bin+" -aviraw video '"+src_file+"'";
    if verbose:
        print "Running: "+mp4_video_cmd
    p = subprocess.Popen(mp4_video_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    (out, err) = p.communicate()
    os.rename(base+"_video.h264", video_file)


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
    mp4_join_cmd = mp4box_bin+" "
    if fps:
        mp4_join_cmd = mp4_join_cmd+"-fps "+str(fps)+" "
    mp4_join_cmd = mp4_join_cmd+" -add '"+audio_file+"' -add '"+video_file+"' '"+final_file+"'"
    if verbose:
        print "Running: "+mp4_join_cmd
    p = subprocess.Popen(mp4_join_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    (out, err) = p.communicate()
    if p.returncode != 0:
        print "Failed (%d/%s)" % (p.returncode, out)
        exit(-1)

    if not debug:
        os.unlink(video_file)
        os.unlink(audio_file)

    return


# Process a single VOB file into final MP4
def process_input(vob_file):
    if verbose: print "process_input: "+vob_file

    video = get_video_source(vob_file, (verbose_level>1))
    video.analyse_video()

    # Save were we are
    (dir, file) = os.path.split(vob_file)
    (base, extension) = os.path.splitext(file)

    start_dir = os.getcwd()
    
    # Temp files
    temp_dir = tempfile.mkdtemp("encode", "video")
    os.chdir(temp_dir)
    
    temp_files = [temp_dir+"/divx2pass.log"]

    if no_crop:
        crop = ""
    else:
        crop = video.crop_spec

    if verbose: print "Calculated crop of %s for %s" % (crop, vob_file)

    try:
        if passes>1:
            tf = calc_temp_pathspec(vob_file, "turbo.avi", temp_dir)
            temp_files.append(do_turbo_pass(vob_file, tf, crop))
            for i in range(2, passes+1):
                tf = calc_temp_pathspec(vob_file, "pass"+str(i)+".avi", temp_dir)
                temp_files.append(do_encoding_pass(vob_file, tf, crop, 3))
        else:
            tf = calc_temp_pathspec(vob_file, "singlepass.avi", temp_dir)
            temp_files.append(do_encoding_pass(vob_file, tf, crop))


        ff = temp_files[-1]
        if verbose: print "Final encode of %s is %s" % (vob_file, ff)

        if os.path.exists(ff):
            print "Final file is:"+ff
            package_mp4(ff, temp_dir, dir, video.fps)
            os.chdir(start_dir)
            if not debug:
                for tf in temp_files:
                    os.unlink(tf)
                    shutil.rmtree(temp_dir)
    except MencoderError as e:
        print "error: %s" % str(e);


def usage():
    print """
Usage:

"""  + me + """ [options] filename

-h, --help         Display usage test
-v, --verbose      Be verbose in output
--progress         Show progress of encode
-d, --debug        Keep interim files for debugging
-n, --no-crop      Don't try and crop
-s, --skip-encode  Skip steps if file present

Encoding control:
    -p, --passes       Number of encoding passes (default """+str(passes)+""")
    -c, --cartoon      Assume we are encoding a cartoon (lower bitrate + filters)
    -f, --film         Assume we are encoding a film (higher bitrate)


    -t, --test         Do a test segment
    -a, --alang=<id>   Audio channel
        --slang=<id>   Bake in subtitles

    --pkg          Just package
    
This script is a fairly dump wrapper to mencoder to encode files
that are compatible with the PS3 system media playback software
"""

# Start of code
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hvdnstp:a:cf", ["help", "verbose", "debug", "no-crop", "skip-encode", "passes=", "test", "slang=", "alang=", "progress", "pkg", "cartoon", "film", "bitrate=", "unit-tests", "aid="])
    except getopt.GetoptError, err:
        usage()

    create_log=None

    for o,a in opts:
        if o in ("-h", "--help"):
            usage()
            exit
        if o in ("-v", "--verbose"):
            verbose=True
            verbose_level += 1
        if o in ("-d", "--debug"):
            debug=True
        if o in ("-n", "--no-crop"):
            no_crop=True
        if o in ("-s", "--skip-encode"):
            skip_encode=True
        if o in ("-p", "--passes"):
            passes=int(a)
        if o in ("-c", "--cartoon"):
            print "Setting cartoon presets"
            passes=1
            video_bitrate=1500
            cartoon=True
        if o in ("-f", "--film"):
            video_bitrate=3000
            audio_bitrate=192
        if o in ("-t", "--test"):
            test=True

        # Long options
        if o.startswith("--bitrate"):
            bitrate=a
        if o.startswith("--slang"):
            subtitle=a
        if o.startswith("--alang"):
            language=a
        if o.startswith("--aid"):
            print "setting audio ID to "+a
            audio_id=a
        if o.startswith("--progress"):
            print "setting progress from (%s)" % (o)
            progress=True
        if o.startswith("--pkg"):
            package_only=True
        if o.startswith("--unit-tests"):
            import doctest
            doctest.testmod()
            exit()
            

    # Calculate the full paths ahead of time (lest cwd changes)
    files = []
    for a in args:
        if a.startswith("dvd://"):
            files.append(a)
        else:
            fp = os.path.realpath(a)
            files.append(fp)
 
    for f in files:
        if package_only:
            package_mp4(f)
        else:
            process_input(f)
        
