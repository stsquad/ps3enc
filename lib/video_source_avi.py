#!/usr/bin/python
#
# Query an AVI file for track information
#
# Further more in-depth analysis can be done
#
# (C)opyright 2011 Alex Bennee <alex@bennee.com>
#
# Licenced under the GPL version 3 Which means no warrenty! Break it
# you get to keep both pieces, fix it then please send me the glue :-)
#

import os
import sys
import getopt
import subprocess
import re
import sys
import shlex
import shutil
import tempfile

mplayer_bin="/usr/bin/mplayer"

# This is for unit testing...
ident_test_output="""
MPlayer SVN-r33094-4.4.5 (C) 2000-2011 MPlayer Team
Playing /home/alex/tmp/DEADWOOD_S3_D1-1/DEADWOOD_S3_D1-1.vob.
ID_VIDEO_ID=0
ID_AUDIO_ID=128
ID_AUDIO_ID=129
ID_AUDIO_ID=130
MPEG-PS file format detected.
VIDEO:  MPEG2  720x576  (aspect 3)  25.000 fps  9800.0 kbps (1225.0 kbyte/s)
Load subtitles in /home/alex/tmp/DEADWOOD_S3_D1-1/
ID_FILENAME=/home/alex/tmp/DEADWOOD_S3_D1-1/DEADWOOD_S3_D1-1.vob
ID_DEMUXER=mpegps
ID_VIDEO_FORMAT=0x10000002
ID_VIDEO_BITRATE=9800000
ID_VIDEO_WIDTH=720
ID_VIDEO_HEIGHT=576
ID_VIDEO_FPS=25.000
ID_VIDEO_ASPECT=0.0000
ID_AUDIO_FORMAT=8192
ID_AUDIO_BITRATE=0
ID_AUDIO_RATE=0
ID_AUDIO_NCH=0
ID_START_TIME=0.29
ID_LENGTH=2255.79
ID_SEEKABLE=1
ID_CHAPTERS=0
==========================================================================
Opening video decoder: [ffmpeg] FFmpeg's libavcodec codec family
Selected video codec: [ffmpeg2] vfm: ffmpeg (FFmpeg MPEG-2)
==========================================================================
ID_VIDEO_CODEC=ffmpeg2
==========================================================================
Opening audio decoder: [ffmpeg] FFmpeg/libavcodec audio decoders
AUDIO: 48000 Hz, 2 ch, s16le, 192.0 kbit/12.50% (ratio: 24000->192000)
ID_AUDIO_BITRATE=192000
ID_AUDIO_RATE=48000
ID_AUDIO_NCH=2
Selected audio codec: [ffac3] afm: ffmpeg (FFmpeg AC-3)
==========================================================================
AO: [pulse] 48000Hz 2ch s16le (2 bytes per sample)
ID_AUDIO_CODEC=ffac3
"""

crop_test_output="""
A:   2.1 V:   2.1 A-V:  0.000 ct:  0.032  48/ 48  4%  5%  0.3% 0 0 
[CROP] Crop area: X: 0..719  Y: 170..404  (-vf crop=720:224:0:176).
A:   2.2 V:   2.2 A-V:  0.000 ct:  0.032  49/ 49  4%  5%  0.3% 0 0 
[CROP] Crop area: X: 0..719  Y: 120..453  (-vf crop=720:320:0:128).
A:   2.2 V:   2.2 A-V:  0.000 ct:  0.032  50/ 50  4%  5%  0.3% 0 0 
[CROP] Crop area: X: 0..719  Y: 77..499  (-vf crop=720:416:0:82).
A:   2.2 V:   2.2 A-V:  0.002 ct:  0.032  51/ 51  4%  5%  0.3% 0 0 
[CROP] Crop area: X: 0..719  Y: 0..573  (-vf crop=720:560:0:8).
A:   2.3 V:   2.3 A-V:  0.000 ct:  0.032  52/ 52  4%  5%  0.3% 0 0 
[CROP] Crop area: X: 0..719  Y: 0..573  (-vf crop=720:560:0:8).
A:   2.3 V:   2.3 A-V:  0.000 ct:  0.032  53/ 53  4%  5%  0.3% 0 0 
[CROP] Crop area: X: 0..719  Y: 0..573  (-vf crop=720:560:0:8).
A:   2.4 V:   2.4 A-V:  0.000 ct:  0.032  54/ 54  4%  5%  0.3% 0 0
"""

from video_source_mplayer import video_source_mplayer


