#!/usr/bin/python
#
#
# Video source factory
#
from video_source_avi import video_source_avi
from video_source_dvd import video_source_dvd
#from video_source_mkv import video_source_mkv

def get_video_source(filename, verbose=False):
    print "get_video_source(%s)" % (filename)
    if filename.endswith("avi"):
        return video_source_avi(filename, verbose)
    elif filename.endswith("vob"):
        return video_source_avi(filename, verbose)
    elif filename.startswith("dvd://"):
        return video_source_dvd(filename, verbose)
    else:
        return None
