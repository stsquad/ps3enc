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
        logger.info("build_cmd: %s, pass=%d" %(dst_file, epass))

        # If we are encoding subs we want a long probe to ensure we find the stream
        if self.args.slang >= 0:
            cmd = "%s -probesize 2G -analyzeduration 2G" % (ffmpeg_bin)
        else:
            cmd = "%s" % (ffmpeg_bin)

        # The input file
        cmd = "%s -y -i '%s'" % (cmd, self.src_file)
        logger.info("build_cmd: %s" % (cmd))

        # This assumes we encoding picture based subs (i.e. DVD subs)
        if self.args.slang >= 0:
            cmd = "%s -filter_complex \"[0:v][0:s:%d]overlay[hardsub]\" -map \"[hardsub]\"" % (cmd, self.args.slang-1)
        else:
            cmd = "%s -map 0:v " % (cmd)

        # For ffmpeg pass 2 is the final pass, pass 3 if we keep collecting data
        if self.args.passes > 1:
            if epass == self.args.passes:
                # final pass
                cmd = "%s -pass 2 " % (cmd)
            elif epass == 1:
                # turbos pass
                cmd = "%s -pass 1 " % (cmd)
            else:
                # nth pass
                cmd = "%s -pass 3 " % (cmd)
            cmd = cmd + "-vcodec mpeg4 -b:v 10M"
        else:
            # Single pass @ CRF
            cmd = "%s -pass %d " % (cmd, epass)
            cmd = cmd + "-vcodec libx264 -profile:v high -level 4.0 -crf 18"

        # use all the threads
        cmd = cmd + " -threads 0"
        logger.info("build_cmd: %s" % (cmd))

        # position
        if self.args.test:
            cmd = cmd + " -ss 20:00 -t 120 "

        logger.info("build_cmd: %s" % (cmd))

        # audio encoding
        if encode_audio:
            if self.args.alang:
                cmd = "%s -map 0:a:%d" % (cmd, self.args.alang - 1)
            else:
                cmd = "%s -map 0:a" % (cmd)
            cmd = "%s -acodec libfaac -ab 128k -ac 2 -ar 48000" % (cmd) #, self.args.audio_bitrate)
        else:
            cmd = cmd + " -an "
        logger.info("build_cmd: %s" % (cmd))


        # We can tune specifically for different sources
        if self.args.cartoon:
            cmd = cmd + " -tune animation"
        elif self.args.film:
            cmd = cmd + " -tune film"

        cmd = cmd + " '" + dst_file + "'"
        logger.info("build_cmd: %s" % (cmd))


        logger.debug("cmd: %s" % (cmd))

        return cmd

    def turbo_pass(self, dst_file):
        """
        Do a fast turbo pass encode of the file
        """
        dst_file = dst_file+".mp4"
        turbo_cmd = self.build_cmd(dst_file, False, 1)
        return self.run(turbo_cmd, dst_file)

    def encoding_pass(self, dst_file, epass=1):
        """
        Normal multi-stage encoding pass
        """
        dst_file = dst_file+".mp4"
        logger.info("encoding_pass: %s" % (dst_file))
        encode_cmd = self.build_cmd(dst_file, True, epass)
        return self.run(encode_cmd, dst_file)
