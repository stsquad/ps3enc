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
maxl=None

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
        opts, args = getopt.getopt(sys.argv[1:], "b:e:d:vlm:", ["episodes=", "dir=","verbose", "log=", "max="])
    except getopt.GetoptError, err:
        usage()

    create_log=None

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
            if a:
                log=open(a, "w", 1)
            else:
                create_log=1
        if o in ("-m", "--max"):
            maxl=float(a)*60

    # First things first scan the DVD
    info=os.popen("lsdvd -Oy", "r").read()
    dvdinfo=eval(info[8:])
    tracks=dvdinfo['track']
    rip_tracks=[]  

    # Define our max criteria
    if maxl==None:
        lt=dvdinfo['longest_track']
        maxl=float(tracks[lt-1]['length'])
        if verbose>0:
            print "Longest track was no: "+str(lt)+" @ "+str(maxl)

        
    minl=maxl*float(0.80)

    print "Looking for episodes between %f and %f seconds" % (maxl, minl)

    for t in tracks:
        length=t['length']
        if verbose>0:
            print "Track: %s" % t
        if length>minl and length<=maxl:
            rip_tracks.append(t)

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
