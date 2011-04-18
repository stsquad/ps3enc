#!/usr/bin/python
#
# Query a video file and pull out various bits of information that will be useful
# for later encoding
#
# (C)opyright 2011 Alex Bennee <alex@bennee.com>
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

mplayer_bin="/usr/bin/mplayer"

# This is for unit testing...
test_output="""
Trying demuxer 2 based on filename extension
system stream synced at 0xD (13)!
==> Found video stream: 0
==> Found audio stream: 128
==> Found audio stream: 129
==> Found audio stream: 130
MPEG-PS file format detected.
Searching for sequence header... OK!
VIDEO:  MPEG2  720x576  (aspect 3)  25.000 fps  9800.0 kbps (1225.0 kbyte/s)
[V] filefmt:2  fourcc:0x10000002  size:720x576  fps:25.000  ftime:=0.0400
"""

test_crop_output="""
A:   2.1 V:   2.1 A-V:  0.000 ct:  0.032  48/ 48  4%  5%  0.3% 0 0 
[CROP] Crop area: X: 0..719  Y: 170..404  (-vf crop=720:224:0:176).
A:   2.2 V:   2.2 A-V:  0.000 ct:  0.032  49/ 49  4%  5%  0.3% 0 0 
[CROP] Crop area: X: 0..719  Y: 120..453  (-vf crop=720:320:0:128).
A:   2.2 V:   2.2 A-V:  0.000 ct:  0.032  50/ 50  4%  5%  0.3% 0 0 
[CROP] Crop area: X: 0..719  Y: 77..499  (-vf crop=720:416:0:82).
A:   2.2 V:   2.2 A-V:  0.002 ct:  0.032  51/ 51  4%  5%  0.3% 0 0 
[CROP] Crop area: X: 0..719  Y: 0..573  (-vf crop=720:560:0:8).
A:   2.3 V:   2.3 A-V:  0.000 ct:  0.032  52/ 52  4%  5%  0.3% 0 0 
[CROP] Crop area: X: 0..719  Y: 0..573  (-vf crop=720:560:0:8).
A:   2.3 V:   2.3 A-V:  0.000 ct:  0.032  53/ 53  4%  5%  0.3% 0 0 
[CROP] Crop area: X: 0..719  Y: 0..573  (-vf crop=720:560:0:8).
A:   2.4 V:   2.4 A-V:  0.000 ct:  0.032  54/ 54  4%  5%  0.3% 0 0
"""

class video_source(object):
    """
    A video source is a wrapper around a video file
    """
    verbose=False
    
    # internal values, file related
    dir=None
    file=None
    base=None
    extension=None
    size=None

    # mplayer parameters
    fps=None

    audio_tracks = []

    # Crop calculation
    crop_spec=None
    potential_crops = {}

    def __init__(self, path, verbose=False):
        """
        >>> x = video_source('/path/to/file.avi')
        >>> x.dir
        '/path/to'
        >>> x.file
        'file.avi'
        >>> x.base
        'file'
        >>> x.extension
        '.avi'
        """
        self.path = path
        if (verbose): print "video_source(%s)" % (self.path)
        (self.dir, self.file) = os.path.split(self.path)
        (self.base, self.extension) = os.path.splitext(self.file)

    def __str__(self):
        return "File: %s, crop(%s), %s FPS" % (self.file, self.crop_spec, self.fps)

    def analyse_video(self):
        if os.path.exists(path):
            self.size = os.path.getsize(path)
            self.sample_video()


    def extract_crop(self, out):
        """
        >>> x = video_source('/path/to/file')
        >>> x.extract_crop(test_output)
        >>> print x.fps
        25.000
        """
        m = re.search("\-vf crop=[-0123456789:]*", out)
        if m:
            try:
                self.potential_crops[m.group(0)]+=1
            except KeyError:
                self.potential_crops[m.group(0)]=1
                if self.verbose: print "Found Crop:"+m.group(0)
        
    def extract_fps(self, out):
        """
        >>> x = video_source('/path/to/file')
        >>> x.extract_fps(test_output)
        >>> print x.fps
        25.000
        """
        m = re.search("(\d{2}\.\d*) fps", out)
        if m:
            self.fps = m.group(0).split(" ")[0]
        
    def extract_audio(self, out):
        return

    def sample_video(self):
        """
        Calculate the best cropping parameters to use by looking over the whole file
        """
        for i in range(0, self.size-self.size/20, self.size/20):
            crop_cmd = mplayer_bin+" -v -nosound -vo null -sb "+str(i)+" -frames 10 -vf cropdetect '"+self.path+"'"
            try:
                p = subprocess.Popen(crop_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
                (out, err) = p.communicate()
                extract_crop(out)
                if self.fps is None:
                    extract_fps(out)
                if len(self.audio_tracks)==0:
                    extract_audio(out)

            except OSError:
                print "Failed to spawn: "+crop_cmd

        # most common crop?
        crop_count = 0
        for crop  in potential_crops:
            if potential_crops[crop] > crop_count:
                crop_count = potential_crops[crop]
                self.crop_spec = crop

        if verbose:
            print "Crop to use is:"+self.crop_spec


# Testing code
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "v", ["verbose"])
    except getopt.GetoptError, err:
        usage()

    for o,a in opts:
        if o in ("-v", "--verbose"):
            verbose=True

    if len(args)>=1:
        for a in args:
            fp = os.path.realpath(a)
            v = video_source(fp, verbose)
            v.analyse_video()
            print v
    else:
        import doctest
        doctest.testmod()
        
        
