#!/usr/bin/python
#
# RIP DVD
#
# Biased toward ripping a series DVD into VOB files and then launching ps3enc on them
#

import os
import sys
import getopt

verbose=0
log=None
encode="list"
episodes=0
ripdir=os.getenv("HOME")+"/tmp"
base=1


def process_track(ep, title, track):
    print "Ripping: %s" % (track)

    name=title+"-"+str(ep)

    dump_dir=ripdir+"/"+name
    if not os.path.isdir(dump_dir):
        os.mkdir(dump_dir)

    os.chdir(dump_dir)
    
    dump_file=dump_dir+"/"+name+".vob"
    rip_cmd="mplayer dvd://"+str(t['ix'])+" -dumpstream -dumpfile "+dump_file+" > /dev/null 2>&1"
    if verbose>0:
        print "cmd: %s" % (rip_cmd)
        os.system(rip_cmd)


    if log:
        log.write(dump_file+"\n");
        log.flush()
    else:
        # Now we have ripped the file spawn ps3enc.pl to deal with it
        enc_cmd="nice ps3enc.pl "+dump_file+" > /dev/null 2>&1 &"
        if verbose>0:
            print "cmd: %s" % (enc_cmd)
            os.system(enc_cmd)
    

# Start of code
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "b:e:d:vl:m:", ["episodes=", "dir=","verbose", "log=", "max="])
    except getopt.GetoptError, err:
        usage()

    for o,a in opts:
        if o in ("-b", "--base"):
            base=int(a)
        if o in ("-e", "--episodes"):
            episodes=a
        if o in ("-d", "--dir"):
            ripdir=a
        if o in ("-v", "--verbose"):
            verbose=1
        if o in ("-l", "--log"):
            log=open(a, "w", 1)
            
        if o in ("-m", "--max"):
            max=float(a)*60

    # Are we logging


    # First things first scan the DVD
    info=os.popen("lsdvd -Oy", "r").read()
    dvdinfo=eval(info[8:])
    tracks=dvdinfo['track']
    rip_tracks=[]

    # Define our max criteria
    if max==None:
        lt=dvdinfo['longest_track']
        max=tracks[lt-1]['length']

    min=max*0.80

    print "Looking for episodes between %f and %f seconds" % (max, min)

    for t in tracks:
        length=t['length']
        if verbose>0:
            print "Track: %s" % t
        if length>min and length<=max:
            rip_tracks.append(t)

    print "Ripping %d episodes" % (episodes)
    
    for t in rip_tracks:
        process_track(base, dvdinfo['title'], t)
        base=base+1
            
    # Eject the DVD
    os.system("cdrecord --eject")
