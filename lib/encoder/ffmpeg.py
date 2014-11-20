#!/usr/bin/python
#
# FFMPEG Wrapper

import subprocess
import shlex
import os
import logging
logger = logging.getLogger("ps3enc.ffmpeg")

from encoder import encoder
ffmpeg_bin="/usr/bin/ffmpeg"

# Some exceptions
class ffmpegException(Exception):
    def __init__(self, reason):
        self.reason = reason
    def __str__(self):
        return repr(self.reason)

class ffmpeg(encoder):
    """
    Helper object to wrap around ffmpeg calls. Instantiate one per
    file to be encoded
    """

    def __init__(self, args, src_file, crop=""):
        self.args = args
        self.src_file = src_file
        self.crop = crop


    def build_cmd(self, dst_file, encode_audio=False, epass=1):
        """
        return a ffmpeg command string
        """
        cmd = "%s -y -i '%s'" % (ffmpeg_bin, self.src_file)

        cmd = "%s -pass %d " % (cmd, epass)

        # general encoding options
        cmd = cmd + "-vcodec libx264 -profile:v baseline -level 3.0 -crf 24 -threads 0"

        # position
        if self.args.test:
            cmd = cmd + " -ss 20:00 -t 120 "
        # if self.args.slang >= 0:
        #     cmd = "%s -sid %d" % (cmd, self.args.slang)
        # else:
        #     cmd = "%s -nosub " % (cmd)
        # if self.args.alang:
        #     cmd = "%s -aid %d" % (cmd, self.args.alang)

        # audio encoding
        # cmd = cmd + " -oac " + oac_args
        if encode_audio:
            cmd = "%s -acodec libfaac -ab 128k -ac 2 -ar 48000" % (cmd, self.args.audio_bitrate)
        else:
            cmd = cmd + " -c:a copy "

        # crop params
        # if self.crop:
        #     cmd = "%s %s" % (cmd, self.crop)

        # # harddump for remuxed streams
        # cmd = cmd + " -vf softskip,harddup"

        # # For cartoons post-processing median deinterlacer seems to help
        # if self.args.cartoon:
        #     cmd = cmd + ",pp=md"

        cmd = cmd + "'" + dst_file + "'"


        logger.debug("cmd: %s" % (cmd))

        return cmd

    def turbo_pass(self, dst_file):
        """
        Do a fast turbo pass encode of the file
        """
        turbo_cmd = self.build_cmd(dst_file, False, 1)
        return self.run(turbo_cmd, dst_file)

    def encoding_pass(self, dst_file, epass=1):
        """
        Normal multi-stage encoding pass
        """
        encode_cmd = self.build_cmd(dst_file, True, epass)
        return self.run(encode_cmd, dst_file)
