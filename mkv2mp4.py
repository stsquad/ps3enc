#!/usr/bin/python

#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

# TODO (in no particular order):
#
# - Fixup selection of audio encoder, and dependency checking.
# - FLAC audio streams:
#   - Garbled audio with mplayer+neroAacEnc (mplayer -channels option?).
#   - ffmpeg rejects FLACs.
# - Add README file.

import os, getopt, re, subprocess, sys, time

file_is_mkv_re = re.compile('(\.mkv)$')

mkvinfo_start_re = re.compile('\+ EBML head')
mkvinfo_segment_tracks_re = re.compile('\+ Segment tracks')
mkvinfo_a_track_re = re.compile('\+ A track')
mkvinfo_track_number_re = re.compile('\+ Track number: ([0-9]+)')
mkvinfo_track_type_re = re.compile('\+ Track type: (.*)')
mkvinfo_codec_id_re = re.compile('\+ Codec ID: (.*)')
mkvinfo_video_fps_re = \
         re.compile('\+ Default duration: .*ms \((.*) fps for a video track\)')

# Values for the track type field in the mkvinfo output.
TRACK_TYPE_VIDEO = "video"
TRACK_TYPE_AUDIO = "audio"

# Mapping from the codec ID in the mkvinfo output to the file exptension.
VIDEO_CODECS = {'V_MPEG4/ISO/AVC': 'h264'}
AUDIO_CODECS = {'A_AAC': 'aac', \
                'A_AC3': 'ac3', \
                'A_DTS': 'dts', \
                'A_FLAC': 'flac'}

# Offset of the level byte in the 
H264_LEVEL_OFFSET = 7
H264_MAX_OUTPUT_LEVEL = 41

class InputFile:

    def __init__(self, filename):
        self.filename = filename
        self.video_track_num = ""
        self.video_fps = ""
        self.audio_track_num = ""
        self.audio_type = ""

    # Use mkvinfo to get information about the tracks in thei file.
    # Currently, this gets the video track, checks that it's h264, stores
    # the framerate.
    def get_info(self):
        in_mkvinfo_output = False
        in_segment_tracks = False
        tracks = []
        
        log("Calling mkvinfo to get file info:")
        subprocess.call(["mkvinfo", \
                        self.filename], \
                        stderr=log_file, \
                        stdout=log_file)
        temp_ro_log_file = open(log_file_name)

        # Parse the file.
        for line in temp_ro_log_file:
            if in_mkvinfo_output:
                if (in_segment_tracks and \
                    (self.line_depth(line) > segment_depth)):
                    while mkvinfo_a_track_re.search(line):
                        line, track = self.parse_track(temp_ro_log_file, \
                                                       self.line_depth(line))
                        tracks.append(track)
                elif (in_segment_tracks and \
                      (self.line_depth(line) <= segment_depth)):
                    break
                elif mkvinfo_segment_tracks_re.search(line):
                    in_segment_tracks = True
                    segment_depth = self.line_depth(line)
            elif mkvinfo_start_re.search(line):
                in_mkvinfo_output = True
        temp_ro_log_file.close()

        # For now we're only allowing one video and one audio track.
        # If this isn't the case then error out.
        # Subtitle tracks are ignored - just output a warning.
        for track in tracks:
            if track['type'] == 'video':
                if VIDEO_CODECS[track['codec']] != 'h264':
                    print "Error: only h264 video is supported " + \
                          "(codec was %s)" % track['codec']
                    sys.exit(2)
                if self.video_track_num != "":
                    print "Error: multiple video tracks not " + \
                          "currently supported."
                    sys.exit(2)
                self.video_track_num = track['num']
                self.video_fps = track['fps']
            elif track['type'] == 'audio':
                if self.audio_track_num != "":
                    print "Error: multiple audio tracks not " + \
                          "currently supported."
                    sys.exit(2)
                self.audio_track_num = track['num']
                self.audio_type = AUDIO_CODECS[track['codec']]
            else:
                print "Warning: ignoring '%s' track." % track['type']
        print "\nInput file properties:"
        print "  Video: h264, %s fps" % self.video_fps
        print "  Audio: %s\n" % self.audio_type

    # Parses a track block from the output of mkvinfo.
    # Extracts track number, track type, codec id, and fps.
    def parse_track(self, ro_log_file, track_nest_depth):
        track = {'type': 'other'}

        for line in ro_log_file:
            if self.line_depth(line) <= track_nest_depth:
                break

            track_number_match = mkvinfo_track_number_re.search(line)
            if track_number_match != None:
                track['num'] = track_number_match.group(1)

            track_type_match = mkvinfo_track_type_re.search(line)
            if track_type_match != None:
                track['type'] = track_type_match.group(1)

            codec_id_match = mkvinfo_codec_id_re.search(line)
            if codec_id_match != None:
                track['codec'] = codec_id_match.group(1)

            video_fps_match = mkvinfo_video_fps_re.search(line)
            if video_fps_match != None:
                track['fps'] = video_fps_match.group(1)
        return line, track

    # Calculate how deeply a line is nested (used for parsing mkvinfo).
    def line_depth(self, line):
        line_start_re = re.compile('\+')
        return line_start_re.search(line).start(0)

    # Use mkvextract to extract the audio and video tracks.
    def extract_tracks(self):
        self.video_track_name = re.sub('(\.[^\.]*)$', '.h264', self.filename)
        self.audio_track_name = re.sub('(\.[^\.]*)$', \
                                       "." + self.audio_type, \
                                       self.filename)
        print "%s: Extracting tracks from mkv file..." % timestamp()
        log("\nCalling mkvextract to demux mkv file:")
        mkvextract_retcode = subprocess.call( \
                         ["mkvextract", \
                          "tracks", \
                          self.filename, \
                          self.video_track_num + ":" + self.video_track_name, \
                          self.audio_track_num + ":" + self.audio_track_name])
        print "%s: Extraction complete.\n" % timestamp()
        return self.video_track_name, self.video_fps, self.audio_track_name

