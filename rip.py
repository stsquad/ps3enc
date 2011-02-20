#!/usr/bin/python
#
# RIP DVD
#
# Biased toward ripping a series DVD into VOB files and then launching ps3enc on them
#

import os
import sys
import getopt
from operator import itemgetter

verbose=0
use_vlc=False
log=None
encode="list"
single_episode=False
ripdir=os.getenv("HOME")+"/tmp"
base=1
maxl=None
passes=None
encode=True
dvd=None
nonav=False

def process_track(ep, title, track):
    print "Ripping: %s" % (track)

    name=title+"-"+str(ep)

    dump_dir=ripdir+"/"+name
    if not os.path.isdir(dump_dir):
        os.mkdir(dump_dir)

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
        if dvd: rip_cmd += " -dvd-device "+dvd

    rip_cmd += " > /dev/null 2>&1"

    if verbose>0: print "cmd: %s" % (rip_cmd)
    os.system(rip_cmd)

    if log:
        log.write(dump_file+"\n");
        log.flush()
        
    if encode:
        # Now we have ripped the file spawn ps3enc.py to deal with it
        enc_options=""
        if passes: enc_options += "-p %s " % (passes)
        enc_cmd="nice ps3enc.py "+enc_options+dump_file+" > /dev/null 2>&1 &"
        if verbose>0:
            print "cmd: %s" % (enc_cmd)
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


def scan_dvd(dvdinfo, maxl):
    rip_tracks=[]  

    # If only one episode rip longest...
    if single_episode:
        # 99% of the time the longest track is what you want
        lt=dvdinfo['longest_track']
        rip_tracks.append(lt)
    else:
        # Define our max criteria
        if maxl==None:
            # As episode DVDs often have a "fake" track which strings them
            # all together lets try and be a bit more clever.
            rt = []
            for t in tracks:
                rt.append(round_time(t['length'], 5))
            mode = get_mode_time(rt)
            maxl  = mode + (60*5)
            if verbose>0: print "Mode of episode tracks was: "+str(mode)+"  "+str(maxl)
        else:
            if verbose>0: print "Have specified longest track to be "+str(maxl)

        minl=maxl*float(0.80)

        print "Looking for episodes between %f and %f seconds" % (maxl, minl)

        for t in tracks:
            length=t['length']
            if verbose>0: print "Track: %s" % t
            if length>minl and length<=maxl:
                rip_tracks.append(t['ix'])

    return rip_tracks
    

def usage():
    print """
    -h/--help         : this message
    -verbose          : verbose

    Base options
    -d/--dir=<path>   : overide default dest dir ("""+ripdir+""")
    -l/--log=<path>   : don't encode just log, default based on dvd name
    -r/--rip-only     : don't encode just rip
    -dvd=<path>       : path to DVD device

    Track selection
    -t/--tracks=<tracks>: just rip given tracks
    -b/--base=n       : start of numbering for episodes
    -e/--episodes     : disc contains episodes
    -1                : just rip longest track
    -m                : max length of episode (in minutes)

    Encoding Options
    -p/--passes=<passes>: override passes used by encode script


    Special options
    --nonav           : don't use dvdnav, use dvd

    """
    return

# Start of code
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hb:ed:vlm:t:p:1r",
                                   ["help", "vlc", "episodes", "dir=","verbose", "log=", "max=", "tracks=", "passes=", "rip-only", "dvd=", "nonav"])
    except getopt.GetoptError, err:
        usage()
        sys.exit(1)

    create_log=None
    rip_tracks=[]  

    for o,a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit(1)
        if o in ("-b", "--base"):
            base=int(a)
        if o in ("-e", "--episodes"):
            single_episode=False
        if o in ("-1" ):
            single_episode=True
        if o in ("-d", "--dir"):
            ripdir=a
        if o in ("-v", "--verbose"):
            verbose=1
        if o == "--vlc":
            use_vlc=True
        if o in ("-l", "--log"):
            if a:
                log=open(a, "w", 1)
            else:
                create_log=1
            encode=False
        if o in ("-r", "--rip-only"):
            encode=False
        if o in ("-m", "--max"):
            maxl=float(a)*60
        if o in ("-t", "--tracks"):
            rip_tracks=a.split(",")
        if o in ("-p", "--passes"):
            passes=a
        if o in ("--dvd"):
            dvd=a
        if o in ("--nonav"):
            nonav=True


    # First things first scan the DVD, TODO: rewrite with subprocess
    lsdvd="lsdvd -Oy "
    if dvd: lsdvd += dvd
    info=os.popen(lsdvd, "r").read()
    dvdinfo=eval(info[8:])
    tracks=dvdinfo['track']

    # if we haven't been told, guess which tracks to rip
    if len(rip_tracks)==0:
        rip_tracks = scan_dvd(dvdinfo, maxl)
        
    print "Ripping %d episodes" % (len(rip_tracks))

    # If we haven't specified a log name then make one up
    if create_log:
        ep_start=str(base)
        ep_end=str(base+len(rip_tracks)-1)
        log_name=os.getenv("HOME")+"/tmp/"+dvdinfo['title']+"-e"+ep_start+"-"+ep_end+".log"
        log=open(log_name, "w", 1)

    
    for t in rip_tracks:
        process_track(base, dvdinfo['title'], t)
        base=base+1
            
    # Eject the DVD
    dev=dvdinfo['device']
    real_dev=os.readlink(dev)
    final_dev=os.path.join(os.path.dirname(dev), real_dev)
    print "DVD on %s?" % (final_dev)
    os.system("umount "+final_dev)
    os.system("cdrecord --eject")
