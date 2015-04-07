#!/usr/bin/python
#
# Encode DVD's (and other sources) into a version of MP4 that a PS3 can use
#
# Based on my ps3enc.pl (perl version) which was...
# originally based on Carlos Rivero's GPL bash script
# (http://subvida.com/2007/06/18/convert-divx-xvid-to-ps3-format-mpeg4-on-linux/)
#
# (C)opyright 2010,2011,2012,2013 Alex Bennee <alex@bennee.com>
#
# Licenced under the GPL version 3 Which means no warrenty! Break it
# you get to keep both pieces, fix it then please send me the glue :-)
#

import os
import sys
import subprocess
import shlex
import shutil
import tempfile
import logging

from datetime import date
from argparse import ArgumentParser

# Logging
logger = logging.getLogger("ps3enc")

# Handy for running in place
from os.path import realpath,dirname
script=realpath(sys.argv[0])
devlibs=dirname(script)+"/lib"
if os.path.exists(devlibs):
    logger.info("Adding "+devlibs+" to path")
    sys.path.insert(0, devlibs)
else:
    logger.info("sys.argv[0] is %s" % (realpath(dirname(sys.argv[0]))))

from video_source_factory import get_video_source
from encoder.encoder import EncoderException
from encoder.mencoder import mencoder
from encoder.ffmpeg import ffmpeg
from encoder.mpv import mpv

mplayer_bin="/usr/bin/mplayer"
mp4box_bin="/usr/bin/MP4Box"

me=os.path.basename(sys.argv[0])
#
# Command line options
#
parser=ArgumentParser(description='Encode video files for the PS3 native player.',
                      epilog="""The script is designed to be easily scriptable for
batch processing of encode requests. The final output is an MP4 that should play
by default on the PS3 games systems built-in video player""")

parser.add_argument('files', metavar='FILE_TO_ENCODE', nargs='+', help='File to encode')
parser.add_argument('-n', '--no-crop', dest="no_crop", action="store_true", default=False, help="Don't try and crop the source")
parser.add_argument('-s', '--skip-encode', dest="skip_encode", action="store_true", help="Skip encode and package if files are there")

output_options = parser.add_argument_group("Logging and output")
output_options.add_argument('-v', '--verbose', action='count', default=None, help='Be verbose in output')
output_options.add_argument('-q', '--quiet', action='store_false', dest='verbose', help="Supress output")
output_options.add_argument('-l', '--log', default=None, help="output to a log file")
output_options.add_argument('-d', '--dump', default=None, help="dump data from runs to file")
output_options.add_argument('--debug', action='store_true', default=False, help="Debug mode, don't delete temp files")

encode_options = parser.add_argument_group('Encoding control')
encode_options.add_argument('-e', '--encoder', default="ffmpeg", help="encoder to use (default ffmpeg)")
encode_options.add_argument('-b', '--bitrate', metavar="n", type=int, dest="video_bitrate", default=2000, help="video encoding bitrate")
encode_options.add_argument('--audio_bitrate', metavar="n", type=int, dest="audio_bitrate", default=192, help="audio encoding bitrate")
encode_options.add_argument('-p', '--passes', metavar="n", type=int, default=1, help="Number of encoding passes (default 1)")
encode_options.add_argument('-c', '--cartoon', action="store_true", help="Assume we are encoding a cartoon (lower bitrate + filters)")
encode_options.add_argument('-f', '--film', dest="video_bitrate", action="store_const", const=3000,
                            help="Assume we are encoding a film (higher bitrate)")
encode_options.add_argument('--hdfilm', dest="video_bitrate", action="store_const", const=5000,
                            help="Assume we are encoding a HD film (even higher bitrate)")
encode_options.add_argument('-t', '--test', action="store_true", help="Do a test segment")
encode_options.add_argument('-a', '--alang', type=int, default=None, help="Select different audio channel")
encode_options.add_argument('--slang', dest="slang", type=int, default=-1, help="Bake in language subtitles")

package_options = parser.add_argument_group('Packaging')
package_options.add_argument('--pkg', action="store_true", help="Don't encode, just package files into MP4")

dev_options = parser.add_argument_group('Developer options')
dev_options.add_argument('--valgrind', action="store_true", help="Run the encode under valgrind (to debug mplayer)")

import code, traceback, signal

def debug(sig, frame):
    """Interrupt running process, and provide a python prompt for
    interactive debugging."""
    d={'_frame':frame}         # Allow access to frame object.
    d.update(frame.f_globals)  # Unless shadowed by global
    d.update(frame.f_locals)

    i = code.InteractiveConsole(d)
    message  = "Signal recieved : entering python shell.\nTraceback:\n"
    message += ''.join(traceback.format_stack(frame))
    i.interact(message)

def listen():
    signal.signal(signal.SIGUSR1, debug)

def setup_logging(args):
    # setup logging
    if args.verbose:
        if args.verbose == 1: logger.setLevel(logging.INFO)
        if args.verbose >= 2: logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARNING)
        
    if args.log:
        handler = logging.FileHandler(args.log)
    else:
        handler = logging.StreamHandler()

    lfmt = logging.Formatter('%(asctime)s:%(levelname)s - %(name)s - %(message)s')
    handler.setFormatter(lfmt)
    logger.addHandler(handler)

    logger.info("running with level %s" % (logger.getEffectiveLevel()))