class VideoTrack:

    def __init__(self, filename, fps):
        self.filename = filename
        self.fps = fps
        self.output_filename = ""

    # From the sample files I've looked at, it looks like this just involves
    # changing the 8th byte of the raw h264 file to the profile number with
    # the decimal point removed (eg. 4.1 is 41 = 0x29).
    #
    # Should really check this though.
    def convert(self):
        print "%s: Updating video track..." % timestamp()
        self.output_filename = self.filename
        file = open(self.filename, 'r+b')
        file.seek(H264_LEVEL_OFFSET)
        current_profile = file.read(1)
        print "Current H264 level is %d" % ord(current_profile)
        if current_profile > chr(H264_MAX_OUTPUT_LEVEL):
            print "Changing H264 level to %d" % H264_MAX_OUTPUT_LEVEL
            file.seek(H264_LEVEL_OFFSET)
            file.write(chr(H264_MAX_OUTPUT_LEVEL))
        else:
            print "No change needed to H264 profile."
        file.close()
        print "%s: Finished updating video track.\n" % timestamp()
        return(self.output_filename)

    # Delete intermediate files.
    def cleanup(self):
        if delete_temp_files:
            os.remove(self.filename)

class AudioTrack:

    def __init__(self, filename, encoder):
        self.filename = filename
        self.encoder = encoder
        self.output_filename = ""

    # Convert the audio file to the target format.
    # Currently converts to AAC using ffmpeg.
    def convert(self):
        if self.encoder == "neroAacEnc":
            print "%s: Transcoding audio using neroAacEnc..." % timestamp()
            self.output_filename = re.sub('(\.[^\.]*)$', '.m4a', self.filename)
            fifo_name = re.sub('(\.[^\.]*)$', '.wav', self.filename)
            try:
                os.mkfifo(fifo_name)
            except:
                pass
            nero_popen = subprocess.Popen(["neroAacEnc", "-lc", "-ignorelength", \
                                "-br", "160", \
                                "-if", fifo_name, "-of", self.output_filename])
            mplayer_popen = subprocess.Popen(["mplayer", self.filename, \
                                   "-vc", "null", "-vo", "null", \
                                   "-ao", "pcm:fast:file=" + fifo_name, \
                                   "-channels", "2", "-quiet"])
            nero_popen.wait()
            os.remove(fifo_name)
        elif self.encoder == "ffmpeg":
            print "%s: Transcoding audio using ffmpeg..." % timestamp()
            self.output_filename = re.sub('(\.[^\.]*)$', '.aac', self.filename)
            log("Calling ffmpeg to transcode audio")
            subprocess.call(["ffmpeg", \
                             "-i", self.filename, \
                             "-acodec", "libfaac", \
                             "-ac", "2", \
                             "-ab", "160000", \
                             self.output_filename])
        print "%s: Audio transcoding complete.\n" % timestamp()
        return self.output_filename

    # Delete intermediate files.
    def cleanup(self):
        if delete_temp_files:
            os.remove(self.filename)
            os.remove(self.output_filename)

class OutputFile:

    def __init__(self, filename):
        self.filename = filename

    def create(self, video_track, audio_track):
        print "%s: Muxing video and audio into MP4 file..." % timestamp()
        subprocess.call(["MP4Box", \
                         "-new", self.filename, \
                         "-add", video_track.output_filename, \
                         "-fps", video_track.fps, \
                         "-add", audio_track.output_filename])
        print "%s: Muxing complete." % timestamp()

