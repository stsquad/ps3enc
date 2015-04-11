#!/usr/bin/python
#
#
# Video source factory
#
from avi import avi
from dvd import dvd
from mplayer import mplayer

def get_video_source(filename):
    if filename.endswith("avi"):
        return avi(filename)
    elif filename.endswith("vob"):
        return avi(filename)
    elif filename.startswith("dvd://"):
        return dvd(filename)
    else:
        return mplayer(filename)
