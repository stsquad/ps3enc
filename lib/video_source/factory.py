#!/usr/bin/python
#
#
# Video source factory
#
from avi import avi
from dvd import dvd
from mplayer import mplayer

def get_video_source(filename, args):
    if filename.endswith("avi"):
        return avi(filename, args)
    elif filename.endswith("vob"):
        return avi(filename, args)
    elif filename.startswith("dvd://"):
        return dvd(filename, args)
    else:
        return mplayer(filename, args)
