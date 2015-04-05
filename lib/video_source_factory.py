#!/usr/bin/python
#
#
# Video source factory
#
from video_source_avi import video_source_avi
from video_source_dvd import video_source_dvd
from video_source_mplayer import video_source_mplayer

def get_video_source(filename):
    if filename.endswith("avi"):
        return video_source_avi(filename)
    elif filename.endswith("vob"):
        return video_source_avi(filename)
    elif filename.startswith("dvd://"):
        return video_source_dvd(filename)
    else:
        return video_source_mplayer(filename)
