#!/usr/bin/python
#
# RIP DVD
#
# Biased toward ripping a series DVD into VOB files and then launching ps3enc on them
#

import os
import sys
import subprocess
import logging

from operator import itemgetter
from argparse import ArgumentParser

# Logging
logger = logging.getLogger("rip")

verbose=0
use_vlc=False
encode="list"
single_episode=False
ripdir=os.getenv("HOME")+"/tmp"
base=1
maxl=None
encode=True
# dvd=None
nonav=False

# Round to nearest n minutes
round_factor=6
# Allow mode + round_fudge_factor * 60 * round_fudge_factor
round_fudge_factor=2

#
# Command line options
#
parser=ArgumentParser(description='Rip raw video file from a DVD',
                      epilog="""The script will usually call its sister script ps3enc.py to complete the encoding process""")
parser.add_argument('-d', '--dir', dest="ripdir", default=os.getenv("HOME")+"/tmp",
                    help="base directory for output")

general_opts = parser.add_argument_group("General Options")
general_opts.add_argument("-s", "--scan-only",  default=False, action="store_true", help="Just run the scan and selection phase.")
general_opts.add_argument("-p", "--pretend",  default=False, action="store_true", help="Pretend, don't rip, just report what you would do.")
general_opts.add_argument('-v', '--verbose', action='count', default=None, help='Be verbose in output')
general_opts.add_argument('-q', '--quiet', action='store_false', dest='verbose', help="Supress output")
general_opts.add_argument('-l', '--log', default=None, help="output to a log file")

source_opts = parser.add_argument_group("Source Options")
source_opts.add_argument("--dvd", help="Manually specify the DVD device.")

track_opts = parser.add_argument_group("Track Options")
track_opts.add_argument('-1', '--single', dest="single_episode", default=False, help="rip a single episode")
track_opts.add_argument('-e', '--episodes', dest="single_episode", action="store_false", help="rip a set of episodes")
track_opts.add_argument('--limit', default=20, type=int, help="Limit to the first N episodes")
track_opts.add_argument('--max', default=None, help="Max episode time (in minutes)")
track_opts.add_argument('--min', default=None, help="Min episode time (in minutes)")
track_opts.add_argument('-t', '--tracks', dest="track_list", type=int, default=[], nargs="+", help="List of tracks to rip")

output_opts = parser.add_argument_group("Output options")
output_opts.add_argument('--title', default=None, help="Set the base title of the series")
output_opts.add_argument('--season', default=1, type=int, help="Set the base season of the series")
output_opts.add_argument('--base', default=1, type=int, help="Set the base season of the series")
output_opts.add_argument('--encode-options', default="", help="Pass string to ps3enc")
output_opts.add_argument('--direct', dest="direct_encode", default=False, action="store_true", help="Encode directly, don't rip")

def encode_track(path):
    enc_cmd = "ps3enc.py -v %s %s" % (path, args.encode_options)
    if verbose>0: print "cmd: %s" % (enc_cmd)
    os.system(enc_cmd)

def process_track(args, base, track):
    if (args.single_episode):
        name = args.title
    else:
        name = "s%02de%02d" % (args.season, base)

    logging.info("Ripping: %s as %s" % (track, name))

    dump_dir=ripdir+"/"+args.title

    if not os.path.isdir(dump_dir):
        os.makedirs(dump_dir)

    os.chdir(dump_dir)

    dump_file=dump_dir+"/"+name+".vob"
    if use_vlc:
        rip_cmd="vlc -I rc dvd:/dev/hda@"+str(track)+' --sout "#standard{access=file,mux=ps,dst='+dump_file+'}"'
    else:
        if nonav:
            nav = "dvd://"+str(track)
        else:
            nav = "dvdnav://"+str(track)

        rip_cmd="mplayer "+nav+" -dumpstream -dumpfile "+dump_file
        if args.dvd: rip_cmd += " -dvd-device "+args.dvd

    rip_cmd += " > /dev/null 2>&1"

    logger.debug("cmd: %s" % (rip_cmd))
    if not args.pretend:
        os.system(rip_cmd)

    if encode:
        # Now we have ripped the file spawn ps3enc.py to deal with it
        enc_cmd="nice ps3enc.py "+args.encode_options+dump_file+" > /dev/null 2>&1 &"
        logger.debug("cmd: %s" % (enc_cmd))
        if not args.pretend:
            os.system(enc_cmd)

