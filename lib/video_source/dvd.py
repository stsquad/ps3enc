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

import sys
import subprocess
import re
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

from video_source import video_options
# from video_source.mplayer import mplayer
from mplayer import mplayer
import logging
logger = logging.getLogger("ps3enc.video_source.dvd")

class dvd(mplayer):
    """
    A video source is a wrapper around direct DVD access
    """

    def _alarm_handler(self, signum, frame):
        raise Alarm
    
    def __init__(self, filepath):
        """
        >>> args = video_options().parse_args(["-q", "dvd://2"])
        >>> x = dvd(args.files[0])
        >>> x.track
        2
        """
        super(dvd, self).__init__(filepath, real_file=False)
        if filepath.startswith("dvd://"):
            self.track = int(filepath.strip("dvd://"))
        
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
    parser = video_options()
    args = parser.parse_args()

    if args.unit_tests:
        import doctest
        doctest.testmod()
    else:
        print "falling through"
        
    for a in args.files:
        if a.startswith("dvd://") or a.endswith(".vob"):
            v = video_source_dvd(a, args, class_logger)
        else:
            print "video_source_dvd: for DVD files"
            exit -1
        if args.identify:
            v.identify_video()
        if args.analyse:
            v.analyse_video()
        print v
        
        




