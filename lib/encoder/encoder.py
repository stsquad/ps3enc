#!/usr/bin/python
#
# Encoder base class

import logging
logger = logging.getLogger("ps3enc.encoder")

class encoder(object):

    def __init__(self, args, src_file, crop=""):
        self.args = args
        self.src_file = src_file
        self.crop = crop
        logger.info("created an encoder for %s (%s, %s)" %
                    (self.src_file, self.args, self.crop))

    def __str__(self):
        return "null encoder"
