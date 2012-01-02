#!/usr/bin/python
#
# Query an  video file and pull out various bits of information that will be useful
# for later encoding
#
# (C)opyright 2011 Alex Bennee <alex@bennee.com>
#
# Licenced under the GPL version 3 Which means no warrenty! Break it
# you get to keep both pieces, fix it then please send me the glue :-)
#

# Testing code
if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:], "v", ["verbose"])
    except getopt.GetoptError, err:
        usage()

    verbose=False
    for o,a in opts:
        if o in ("-v", "--verbose"):
            verbose=True

    if len(args)>=1:
        for a in args:
            fp = os.path.realpath(a)
            v = video_source(fp, verbose)
            v.analyse_video()
            print v
    else:
        import doctest
        doctest.testmod()