def calc_temp_pathspec(src_file, stage, temp_dir):
    """
    Simple helper function for calculating temporary filenames
    >>> calc_temp_pathspec('/home/alex/tmp/video/something.vob', 'turbo.avi', '/tmp/tmpdir_xxx')
    '/tmp/tmpdir_xxx/something.turbo.avi'
    """
    (dir, file) = os.path.split(src_file)
    (base, extension) = os.path.splitext(file)
    final_path = temp_dir+"/"+base+"."+stage
    return final_path


def package_mp4(arg, src_file, temp_dir, dest_dir, fps=None):
    """
    Package a given AVI file into clean MP4
    """
    global args
    (dir, file) = os.path.split(src_file)
    (base, extension) = os.path.splitext(file)

    logger.info("package_mp4: (%s:%s) -> (%s:%s)\n" % (dir, file, base, extension))

    # Do this all in the work directory
    os.chdir(temp_dir)
    
    # Final file names
    video_file = calc_temp_pathspec(src_file, "video.h264", temp_dir)
    audio_file = calc_temp_pathspec(src_file, "audio.aac", temp_dir)
    final_file = dest_dir+"/"+base+".mp4"

    # Get video
    mp4_video_cmd = mp4box_bin+" -aviraw video '"+src_file+"'";
    logger.info("Running: "+mp4_video_cmd)
    p = subprocess.Popen(mp4_video_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    (out, err) = p.communicate()
    if p.returncode != 0:
        logger.error("Failed MP4 video extraction (%d/%s)" % (p.returncode, out))
        exit(-1)

    os.rename(base+"_video.h264", video_file)

    # Get Audio
    mp4_audio_cmd = mp4box_bin+" -aviraw audio '"+src_file+"'";
    logger.info("Running: "+mp4_audio_cmd)
    p = subprocess.Popen(mp4_audio_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    (out, err) = p.communicate()
    if p.returncode != 0:
        logger.error("Failed MP4 audio extraction (%d/%s)" % (p.returncode, out))
        exit(-1)

    os.rename(base+"_audio.raw", audio_file);

    # Join the two together
    mp4_join_cmd = mp4box_bin+" "
    if fps:
        mp4_join_cmd = mp4_join_cmd+"-fps "+str(fps)+" "
    mp4_join_cmd = mp4_join_cmd+" -add '"+audio_file+"' -add '"+video_file+"' '"+final_file+"'"

    logger.info("Running: "+mp4_join_cmd)
    p = subprocess.Popen(mp4_join_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    (out, err) = p.communicate()
    if p.returncode != 0:
        logger.error("Failed MP4 join step (%d/%s)" % (p.returncode, out))
        exit(-1)

    if not args.debug:
        os.unlink(video_file)
        os.unlink(audio_file)

    return


# Process a single VOB file into final MP4
def process_input(args, vob_file):
    logger.info("process_input: "+vob_file)

    video = get_video_source(vob_file)
    video.analyse_video()

    # Save were we are
    if vob_file.startswith("dvd://"):
        dir="%s/tmp/encode_%s" % (os.getenv("HOME"), date.today())
        os.mkdir(dir)
    else:
        (dir, file) = os.path.split(vob_file)
        (base, extension) = os.path.splitext(file)

    start_dir = os.getcwd()
    
    # Temp files
    temp_dir = tempfile.mkdtemp("encode", "video")
    os.chdir(temp_dir)
    
    temp_files = [temp_dir+"/divx2pass.log"]

    if args.no_crop or args.encoder == "mencoder":
        crop = ""
    else:
        crop = video.crop_spec
        logger.info("Calculated crop of %s for %s" % (crop, vob_file))

    if args.encoder == "mencoder":
        encoder = mencoder(args, vob_file, crop)
    elif args.encoder == "mpv":
        encoder = mpv(args, vob_file, crop)
    else:
        encoder = ffmpeg(args, vob_file)

    try:
        if args.passes>1:
            tf = calc_temp_pathspec(vob_file, "turbo", temp_dir)
            temp_files.append(encoder.turbo_pass(tf))
            for i in range(2, args.passes+1):
                tf = calc_temp_pathspec(vob_file, "pass"+str(i), temp_dir)
                temp_files.append(encoder.encoding_pass(tf, i))
        else:
            tf = calc_temp_pathspec(vob_file, "singlepass", temp_dir)
            temp_files.append(encoder.encoding_pass(tf))


        ff = temp_files[-1]
        logger.info("Final encode of %s is %s" % (vob_file, ff))

        if os.path.exists(ff):
            if ff.endswith(".avi"):
                logger.info("Repackage final file is: %s", (ff))
                package_mp4(args, ff, temp_dir, dir, video.fps)
                os.chdir(start_dir)
            else:
                logger.info("Copy final file: %s", (ff))
                shutil.move(ff, start_dir)
                
            if not args.debug:
                for tf in temp_files:
                    os.unlink(tf)
                    shutil.rmtree(temp_dir)
    except Exception as e:
        logger.warning("error: %s" % str(e))


# Start of code
if __name__ == "__main__":
    args = parser.parse_args()
    setup_logging(args)

    if args.debug:
        print ("Debugging enabled on SIGUSR1")
        listen()

    if args.cartoon:
        args.passes=1
        args.video_bitrate=1500

    logger.debug("args: %s" % (args))
            
    # Calculate the full paths ahead of time (lest cwd changes)
    files = []
    for a in args.files:
        if a.startswith("dvd://"):
            files.append(a)
        else:
            fp = os.path.realpath(a)
            files.append(fp)
 
    for f in files:
        if args.pkg:
            package_mp4(args, f)
        else:
            process_input(args, f)
        
