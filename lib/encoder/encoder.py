#!/usr/bin/python
#
# Encoder base class

import os
import subprocess
import shlex
import logging
logger = logging.getLogger("ps3enc.encoder")

# Some exceptions
class EncoderException(Exception):
    def __init__(self, reason):
        self.reason = reason
    def __str__(self):
        return repr(self.reason)

class encoder(object):

    def __init__(self, args, src_file, crop=""):
        self.args = args
        self.src_file = src_file
        self.crop = crop
        logger.info("created an encoder for %s (%s, %s)" %
                    (self.src_file, self.args, self.crop))

    def __str__(self):
        return "null encoder"

    def run(self, command, dst_file):
        if self.args.skip_encode and os.path.exists(dst_file):
            logger.info("Skipping generation of: "+dst_file)
        else:
            logger.debug("running: %s" % (command))
            args = shlex.split(command)
            p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            while p.returncode == None:
                status = p.stdout.readlines(4096)

                if status:
                    if self.args.verbose:
                        line = status[-1]
                        if line.startswith("Pos:"):
                            line.rstrip()
                            sys.stdout.write("\r"+line)
                            sys.stdout.flush()
                else:
                    break
            
            # Grab final bits
            (out, err) = p.communicate()
            logger.debug("complete with %d (%s)" % (p.returncode, err))
            if p.returncode != 0:
                raise EncoderException("encode failed ((%d/%s)" % (p.returncode, out))

        if os.path.exists(dst_file):
            return dst_file
        else:
            raise EncoderException("Missing output file: %s" % dst_file)