class video_source_avi(video_source_mplayer):
    """
    A video source is a wrapper around an AVI file
    """

    # mplayer parameters
    fps=None

    audio_tracks = []

    # Crop calculation
    crop_spec=None
    potential_crops = {}

    def __str__(self):
        """
        Our string representation
        """
        results = super(self.__class__,self).__str__().split(", ")
        if len(self.audio_tracks)>0:
            results.append("Audio tracks: %d" % (len(self.audio_tracks)))

        return ", ".join(results)

    def analyse_video(self):
        if os.path.exists(self.path):
            self.size = os.path.getsize(self.path)
        super(self.__class__,self).analyse_video()

    def identify_video(self):
        ident_cmd = mplayer_bin+" -identify -frames 0 '"+self.path+"'"
        if self.verbose: print "doing identify step: %s" % (ident_cmd)
        try:
            p = subprocess.Popen(ident_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
            (out, err) = p.communicate()
            self.extract_fps(out)
            self.extract_audio(out)
            self.extract_video_codec(out)
            self.extract_audio_codec(out)
        except OSError:
                print "Failed to spawn: "+ident_cmd

    def extract_crop(self, out):
        """
        >>> x = video_source_avi('/path/to/file')
        >>> x.extract_crop(crop_test_output)
        >>> print x.crop_spec
        """
        m = re.search("\-vf crop=[-0123456789:]*", out)
        if m:
            try:
                self.potential_crops[m.group(0)]+=1
            except KeyError:
                self.potential_crops[m.group(0)]=1
                if self.verbose: print "Found Crop:"+m.group(0)
        
    def extract_fps(self, out):
        """
        >>> x = video_source_avi('/path/to/file')
        >>> x.extract_fps(ident_test_output)
        >>> print x.fps
        25.000
        """
        m = re.search("ID_VIDEO_FPS=(\d{2}\.\d*)", out)
        if m:
            self.fps = m.groups()[0]
        else:
            print "extract_fps: Failed to find FPS in (%s)" % (out)

    def extract_video_codec(self, out):
        """
        >>> x = video_source_avi('/path/to/file')
        >>> x.extract_video_codec(ident_test_output)
        >>> print x.video_codec
        ffmpeg2
        """
        m = re.search("ID_VIDEO_CODEC=(\w+)", out)
        if m:
            self.video_codec = m.groups()[0]
        else:
            print "extract_video_codec: Failed to find VIDEO in (%s)" % (out)

    def extract_audio(self, out):
        """
        >>> x = video_source_avi('/path/to/file')
        >>> x.extract_audio(ident_test_output)
        >>> print x.audio_tracks
        ['128', '129', '130']
        """
        self.audio_tracks = re.findall("ID_AUDIO_ID=(\d+)", out)
        if len(self.audio_tracks)==0:
            print "extract_audio: Failed to find audio tracks in (%s)" % (out)
            

    def extract_audio_codec(self, out):
        """
        >>> x = video_source_avi('/path/to/file')
        >>> x.extract_audio_codec(ident_test_output)
        >>> print x.audio_codec
        ffac3
        """
        m = re.search("ID_AUDIO_CODEC=(\w+)", out)
        if m:
            self.audio_codec = m.groups()[0]
        else:
            print "extract_audio_codec: Failed to find AUDIO in (%s)" % (out)

    def sample_video(self):
        """
        Calculate the best cropping parameters to use by looking over the whole file
        """
        for i in range(0, self.size-self.size/60, self.size/60):
            crop_cmd = mplayer_bin+" -v -nosound -vo null -sb "+str(i)+" -frames 10 -vf cropdetect '"+self.path+"'"
            if self.verbose: print "doing sample step: %s" % (crop_cmd)
            try:
                p = subprocess.Popen(crop_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
                (out, err) = p.communicate()
                self.extract_crop(out)

            except OSError:
                print "Failed to spawn: "+crop_cmd

        # most common crop?
        crop_count = 0
        for crop  in self.potential_crops:
            if self.potential_crops[crop] > crop_count:
                crop_count = self.potential_crops[crop]
                self.crop_spec = crop

        if self.verbose: print "sample_video: crop is "+self.crop_spec



# Testing code
if __name__ == "__main__":
    from video_source import video_options
    (parser, options, args) = video_options()

    if len(args)>=1:
        for a in args:
            if a.startswith("dvd://"):
                v = video_source_avi(a, options.verbose)
            else:
                fp = os.path.realpath(a)
                v = video_source_avi(fp, options.verbose)
            if options.identify:
                v.identify_video()
            if options.analyse:
                v.analyse_video()
            print v
    else:
        import doctest
        doctest.testmod()
        
        
