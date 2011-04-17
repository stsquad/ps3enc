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

verbose=False
bitrate=2000
no_crop=False
test=False
progress=False
debug=False
language=None
subtitle=None
package_only=False
cartoon=False

fps=None

mplayer_bin="/usr/bin/mplayer"
mencoder_bin="/usr/bin/mencoder"
mp4box_bin="/usr/bin/MP4Box"

me=os.path.basename(sys.argv[0])
passes=3
skip_encode=False

def calc_temp_pathspec(src_file, stage, temp_dir):
    """
    >>> calc_temp_pathspec('/home/alex/tmp/video/something.vob', 'turbo.avi', '/tmp/tmpdir_xxx')
    '/tmp/tmpdir_xxx/something.turbo.avi'
    """
    (dir, file) = os.path.split(src_file)
    (base, extension) = os.path.splitext(file)
    final_path = temp_dir+"/"+base+"."+stage
    return final_path

def guess_best_crop(file):
    """
    Calculate the best cropping parameters to use by looking over the whole file
    """
    size = os.path.getsize(file)
    potential_crops = {}
    for i in range(0, size-size/20, size/20):
        crop_cmd = mplayer_bin+" -nosound -vo null -sb "+str(i)+" -frames 10 -vf cropdetect '"+file+"'"
#        if verbose:
#            print "Running: "+crop_cmd
        try:
            p = subprocess.Popen(crop_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            (out, err) = p.communicate()
            m = re.search("\-vf crop=[-0123456789:]*", out)
            if m:
                try:
                    potential_crops[m.group(0)]+=1
                except KeyError:
                    potential_crops[m.group(0)]=1
                    if verbose: print "Found Crop:"+m.group(0)

            m = re.search("(\d{2}\.\d*) fps", out)
            if m:
                global fps
                fps = m.group(0).split(" ")[0]
                print "Found FPS:"+fps

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

    # For cartoons post-processing median deinterlacer seems to help
    if cartoon:
        cmd = cmd + ",pp=md"
        
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

def package_mp4(src_file, temp_dir, dest_dir):
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
    if verbose: print "Handling: "+vob_file

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
        crop = guess_best_crop(vob_file)

    if verbose: print "Calculated crop of %s for %s" % (crop, vob_file)

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
        package_mp4(ff, temp_dir, dir)
        os.chdir(start_dir)
        if not debug:
            for tf in temp_files:
                os.unlink(tf)
            shutil.rmtree(temp_dir)
    else:
        print "Cannot package, no file encoded"


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
        opts, args = getopt.getopt(sys.argv[1:], "hvdnstp:a:cf", ["help", "verbose", "debug", "no-crop", "skip-encode", "passes=", "test", "slang=", "alang=", "progress", "pkg", "cartoon", "film", "bitrate=", "unit-tests"])
    except getopt.GetoptError, err:
        usage()

    create_log=None

    for o,a in opts:
        if o in ("-h", "--help"):
            usage()
            exit
        if o in ("-v", "--verbose"):
            verbose=True
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
            bitrate=1500
            cartoon=True
        if o in ("-f", "--film"):
            bitrate=3000
        if o in ("--bitrate"):
            bitrate=a
        if o in ("-t", "--test"):
            test=True
        if o is ("--slang"):
            subtitle=a
        if o is ("--alang"):
            language=a
        if o is ("--progress"):
            print "setting progress from (%s)" % (o)
            progress=True
        if o is ("--pkg"):
            package_only=True
        if o is ("--unit-tests"):
            import doctest
            doctest.testmod()
            exit()
            

    # Calculate the full paths ahead of time (lest cwd changes)
    files = []
    for a in args:
        fp = os.path.realpath(a)
        files.append(fp)

    for f in files:
        if verbose: print "Processing: %s package only=%s" % (f, package_only)
        
        if package_only:
            package_mp4(f)
        else:
            process_input(f)
        
