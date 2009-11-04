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
episodes=0
ripdir=os.getenv("HOME")+"/tmp"
base=1

# Start of code
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "b:e:d:v", ["episodes=", "dir=","verbose"])
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

    # First things first scan the DVD
    info=os.popen("lsdvd -Oy", "r").read()
    dvdinfo=eval(info[8:])
    tracks=dvdinfo['track']

    # Guess how many episodes if not told
    lt=dvdinfo['longest_track']
    long_enough=tracks[lt-1]['length']*0.80
    if episodes==0:
        if verbose>0:
            print "long_enough=%d" % (long_enough)
        shortest_track=long_enough
        for t in tracks:
            length=t['length']
            if length>long_enough:
                episodes=episodes+1
    else:
        # define long_enough by finding the n'th longest episode
        print "Hmmm"
        sys.exit(1)

    print "Ripping %d episodes" % (episodes)
    os.chdir(ripdir)
    
    for t in tracks:
        if t['length']>=long_enough:
            print "Ripping: %s" % (t)
            dump_file=dvdinfo['title']+"ep"+str(base)+".vob"
            rip_cmd="mplayer dvd://"+str(t['ix'])+" -dumpstream -dumpfile "+dump_file+" > /dev/null 2>&1"
            if verbose>0:
                print "cmd: %s" % (rip_cmd)

            # Do the rip syncronusly
            os.system(rip_cmd)
                
            # Now we have ripped the file spawn ps3enc.pl to deal with it
            enc_cmd="nice ps3enc.pl -p 1 "+dump_file+" > /dev/null 2>&1 &"
            if verbose>0:
                print "cmd: %s" % (enc_cmd)
            os.system(enc_cmd)

            # Next "track"
            base=base+1
            
    # Eject the DVD
    os.system("cdrecord --eject")
