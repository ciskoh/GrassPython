#!/usr/bin/env python

import grass.script as gs
import datetime as dt

def main():
    gs.run_command('g.region', flags='p')


if __name__ == '__main__':
    main()

#loop to set timestamp of images

start=dt.datetime(2013, 03, 15) #minus 1 to use in the cycle

for x in range(1,58):
    name="monthlyAverageNDVI.%d" % (x) #name of processed map
    dl=30*x
    datetemp=start + dt.timedelta(days=dl)
    stdate=str(datetemp)
    date=stdate[:8]+"15"+stdate[10:]
    print "working on image" + name + "corresponding to date" + str(date)
    gs.run_command('t.register', input="ndviAverageM@L8Phen", maps=name, start=date, overwrite=True)

print "finished!"