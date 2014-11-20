#!/usr/bin/python
#
#
# Video source factory
#
from video_source_avi import video_source_avi
from video_source_dvd import video_source_dvd
from video_source_mplayer import video_source_mplayer

def get_video_source(filename, logger):
    logger.debug("get_video_source(%s)" % (filename))
    if filename.endswith("avi"):
        return video_source_avi(filename, logger)
    elif filename.endswith("vob"):
        return video_source_avi(filename, logger)
    elif filename.startswith("dvd://"):
        return video_source_dvd(filename, logger)
    else:
        return video_source_mplayer(filename, logger)
