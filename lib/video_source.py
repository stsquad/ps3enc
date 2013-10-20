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
import subprocess

# Logging, use this if none passed in
from video_logging import setup_logging
import logging
class_logger = logging.getLogger("video_source")

class video_source(object):
    """
    A video source is a wrapper around a video file
    """
    def __init__(self, path, args, logger=class_logger, real_file=True):
        """
        >>> args = video_options().parse_args(["-q", "/path/to/file.avi"])
        >>> x = video_source('/path/to/file.avi', args, class_logger)
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
        self.args = args
        self.logger = logger
        self.logger.info("video_source(%s)" % (self.path))
        if self.args.dump:
            self.dump = open(self.args.dump, "w")
        else:
            self.dump = None

        # calculated values
        self.crop_spec=None
        self.fps=None
        self.video_codec=None
        self.audio_codec=None
        self.audio_tracks=None
        self.size = None

        if real_file:
            (self.dir, self.file) = os.path.split(self.path)
            (self.base, self.extension) = os.path.splitext(self.file)
        else:
            self.logger.warning("treating filepath as 'fake': %s" % (self.path))


    def __str__(self):
        """
        >>> args = video_options().parse_args(["-q", "/path/to/fake/file.avi"])
        >>> x = video_source(args.files[0], args, class_logger)
        >>> print x.file
        file.avi
        >>> print x
        File: file.avi
        """
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

    def filepath(self):
        """
        >>> args = video_options().parse_args(["-q", "/path/to/fake/file.avi"])
        >>> x = video_source(args.files[0], args, class_logger)
        >>> x.filepath()
        '/path/to/fake/file.avi'
        """
        return "%s/%s" % (self.dir, self.file)

    def analyse_video(self):
        """
        The most basic analysis, check file size
        """
        if os.path.exists(self.path):
            self.size = os.path.getsize(self.path)
        return

        
    def run_cmd(self, command):
        self.logger.debug("running command %s" % (command))
        try:
            p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            (out, err) = p.communicate()
            if self.dump:
                self.dump.write(out)
            if p.returncode == 0:
                return (out,err)
            else:
                self.logger.error("command %s failed with %d (%s)\n" % (command, p.returncode, err))
        except OSError:
            self.logger.error("failed to spawn: "+command)

        return (out,err)
        


#
# Shared option code
#
from argparse import ArgumentParser

def video_options():
    parser=ArgumentParser(description="Video Source analysis options")
    parser.add_argument('files', metavar='FILE_TO_ANALYSE', nargs='+', help='Files to analyse')

    output_options = parser.add_argument_group("Logging and output")
    output_options.add_argument('-v', '--verbose', action='count', default=None, help='Be verbose in output')
    output_options.add_argument('-q', '--quiet', action='store_false', dest='verbose', help="Supress output")
    output_options.add_argument('-l', '--log', default=None, help="output to a log file")
    output_options.add_argument('-d', '--dump', default=None, help="dump data from runs to file")

    source_actions = parser.add_argument_group('Actions')
    source_actions.add_argument("-i", "--identify",
                                dest="identify",
                                action="store_true",
                                default=True,
                                help="do a simple analysis of the media files")

    source_actions.add_argument("-a", "--analyse",
                                dest="analyse",
                                action="store_true",
                                default=False,
                                help="perform deeper analysis of the file")

    unit_test_actions = parser.add_argument_group('Unit Testing')
    unit_test_actions.add_argument("--unit-tests", action="store_true", default=False, help="Run modules unit tests")

    return parser
    

# Testing code
if __name__ == "__main__":
    parser = video_options()
    args = parser.parse_args()
    setup_logging(class_logger, args)

    for a in args.files:
        fp = os.path.realpath(a)
        v = video_source(fp, args, class_logger)
        v.analyse_video()
        print v









