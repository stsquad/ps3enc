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

    # calculated values
    crop_spec=None
    fps=None
    video_codec=None
    audio_codec=None
    tracks=None

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
        self.verbose = verbose
        if (self.verbose): print "video_source(%s)" % (self.path)
        (self.dir, self.file) = os.path.split(self.path)
        (self.base, self.extension) = os.path.splitext(self.file)

    def filepath(self):
        return "%s/%s" % (self.dir, self.file)

    def __str__(self):
        result = []
        if self.file:
            result.append("File: %s" % (self.file))
        if self.video_codec:
            result.append("Video: %s" % (self.video_codec))
        if self.audio_codec:
            result.append("Audio: %s" % (self.audio_codec))
        if self.audio_tracks:
            result.append("Tracks: %s" % (self.audio_tracks))
        if self.crop_spec:
            result.append("Crop: %s" % (self.crop_spec))
        if self.fps:
            result.append("FPS: %s" % (self.fps))
            
        return ", ".join(result)


#
# Shared option code
#
from optparse import OptionParser

def video_options():
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

    parser.add_option("-i", "--identify",
                      dest="identify",
                      action="store_true",
                      default=True,
                      help="do a simple analysis of the media files")

    parser.add_option("-a", "--analyse",
                      dest="analyse",
                      action="store_true",
                      default=False,
                      help="perform deeper analysis of the file")

    (options, args) = parser.parse_args()
    return (parser, options, args)

        

# Testing code
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "v", ["verbose"])
    except getopt.GetoptError, err:
        usage()

    verbose=False
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
        
        
