#!/usr/bin/env python

import os
import sys
import time
from PyQt4.QtGui import *
from PyQt4.QtCore import *
import sys
import processing as p
import xml.etree.ElementTree as ET
from decimal import *
from pyproj import Proj, transform



#----------------------------DESCRIPTION
#Script to preprocess sentinel images with QGIS using GRASS Modules

#----------------------------PARAMETERS
#input directory
# remote dir ind="/home/jkm2/GIS/Sentinel_preprocess/test/input"
# local dir
ind="/home/matt/Dropbox/ongoing/BFH-Pastures/gis data/Sentinel_preprocess/test/input"
#code of image tiles to be analysed
tiles=['T30STA', 'T30STB', 'T30SUA', 'T30SUB']

#years to be considered
yea=[2016, 2017, 2018]

# metadata folder
mdPath="/home/matt/Dropbox/ongoing/BFH-Pastures/gis data/Sentinel_preprocess/test/metadata"
#path to Dem for topographic correction
dem="/home/matt/Dropbox/ongoing/BFH-Pastures/gis data/DEM/ASTER_big/asterDemUTM/asterDemUTM.vrt"

# output directory
outd="/home/matt/Dropbox/ongoing/BFH-Pastures/gis data/Sentinel_preprocess/test/output"

# working folder for temporary folders
temp1="/tmp/"
#------------------------------------------------------------------------------------------------
#### 0- TRIGGER
#TRIGGER to check if there are new images

##Search for images in input directory
# empty list with root
rlist=[] 
#path to images
multifolds=(ind+"/"+tile for tile in tiles)
#search for tiff files in folder
for i in multifolds:
    for r,d,files in os.walk(i):
        for f in files:
            if f.endswith(".tif"):
                rlist.append(os.path.join(r,f))


##Search in output directory

multifolds=(outd+"/"+tile for tile in tiles)
#list of output images

#actual search of images
Ochlist=[]
for i in multifolds:
    for r,d,files in os.walk(i):
        for f in files:
            if f.endswith(".tif"):
                Ochlist.append(f)

# get sublist of missing/non processed images

RlistNP=[y for y in rlist if os.path.basename(y) not in Ochlist]

#if sublist is of length 0 exit right now
if len(RlistNP) == 0:
    quit()
else:
    print "\nfound %d unprocessed images" %(len(RlistNP))
    print "\nthe following images will be processed"
    for i in RlistNP:
        print os.path.basename(i)

#### 1 set qgis variables and open mapset

#Python variables to be set for qgis

#Open qgis

#### 2 Import images

#list of of folders


# cycle through sublist
#Parallel instead of cycle
#args = [A, B]
#results = pool.map(solve1, args)

#***********Temporary variable to avoid loop
ipat=RlistNP[0]
	
#*************************************************
# get path of image
	# import image
fileName = ipat
fileInfo = QFileInfo(fileName)
baseName = fileInfo.baseName()
orImg = QgsRasterLayer(fileName, baseName)
if not orImg.isValid():
    print "\nLayer failed to load!"

#check of reference system and reprojection
imgCrs= orImg.crs()
print "\nImage CRS :", imgCrs.description()

if QgsRasterLayer(dem).crs() != imgCrs:
    print "\nreprojecting DEM to %" %imgCrs.description()
    #TODO: reproject DEM
else:
    print "\nall files are in the same CRS!"
 
 #### separate images in multiple layers
 # count number of bands and create list of names
brange=range(1,orImg.bandCount()+1)
blist=["band"+str(x) for x in brange]

# get coordinates
extImg="%f,%f,%f,%f" %(orImg.extent().xMinimum(),\
    orImg.extent().xMaximum(),\
    orImg.extent().yMinimum(),\
    orImg.extent().yMaximum())
###if not os.path.exists(bpat):
try:
	bPatDic
except NameError:
	bPatDic={}
if len(bPatDic) == 0:
    #create dictionary to hold band names and path
    bPatDic={}
    for i in brange:
        #name of band
        bname=blist[i-1]
        bstr="-b "+str(i)
        #save raster in temp folder
        print "saving %s" %(bname)
        tband=p.runalg("gdalogr:translate",orImg,100,True,"",0,"",extImg,False,6,4,75,6,1,False,0,False,bstr,None)
        if QgsRasterLayer(tband['OUTPUT']).isValid():
            print "layer %s is valid" %bname
            bPatDic[bname]=tband['OUTPUT']

#### 3 Athmospheric correction

#### create 6s parameters file for each band
# preparation parameters for 6S 
#For second line
#read end of basename for date and time
dateS=baseName[11:26]

