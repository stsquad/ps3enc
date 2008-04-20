#!/usr/bin/python

# TODO (in no particular order):
#
# - Don't spam to screen.
# - Support neroAacEnc.
# - Edit h264 profile.

import sys, getopt, re, subprocess, time

file_is_mkv_re = re.compile('(\.mkv)$')

mkvinfo_start_re = re.compile('\+ EBML head')
mkvinfo_segment_tracks_re = re.compile('\+ Segment tracks')
mkvinfo_a_track_re = re.compile('\+ A track')
mkvinfo_track_number_re = re.compile('\+ Track number: ([0-9]+)')
mkvinfo_track_type_re = re.compile('\+ Track type: (.*)')
mkvinfo_codec_id_re = re.compile('\+ Codec ID: (.*)')
mkvinfo_video_fps_re = re.compile('\+ Default duration: .*ms \((.*) fps for a video track\)')

# Values for the track type field in the mkvinfo output.
TRACK_TYPE_VIDEO = "video"
TRACK_TYPE_AUDIO = "audio"

# Mapping from the codec ID in the mkvinfo output to the file exptension.
VIDEO_CODECS = {'V_MPEG4/ISO/AVC': 'h264'}
AUDIO_CODECS = {'A_AAC': 'aac', 'A_AC3': 'ac3', 'A_DTS': 'dts', 'A_FLAC': 'flac'}

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
        # Add this later - for now assume all is well and we have track 1 25 fps video, track 2 ac3 audio.
        #mkvinfo_output = subprocess.Popen(["mkvinfo", self.filename], stdout=PIPE).communicate()[0]
        in_mkvinfo_output = False
        in_segment_tracks = False
        tracks = []
        
        subprocess.call(["mkvinfo", self.filename], stderr=log_file, stdout=log_file)
        temp_ro_log_file = open(log_file_name)

        # Parse the file.
        for line in temp_ro_log_file:
            if in_mkvinfo_output:
                if in_segment_tracks and (self.line_depth(line) > segment_depth):
                    while mkvinfo_a_track_re.search(line):
                        line, track = self.parse_track(temp_ro_log_file, self.line_depth(line))
                        tracks.append(track)
                elif (in_segment_tracks and self.line_depth(line) <= segment_depth):
                    break
                elif mkvinfo_segment_tracks_re.search(line):
                    in_segment_tracks = True
                    segment_depth = self.line_depth(line)
                    print "Segment depth %d" % segment_depth
            elif mkvinfo_start_re.search(line):
                in_mkvinfo_output = True

        # For now we're only allowing one video and one audio track.
        # If this isn't the case then error out. = mkvinfo_track_number_re.search(line)
        # Subtitle tracks are ignored - just output a warning.
        for track in tracks:
            if track['type'] == 'video':
                if VIDEO_CODECS[track['codec']] != 'h264':
                    print "Error: only h264 video is supported (codec was %s)" % track['codec']
                    sys.exit(2)
                if self.video_track_num != "":
                    print "Error: multiple video tracks not currently supported."
                    sys.exit(2)
                self.video_track_num = track['num']
                self.video_fps = track['fps']
            elif track['type'] == 'audio':
                if self.audio_track_num != "":
                    print "Error: multiple audio tracks not currently supported."
                    sys.exit(2)
                self.audio_track_num = track['num']
                self.audio_type = AUDIO_CODECS[track['codec']]
            else:
                print "Warning: ignoring track type " + track['type'] + "."
        print "Video track num: " + self.video_track_num
        print "Video track fps: " + self.video_fps
        print "Audio track num: " + self.audio_track_num
        print "Audio type: " + self.audio_type

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
        self.video_track_name = re.sub('(\..*)$', '.h264', self.filename)
        self.audio_track_name = re.sub('(\..*)$', "." + self.audio_type, self.filename)
        mkvextract_retcode = subprocess.call(["mkvextract", \
                                              "tracks", \
                                              self.filename, \
                                              self.video_track_num + ":" + self.video_track_name, \
                                              self.audio_track_num + ":" + self.audio_track_name])
        return self.video_track_name, self.video_fps, self.audio_track_name

