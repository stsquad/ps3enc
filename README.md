Alex's Random Media Handling Scripts
====================================

The following scripts are used for ripping and encoding media files
into a format suitable for playing on a PS3/PS4 (h.264 encoded MP4's).

All the heavy encoding work is done with ffmpeg or mencoder.

Why?
====

Every other solution I've tried sucks?

There are loads of ripping front-ends out there however they don't
happen to suit me. These scripts concentrate on being command line
based, tuned for the Playstation (may main media hub) and useful for
ripping box sets by using heuristics to identify the episodes on a
disk.

It's also an exercise in coding more python for me. Having said that
it is all open source so I'll happily accept patches and you are
perfectly free to fork it for your own needs.

Approach and prerequisites
==========================

The script is optimised for my setup. As the files are quite big and a
lot of the stuff in multi-pass is thrown away most of the heavy file
I/O is in /tmp which on my 16GB machine is huge tmpfs partition. This
means the encoding is rarely I/O bound which makes running multiple
encodes less of a load on my machine (which is a 2 core + 2 thread i5
system).

These scripts require the following:

* ffmpeg
* mencoder (fallback, used for subtitle rips)
* lsdvd
* MP4Box

Usage
=====

There are currently three scripts

rip.py
------

The rip script is used to rip a DVD into 1-n separate VOB files. It
attempts to calculate this by looking for the modal episode length
after having rounded to the nearest 6 minutes. If you explicitly
set the max times from the command line it will rip anything else
within 80% of the size.

The aim of this is to make ripping fairly seamless when presented with
a TV box set.

Episodes will be numbered from 1 unless the -b flag specifies a
new base.

The script requires the "lsdvd" utility to be installed to get the
chapter information from the DVD.

Unless -l/-r is specified the script will automatically kick of
ps3enc.py to start encoding the VOB file. Otherwise the script will
create a log of files ripped that can be passed to an encoding process
as ripping 4 episodes in one go on a single or duel core machine isn't
actually that efficient.

See --help for all the command line options.

ps3enc.py
---------

This script encodes video files into PS3 compliant MP4 files. By
default it does a 3 pass encode with a video bitrate of 2MBs.

It has a couple of presets:

  -c/--cartoon

  Single pass, lower bitrate, enables a filter that seems to improve
  encoding

  --film

  Higher video bitrate also increases the audio bitrate as films often
  have quite a dense soundtrack which benefits from it.

mkv2mp4.py
----------

This was originally written by L.J.J Lee, also under GPLv3
(https://github.com/vgasu/mkv2mp4). I've made a few tweaks to it since.

mkv2mp4 is a commandline utility, written in Python, which allows conversion
of video files in the Matroska container (*.mkv file extension) containing
H.264 video to be converted into a format which the PS3/PS4 and Xbox 360 can play.
  
It differs from other similar tools in that no video transcoding is
performed; the video is passed through untouched and the just the audio is
transcoded if necessary.  This means that the conversion is much faster
(the whole process being quicker than realtime on reasonably modern
machines), and more importantly that there is no degradation in video quality
(which makes it very suitable for HD video).
  
Due to the fact no video transcoding is performed, this tool is somewhat
restrictive in the input formats it supports.  Supported formats are the
the following - the intention being that this should work on (at least) files
conforming to the x264 HD scene rules - FLAC multichannel audio is the only
exception currently.
  - Container: Matroska.
  - Video codec: H.264
  - Audio codec: the app supports all audio codecs, however:
    - ffmpeg's multichannel support currently isn't great, and therefore only
      a subset of codecs with more than two channels will work.  5.1 AC3 and
      5.1 DTS are known to work, 5.1 FLAC is known not to, others are untested.
    - All stereo codecs which ffmpeg can decode should work.

Technical details:

  This application makes the following alterations to the file:
  - Extract tracks from mkv input (uses mkvinfo & mkvextract)
  - Edit H.264 video stream to have level 4.1 or less (this is just a change
    to the file header - no transcoding).  This is because the Xbox 360 doesn't
    play files with a higher level.
  - Transcode audio to stereo AAC (unfortunately the Xbox 360 doesn't support
    any 5.1 audio codecs in mp4) (using ffmpeg for decoding and encoding (with
    native aac support), or ffmpeg for decoding and neroAacEnc for encoding.
  - Drop any tracks other than the first video and audio tracks (the Xbox 360
    doesn't support multiple video or audio tracks, and doesn't support
    subtitles in mp4).
  - Remux into an mp4 container.  Files are split such that they are smaller
    than 4GB (again... a restriction for the Xbox 360).
