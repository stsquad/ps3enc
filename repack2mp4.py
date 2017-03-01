#!/usr/bin/python
#
# Repack an ostensibly H.264 encoded file into an MP4 for the benefit of the PS3
#
# This is a re-pack rather than a re-encode (although audio might get re-encoded).
# The idea is to preserve the H.264 audio as much as I can.
#
# I looked at the following similar scripts when doing this:
#  * http://code.google.com/p/mkv2mp4/
#
# (C)opyright 2010 Alex Bennee <alex@bennee.com>
#
# Licenced under the GPL version 3 Which means no warrenty! Break it
# you get to keep both pieces, fix it then please send me the glue :-)
#

import os
import sys
import tempfile
import subprocess
from optparse import OptionParser


# Handy for running in place
from os.path import realpath,dirname
devlibs=realpath(dirname(sys.argv[0])+"/lib")
if os.path.exists(devlibs):
    print "Adding "+devlibs+" to path"
    sys.path.insert(0, devlibs)

from video_source import get_video_source

mp4box_bin="/usr/bin/MP4Box"

def calc_temp_pathspec(src_file, stage, temp_dir):
    """
    >>> calc_temp_pathspec('/home/alex/tmp/video/something.vob', 'turbo.avi', '/tmp/tmpdir_xxx')
    '/tmp/tmpdir_xxx/something.turbo.avi'
    """
    (dir, file) = os.path.split(src_file)
    (base, extension) = os.path.splitext(file)
    final_path = temp_dir+"/"+base+"."+stage
    return final_path

def mp4box_extract(video, tempdir, verbose=False, mode="video", extension="h264"):
    # Get video
    output = "%s/%s.%s" % (tempdir, video.base, extension)
    mp4_video_cmd = "%s -aviraw %s '%s' -out '%s'" % (mp4box_bin, mode, video.filepath(), output)
    if verbose:
        print "Running: "+mp4_video_cmd
    p = subprocess.Popen(mp4_video_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    (out, err) = p.communicate()

    output = "%s/%s_%s.%s" % (tempdir, video.base, mode, extension)
    return output

def repack_video(video, verbose=False):
    video.identify_video()
    if not video.video_codec.find("h264")>0:
        print "Can't re-pack a non-h264 video"
        return

    src_file = video.filepath()
    base = video.base
    
    # Temp files
    temp_dir = tempfile.mkdtemp("repack", "video")
    os.chdir(temp_dir)
    
    temp_files = [temp_dir+"/divx2pass.log"]

    extracted_video = mp4box_extract(video, temp_dir, verbose, mode="video", extension="h264");
    extracted_audio = mp4box_extract(video, temp_dir, verbose, mode="audio", extension="raw");

    # Check to see if we need to convert the audio?
    file_cmd = "file '%s'" % (extracted_audio)
    if verbose: print "Running: "+file_cmd
    p = subprocess.Popen(file_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    (out, err) = p.communicate()
    if out.find("AC-3") > 0:
        outfile = extracted_audio.replace("raw", "ac3")
        os.rename(extracted_audio, outfile)
        final_audio = extracted_audio.replace("raw", "aac")
        transcode="ffmpeg -i '%s' -acodec aac -ac 2 -ab 160000 '%s'" % (outfile, final_audio)
        if verbose: print "Running: "+transcode
        p = subprocess.Popen(transcode, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        (out, err) = p.communicate()
    else:
        print "error can't handle this audio type %s" % (out)
        return
    

    # Join the two together
    final_file = "%s/%s.mp4" % (video.dir, video.base)
    if video.fps:
        fps = "-fps "+str(video.fps)
    else:
        fps = ""

    mp4_join_cmd = "%s %s -add '%s' -add '%s' '%s'" % (mp4box_bin, fps, extracted_video, final_audio, final_file)
    if verbose:
        print "Running: "+mp4_join_cmd
    p = subprocess.Popen(mp4_join_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    (out, err) = p.communicate()
    if p.returncode != 0:
        print "Failed (%d/%s)" % (p.returncode, out)
        exit(-1)


def define_options():
    """
    Define options for code
    """
    
    parser = OptionParser()

    # Default options
    parser.add_option("-v",
                      "--verbose",
                      dest="verbose",
                      action="store_true",
                      default=True,
                      help="Be more verbose")

    parser.add_option("-q",
                      "--quiet",
                      dest="verbose",
                      action="store_false",
                      default=True,
                      help="Be fairly quiet about it")

    return parser

    
# Start of code
if __name__ == "__main__":
    parser = define_options()
    (options, args) = parser.parse_args()
            
    # Calculate the full paths ahead of time (lest cwd changes)
    files = []
    for a in args:
        fp = os.path.realpath(a)
        files.append(fp)

    for f in files:
        video = get_video_source(f)
        repack_video(video, options.verbose)
        