def round_time(time, mins):
    """
    Round time to nearest n minutes
    """
    rem = time % (60*mins)
    res = time - rem
    return res

def get_mode_time(times):
    """
    Count the times and calculate the mode
    """
    time_dict = dict()
    for n in times:
        if n in time_dict:
            time_dict[n] = time_dict[n]+1
        else:
            time_dict[n] = 1

    # sort dictionary
    time_sorted = sorted(time_dict.iteritems(), key=itemgetter(1))
    mode = time_sorted[-1][0]
    return mode


def scan_dvd(args, dvdinfo, maxl):
    rip_tracks=[]
    tracks=dvdinfo['track']

    # If only one episode rip longest...
    if args.single_episode:
        # 99% of the time the longest track is what you want
        lt=dvdinfo['longest_track']
        for t in tracks:
            if t['ix'] == lt:
                logger.debug("longest track %s (%d seconds/%d mins)" % (t['ix'], t['length'], t['length']/60))
        rip_tracks.append(lt)
    else:
        # Define our max criteria
        if maxl==None:
            # As episode DVDs often have a "fake" track which strings them
            # all together lets try and be a bit more clever.
            rt = []
            for t in tracks:
                tt = round_time(t['length'], round_factor)
                if tt>0 and tt<(60*120):
                    logger.debug("track %s (%d/%d->%d/%d)" % (t['ix'], t['length'], t['length']/60, tt, tt/60))
                    rt.append(tt)
            mode = get_mode_time(rt)
            maxl = mode + (round_fudge_factor*60*round_factor)
            minl = mode
            logger.debug("Mode of episode tracks was: "+str(mode)+" with max time "+str(maxl))
        else:
            logger.debug("Have specified longest track to be "+str(maxl))
            minl=maxl*float(0.80)


        logger.info("Looking for episodes between %f and %f seconds" % (maxl, minl))

        for t in tracks:
            length=t['length']
            if length>=minl and length<=maxl:
                logger.info("Selecting candidate track: %s" % t)
                rip_tracks.append(t['ix'])

    if (args.limit):
        rip_tracks = rip_tracks[:args.limit]

    return rip_tracks

def create_rip_list(args):
    "Create a list of tracks to rip"

    if (len(args.track_list)>0):
        logger.info("Passed in a track list (%s)" % args.track_list)
        return args.track_list

    lsdvd="lsdvd -Oy "
    if args.dvd: lsdvd += args.dvd
    p = subprocess.Popen(lsdvd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
    (info, err) = p.communicate()

    dvdinfo=eval(info[8:])
    rip_tracks = scan_dvd(args, dvdinfo, maxl)

    if args.title is None:
        args.title=dvdinfo['title']

    return rip_tracks

def setup_logging(args):
    # setup logging
    if args.verbose:
        if args.verbose == 1: logger.setLevel(logging.INFO)
        if args.verbose >= 2: logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARNING)

    if args.log:
        handler = logging.FileHandler(args.log)
    else:
        handler = logging.StreamHandler()

    lfmt = logging.Formatter('%(asctime)s:%(levelname)s - %(name)s - %(message)s')
    handler.setFormatter(lfmt)
    logger.addHandler(handler)

    logger.info("running with level %s" % (logger.getEffectiveLevel()))

# Start of code
if __name__ == "__main__":
    args = parser.parse_args()
    setup_logging(args)

    create_log=None
    rip_tracks=create_rip_list(args)

    print "Ripping %d episodes (%s)" % (len(rip_tracks), rip_tracks)
    if args.scan_only:
        exit(-len(rip_tracks))

    base = args.base
    for t in rip_tracks:
        if args.direct_encode:
            encode_track("dvd://%d" % int(t))
        else:
            process_track(args, base, t)
        base=base+1

    # Eject the DVD
    if not args.pretend or args.direct_encode:
        os.system("eject")