year=dateS[0:4]
month=dateS[4:6]
day=dateS[6:8]

hours=dateS[9:11]
minutes=dateS[11:13]
seconds=dateS[13:15]
# hours and day in decimal time
dmin=round(100*float(minutes)/60,2)

dtime=str(hours)+"."+str(dmin)

#long lat (centre point)
long=orImg.extent().xMinimum()+((orImg.extent().xMaximum()-orImg.extent().xMinimum())/2)
lat=orImg.extent().yMinimum()+((orImg.extent().yMaximum()-orImg.extent().yMinimum())/2)
# transform long and lat in WGS 84
crsDest=QgsCoordinateReferenceSystem(4326)
xform = QgsCoordinateTransform(orImg.crs(), crsDest)
ncoord=xform.transform(QgsPoint(long,lat))

# For seventh line (average altitude in km)
#altitude average
demStats=p.runalg("grass7:r.univar",dem,None,"","",False,extImg,None)
statFile=open(demStats['output'], "r")
line=statFile.read().splitlines()[1]
#negative altitude average in km
avgDem=-1*float(line.split('|')[6])/1000

#For eighth line (Sensor band)
# band codes as dictionary
bcodes=range(166, 179)


####---- Loop through bands
for i in brange:
    band="band"+str(i)
    bRast=QgsRasterLayer(bPatDic[band])
    
    #path to parameter file
    Spath=str(temp1+baseName+band+"atcorParam.txt")
    Sfile=open(Spath, "w")
    #Writing paramater file
    #first line : satellite type
    firstLine="25\n"
    Sfile.write(firstLine)
    print "first line of 6S parameter file is %s" %firstLine

    print "centre-point coordinates are %s " %ncoord
    #second line : month,day,hh.ddd,long.,lat. :
    secondLine=str(month)+" "+str(day)+" "+str(dtime)+" "+str(ncoord.x())+" "+str(ncoord.y())+"\n"
    Sfile.write(secondLine)
    print "second line of 6S parameter file is (month, day, hh.ddd, long, lat):\n %s" %secondLine

    #third line of parameter file athmospheric model (1) continental
    if month < 3 or month > 10:
        atmMod=3
    else:
        atmMod=2
    thirdLine="%s \n" %atmMod
    Sfile.write(thirdLine)
    print "third line of 6S parameter file is  (Athmospheric model):\n %s" %thirdLine

    #C: 1 continental model
    fourthLine="1\n"
    Sfile.write(fourthLine)
    print "fourth line of 6S parameter file is (Aereosol model):\n %s" %fourthLine

    #D. Aerosol concentration model (visibility)

    fifthLine="-1\n"
    sixthLine="0\n"
    Sfile.write(fifthLine)
    Sfile.write(sixthLine)
    print "fifth and sixth line of 6S parameter file is (Visibility model):\n %s and %s" %(fifthLine, sixthLine)
    #E: Target altitude (xps): -1000
    # sensor platform (xpp): in kilometers -1.500
    seventhLine=str(avgDem)+"\n"
    eighthLine="-1000\n"
    Sfile.write(seventhLine)
    Sfile.write(eighthLine)
    print "7th and 8th lines of 6S parameter file is %s %s " %(seventhLine, eighthLine)
    # F : sensor band code
    ninthLine=str(bcodes[i-1])+"\n"
    Sfile.write(ninthLine)
    print "9th line of 6S parameter file is %s " %(ninthLine)
    Sfile.close()
    #minimum and maximum pixel value
    #range of values
    prov=bRast.dataProvider()
    stats=prov.bandStatistics(1)
    pMin=stats.minimumValue
    pMax=stats.maximumValue
    pRange=str(pMin)+","+str(pMax)

    # launch athmospheric correction
    #TODO: improve algorithm
    #corrImg=p.runalg("grass7:i.atcorr",bRast,pRange,\
       # dem, None,mDpat,"0.0,255.0",False,True,False,False,"117975.229898,500013.259194,3470154.5897,3769391.47316",0,None)
        # launch topographic correction




	#### 4 Masking out bad pixels

	# band of quality assessment

	# bitwise and to exclude clouds

	# bitwise and to exclude snow



	#### 5 Vegetation indices calculation

	# get bands for NDVI

	# calculate soil adjusted NDVI

	# get swir band (with pansharpening?)

	# other vegetation index



	#### 6 Exporting
	
	# Create image-specific folder in outd

	# create folder for all bands

	# create folder for vegetation indices

	# Export images

# end of cycle



### 7 write logfile

# add script name

# add date and time

# add number of images

#8 Clean up
#bPatDic={}
