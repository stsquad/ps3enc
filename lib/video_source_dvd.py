#!/usr/bin/python
#
# Query an DVD for track information
#
# This is only really useful when we have failed to rip the VOB file for
# off-line ripping. There are some cases where mplayer/mencoder can play
# the direct stream fine but fail when trying to dump the stream. This
# analyser is to support ripping in this case
#
# (C)opyright 2012 Alex Bennee <alex@bennee.com>
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
import signal

# for timeouts
class Alarm(Exception):
    pass

mplayer_bin="/usr/bin/mplayer"

crop_test_output="""
[CROP] Crop area: X: 7..712  Y: 77..492  (-vf crop=704:400:8:86).
V: 566.7 14164/14164  3%  0%  0.0% 0 0 
[CROP] Crop area: X: 7..712  Y: 77..492  (-vf crop=704:400:8:86).
V: 566.8 14165/14165  3%  0%  0.0% 0 0 
[CROP] Crop area: X: 7..712  Y: 77..492  (-vf crop=704:400:8:86).
V: 566.8 14166/14166  3%  0%  0.0% 0 0 
[CROP] Crop area: X: 7..712  Y: 77..492  (-vf crop=704:400:8:86).
V: 566.8 14167/14167  3%  0%  0.0% 0 0 
[CROP] Crop area: X: 7..712  Y: 77..492  (-vf crop=704:400:8:86).
V: 566.9 14168/14168  3%  0%  0.0% 0 0 
[CROP] Crop area: X: 7..712  Y: 77..492  (-vf crop=704:400:8:86).
V: 566.9 14169/14169  3%  0%  0.0% 0 0 
[CROP] Crop area: X: 7..712  Y: 77..492  (-vf crop=704:400:8:86).
V: 567.0 14170/14170  3%  0%  0.0% 0 0 
[CROP] Crop area: X: 7..712  Y: 77..494  (-vf crop=704:416:8:78).
V: 567.6 14185/14185  3%  0%  0.0% 0 0 
[CROP] Crop area: X: 7..712  Y: 77..494  (-vf crop=704:416:8:78).
V: 567.6 14186/14186  3%  0%  0.0% 0 0 
[CROP] Crop area: X: 7..712  Y: 77..494  (-vf crop=704:416:8:78).
V: 567.6 14187/14187  3%  0%  0.0% 0 0 
[CROP] Crop area: X: 7..712  Y: 77..494  (-vf crop=704:416:8:78).
V: 567.7 14188/14188  3%  0%  0.0% 0 0 
[CROP] Crop area: X: 7..712  Y: 77..494  (-vf crop=704:416:8:78).
V: 567.7 14189/14189  3%  0%  0.0% 0 0 
[CROP] Crop area: X: 7..712  Y: 77..494  (-vf crop=704:416:8:78).
V: 567.8 14190/14190  3%  0%  0.0% 0 0 
[CROP] Crop area: X: 7..712  Y: 77..494  (-vf crop=704:416:8:78).
V: 567.8 14191/14191  3%  0%  0.0% 0 0 
[CROP] Crop area: X: 7..712  Y: 77..494  (-vf crop=704:416:8:78).
V: 567.8 14192/14192  3%  0%  0.0% 0 0 
[CROP] Crop area: X: 7..712  Y: 77..494  (-vf crop=704:416:8:78).
V: 567.9 14193/14193  3%  0%  0.0% 0 0 
[CROP] Crop area: X: 7..712  Y: 77..494  (-vf crop=704:416:8:78).
V: 567.9 14194/14194  3%  0%  0.0% 0 0 
[CROP] Crop area: X: 7..712  Y: 77..494  (-vf crop=704:416:8:78).
V: 568.0 14195/14195  3%  0%  0.0% 0 0 
"""

from video_source_mplayer import video_source_mplayer

class video_source_dvd(video_source_mplayer):
    """
    A video source is a wrapper around direct DVD access
    """

    def _alarm_handler(self, signum, frame):
        raise Alarm
    
    def __init__(self, path, verbose=False):
        """
        >>> x = video_source_dvd('dvd://2')
        >>> x.track
        2
        """
        self.path = path
        self.verbose = verbose
        if (self.verbose): print "video_source(%s)" % (self.path)


    def extract_crop(self, out):
        """
        >>> x = video_source_dvd('/path/to/file')
        >>> x.extract_crop(crop_test_output)
        >>> print x.crop_spec
        "-vf crop=704:416:8:78"
        """
        m = re.findall("\-vf crop=[-0123456789:]*", out)
        if m:
            total = len(m)
            keep = int(total/2)
            film_matches = m[keep:]
            if self.verbose: print "found %d crop descriptions, keeping %d" % (total, keep)
            for match in film_matches:
                try:
                    self.potential_crops[match]+=1
                except KeyError:
                    self.potential_crops[match]=1
        
    def sample_video(self):
        """
        Calculate the best cropping parameters to use by looking over the whole file
        """
        signal.signal(signal.SIGALRM, self._alarm_handler)

        crop_cmd = mplayer_bin+" -v -nosound -vo null -endpos 10:00 -vf cropdetect '"+self.path+"'"
        if self.verbose: print "doing sample step: %s" % (crop_cmd)
        p = subprocess.Popen(crop_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        (out, err) = p.communicate()
        print "out=%s" % (out)
        self.extract_crop(out)

        # most common crop?
        crop_count = 0
        for crop  in self.potential_crops:
            print "checking crop: %s" % (crop)
            if self.potential_crops[crop] > crop_count:
                crop_count = self.potential_crops[crop]
                self.crop_spec = crop

        if self.verbose: print "sample_video: crop is "+self.crop_spec



# Testing code
if __name__ == "__main__":
    from video_source import video_options
    (parser, options, args) = video_options()

    if len(args)>=1:
        for a in args:
            if a.startswith("dvd://"):
                v = video_source_dvd(a, options.verbose)
            if options.identify:
                v.identify_video()
            if options.analyse:
                v.analyse_video()
            print v
    else:
        import doctest
        doctest.testmod()
        
        