def main(argv):

    global delete_temp_files
    global log_file_name
    global log_file

    input_file = ""
    target_device = "Xbox360"
    explicit_audio_encoder = False
    audio_encoder = "ffmpeg"
    delete_temp_files = True
    output_log_file = False

    try:
        opts, args = getopt.getopt(argv, \
                                   "a:d:hi:kl", \
                                   ["audio-encoder=", \
                                    "target-device=", \
                                    "help", \
                                    "input-file=", \
                                    "keep-temp-files", \
                                    "output-logfile"])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-a", "--audio-encoder"):
            if arg in ("neroAacEnc", "ffmpeg"):
                explicit_audio_encoder = True
                audio_encoder = arg
            else:
                print "Error: invalid audio encoder specified."
                usage()
                sys.exit(2)
        elif opt in ("-d", "--target-device"):
            target_device = arg
        elif opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt in ("-i" "--input-file"):
            input_file = arg
        elif opt in ("-k", "--keep-temp-files"):
            delete_temp_files = False
        elif opt in ("-l", "--output-logfile"):
            output_log_file = True

    if input_file == "":
        print "Error: no input file specified"
        usage()
        sys.exit(2)
    if not (file_is_mkv_re.search(input_file)):
        print "Error - mkv input expected"
        usage()
        sys.exit(2)
 
    # Create a log file.
    start_time = time.time()
    log_file_name = "mkv2mp4_log_" + \
                    time.strftime("%Y-%m-%d_%H-%M-%S", time.gmtime(start_time)) + \
                    ".log"
    log_file = open(log_file_name, "w")

    # Check for the existence of the programs we'll need.
    log("Checking for mkvinfo:")
    if (subprocess.call(["which", "mkvinfo"], stdout=log_file) != 0):
        print "Error: mkvinfo not present."
        sys.exit(2)
    log("Checking for mkvextract:")
    if (subprocess.call(["which", "mkvextract"], stdout=log_file) != 0):
        print "Error: mkvextract not present."
        sys.exit(2)
    log("Checking for neroAacEnc:")
    if (subprocess.call(["which", "neroAacEnc"], stdout=log_file) != 0):
        print "Error: neroacCEnc not present."
        sys.exit(2)
    log("Checking for MP4Box:")
    if (subprocess.call(["which", "MP4Box"], stdout=log_file) != 0):
        print "Error: MP4Box not present."
        sys.exit(2)
    log("")

    # Get file info from the input mkv file.
    mkv_file = InputFile(input_file)
    mkv_file.get_info()

    # Extract the video and audio tracks.
    video_track_name, video_track_fps, audio_track_name = \
                                                      mkv_file.extract_tracks()

    # Convert the video and audio tracks.
    video_track = VideoTrack(video_track_name, video_track_fps)
    converted_video_filename = video_track.convert()
    audio_track = AudioTrack(audio_track_name, audio_encoder)
    converted_audio_filename = audio_track.convert()

    # Mux the video and audio tracks.
    output_filename = "mkv2mp4_" + re.sub('(\.[^\.]*)$', '.mp4', input_file)
    output_file = OutputFile(output_filename)
    output_file.create(video_track, audio_track)

    # Cleanup processing.
    video_track.cleanup()
    audio_track.cleanup()
    log_file.close()
    if not output_log_file:
        os.remove(log_file_name)
    
    # All done.
    print "\n%s: Conversion complete (took %s); output in:\n%s" % \
           (timestamp(), \
            time.strftime("%M minutes and %S seconds", time.gmtime(time.time() - start_time)), \
            output_filename)

def log(line):
    log_file.write(line + "\n")
    log_file.flush()

def timestamp():
    return time.strftime("%d %b %H:%M:%S", time.gmtime())

def usage():
    print \
"Usage: mkv2mp4.py [options] -i input_file\n" + \
"\n" + \
"Options:\n" + \
"  -a <encoder>, --audio-encoder=<encoder>\n" + \
"                     Specify the audio encoder to use.  Supported encoders are:\n" + \
"                       'neroAacEnc': The NERO AAC encoder [preferred default]\n" + \
"                       'ffmpeg': ffmpeg (needs libfaac support)\n" + \
"  -d <device>, --target-device=<device>\n" + \
"                     Specify the target device.  Supported devices are:\n" + \
"                       'Xbox360': Microsoft Xbox 360 [default]\n" + \
"  -h, --help         Print this help text.\n" + \
"  -k, --keep-temp-files\n" + \
"                     Keep intermediate files (default is not to).\n" + \
"  -l, --output-logfile\n" + \
"                     Output a log file\n"

if __name__ == '__main__':
     main(sys.argv[1:])

