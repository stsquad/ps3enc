#!/usr/bin/python
#
# Mencoder Wrapper

# Some exceptions
class MencoderError(Exception):
    def __init__(self, reason):
        self.reason = reason
    def __str__(self):
        return repr(self.reason)

class mencoder(object):
    """
    Helper object to wrap around mencoder calls. Instantiate one per
    file to be encoded
    """

    def __init__(self, args, src_file, crop=""):
        self.args = args
        self.src_file = src_file
        self.crop = crop

    def run(self, command, dst_file):
        if self.args.skip_encode and os.path.exists(dst_file):
            logger.info("Skipping generation of: "+dst_file)
        else:
            logger.debug("running: %s" % (command))
            args = shlex.split(command)
            p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            while p.returncode == None:
                status = p.stdout.readlines(4096)

                if status and self.args.verbose:
                    line = status[-1]
                    if line.startswith("Pos:"):
                        line.rstrip()
                        sys.stdout.write("\r"+line)
                        sys.stdout.flush()
                    else:
                        break
            
            # Grab final bits
            (out, err) = p.communicate()
            logger.debug("mencoder complete with %d (%s)" % (p.returncode, err))
            if p.returncode != 0:
                raise MencoderError("mencoder failed ((%d/%s)" % (p.returncode, out))

        if os.path.exists(dst_file):
            return dst_file
        else:
            raise MencoderError("Missing output file: %s" % dst_file)

    def build_cmd(self, dst_file, encode_audio=False, epass=1):
        """
        return a mencoder command string
        """
        cmd = "%s -v '%s'" % (mencoder_bin, self.src_file)

        # Do we want to valgrind it?
        if self.args.valgrind:
            (dir, file) = os.path.split(self.src_file)
            (base, extension) = os.path.splitext(file)
            log_file="%s/%s-valgrind-pass%d.log" % (dir, base, epass)
            cmd = "valgrind --trace-children=yes --log-file=%s %s" % (log_file, cmd)

        # position
        if self.args.test:
            cmd = cmd + " -ss 20:00 -endpos 120 "
        if self.args.slang >= 0:
            cmd = "%s -sid %d" % (cmd, self.args.slang)
        else:
            cmd = "%s -nosub " % (cmd)
        if self.args.alang:
            cmd = "%s -aid %d" % (cmd, self.args.alang)

        # audio encoding
        # cmd = cmd + " -oac " + oac_args
        if encode_audio:
            cmd = "%s -oac faac -faacopts mpeg=4:object=2:br=%d" % (cmd, self.args.audio_bitrate)
        else:
            cmd = cmd + " -oac copy "

        # crop params
        if self.crop:
            cmd = "%s %s" % (cmd, self.crop)

        # harddump for remuxed streams
        cmd = cmd + " -vf softskip,harddup"

        # For cartoons post-processing median deinterlacer seems to help
        if self.args.cartoon:
            cmd = cmd + ",pp=md"


        # x264 video encoding...
        # x264_encode_opts="-x264encopts subq=6:bframes=3:partitions=p8x8,b8x8,i4x4:weight_b:threads=1:nopsnr:nossim:frameref=3:mixed_refs:level_idc=41:direct_pred=auto:trellis=1"
        cmd = cmd + " -ovc x264 -x264encopts bitrate="+str(self.args.video_bitrate)
        cmd = cmd + ":me=hex:nodct_decimate:nointerlaced:no8x8dct:nofast_pskip:trellis=1:partitions=p8x8,b8x8,i4x4"
        cmd = cmd + ":mixed_refs:keyint=300:keyint_min=30:psy_rd=0.8,0.2:frameref=3"
        cmd = cmd + ":bframes=3:b_adapt=2:b_pyramid=none:weight_b:weightp=1:direct_pred=spatial:subq=6"
        cmd = cmd + ":nombtree:chroma_me:cabac:aud:aq_mode=2:deblock:vbv_maxrate=20000:vbv_bufsize=20000:level_idc=41:threads=auto:ssim:psnr"
        cmd = cmd + ":pass="+str(epass)
        cmd = cmd + " -o '" + dst_file + "'"

        logger.debug("cmd: %s" % (cmd))

        return cmd

    def turbo_pass(self, dst_file):
        """
        Do a fast turbo pass encode of the file
        """
        # my $pass1_cmd = "$mencoder_bin \"$source\" -ovc $ovc -oac copy $crop_opts $x264_encode_opts:bitrate=$bitrate:pass=1:turbo=1 -o $avi_file";
        turbo_cmd = self.build_cmd(dst_file, False, 1)
        return self.run(turbo_cmd, dst_file)

    def encoding_pass(self, dst_file, epass=1):
        """
        Normal multi-stage encoding pass
        """
        encode_cmd = self.build_cmd(dst_file, True, epass)
        return self.run(encode_cmd, dst_file)