class VideoTrack:

    def __init__(self, filename, fps):
        self.filename = filename
        self.fps = fps
        self.output_filename = ""

    # Need to add code to set h264 profile level to 4.1 or less.
    def convert(self):
        self.output_filename = self.filename
        return(self.output_filename)

class AudioTrack:

    def __init__(self, filename, encoder):
        self.filename = filename
        self.encoder = encoder
        self.output_filename = ""

    # Convert the audio file to the target format.
    # Currently converts to AAC using NeroAACEnc.
    def convert(self):

        if self.encoder == "neroAacEnc":
            fifo_name = re.sub('(\..*)$', '.wav', self.filename)
            self.output_filename = re.sub('(\..*)$', '.m4a', self.filename)
            mkfifo(fifo_name) # Instead of subprocess.call(["mkfifo", fifo_name])
            subprocess.call(["neroAacEnc -lc -ignorelength -q 0.20 -if audiodump.wav -of audio.m4a & mplayer audio.ac3 -vc null -vo null -channels 2 -ao pcm:fast", ""])
        elif self.encoder == "ffmpeg":
            self.output_filename = re.sub('(\..*)$', '.aac', self.filename)
            subprocess.call(["ffmpeg", \
                             "-i", self.filename, \
                             "-acodec", "libfaac", \
                             "-ac", "2", \
                             "-ab", "160000", \
                             self.output_filename])

        return self.output_filename

class OutputFile:

    def __init__(self, filename):
        self.filename = filename

    def create(self, video_track, audio_track):
        subprocess.call(["MP4Box", \
                         "-new", self.filename, \
                         "-add", video_track.output_filename, \
                         "-fps", video_track.fps, \
                         "-add", audio_track.output_filename])

def main(argv):

    input_file = ""
    target_device = "Xbox360"
    explicit_audio_encoder = False
    audio_encoder = "ffmpeg"
    delete_temp_files = True
    verbose = False
    global log_file_name
    global log_file

    try:
        opts, args = getopt.getopt(argv, "a:d:hi:kv", ["audio-encoder=", "help", "input-file=", "keep-temp-files", "target-device=", "verbose"])
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
        elif opt in ("-v", "--verbose"):
            verbose = True

    if input_file == "":
        print "Error: no input file specified"
        usage()
        sys.exit(2)
    if not (file_is_mkv_re.search(input_file)):
        print "Error - mkv input expected"
        usage()
        sys.exit(2)
 
    # Check for the existence of the programs we'll need.
    if (subprocess.call(["which", "mkvinfo"]) != 0):
        print "Error: mkvinfo not present."
        sys.exit(2)
    if (subprocess.call(["which", "mkvextract"]) != 0):
        print "Error: mkvextract not present."
        sys.exit(2)
    if (subprocess.call(["which", "neroAacEnc"]) != 0):
        print "Error: neroacCEnc not present."
        sys.exit(2)
    if (subprocess.call(["which", "MP4Box"]) != 0):
        print "Error: MP4Box not present."
        sys.exit(2)

    # Create a log file.
    log_file_name = "MKVConv_log_" + time.strftime("%Y-%m-%d_%H-%M-%S", time.gmtime()) + ".log"
    log_file = open(log_file_name, "w")

    # Get file info from the input mkv file.
    mkv_file = InputFile(input_file)
    mkv_file.get_info()

    # Extract the video and audio tracks.
    video_track_name, video_track_fps, audio_track_name = mkv_file.extract_tracks()

    # Convert the video and audio tracks.
    video_track = VideoTrack(video_track_name, video_track_fps)
    converted_video_filename = video_track.convert()
    audio_track = AudioTrack(audio_track_name, audio_encoder)
    converted_audio_filename = audio_track.convert()

    # Mux the video and audio tracks.
    output_filename = re.sub('(\..*)$', '.mp4', input_file)
    output_file = OutputFile(output_filename)
    output_file.create(video_track, audio_track)
    
    # All done.
    print "Conversion complete."

def usage():
    print "Usage: mkv2mp4.py [options] [-i input_file]\n" + \
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
          "  -v, --verbose      Verbose output to console.\n"

if __name__ == '__main__':
     main(sys.argv[1:])

