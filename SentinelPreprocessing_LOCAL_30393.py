#!/usr/bin/env python
#----------------------------DESCRIPTION
#Script to preprocess sentinel images with QGIS using GRASS Modules

#------------------------------SETTINGS-------------------------
# Prepare the environment
import sys
import os
import qgis
from qgis.core import *
from PyQt4.QtGui import *


app = QgsApplication([],True, None)
app.setPrefixPath("/usr", True)
app.initQgis()
sys.path.append('/usr/share/qgis/python/plugins')
from processing.core.Processing import Processing
Processing.initialize()
import processing as p



import time
import xml.etree.ElementTree as ET
from decimal import *
from pyproj import Proj, transform
from multiprocessing import Pool
import datetime
import numpy as np
from osgeo import gdal


#----------------------------PARAMETERS
#input directory
# remote dir 
ind="/mnt/cephfs/data/BFH/Geodata/World/Sentinel-2/S2MSI1C/GeoTIFF"
# local dir ind="/home/matt/Dropbox/ongoing/BFH-Pastures/gis data/Sentinel_preprocess/test/input"
#code of image tiles to be analysed
tiles=['T30STA', 'T30STB', 'T30SUA', 'T30SUB']

#years to be considered
yea=[2016, 2017, 2018]

#
#path to Dem for topographic correction
dem="/home/jkm2/GIS/DEM/ASTER_big/asterDemUTM/asterDemUTM_comp.tif"

# output directory
#local dir outd="/home/matt/Dropbox/ongoing/BFH-Pastures/gis data/Sentinel_preprocess/test/output"
#remote dir
outd="/home/jkm2/GIS/Sentinel_preprocess/test/output"
# working folder for temporary folders
temp1="/home/jkm2/GIS/Sentinel_preprocess/test/WOD"
#-------------------------------CODE---------------------------------

####LOG
timestr=(
    '1{date:%Y-%m-%d %H:%M:%S}'.format( date=datetime.datetime.now() )
    )
    
logpath=outd+"/"+"log.txt"
Lfile=open(logpath, "w")
logtext= "Athmospheric correction using SentinelPreprocessing.py started at %s" %(timestr)
Lfile.write(logtext)
print logtext

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
    print "no image to correct.\nQuitting program"
    quit()
else:
    logstr2= "\nfound %d unprocessed images" %(len(RlistNP))
    Lfile.write(logstr2)
    print logstr2
    print "\nthe following images will be processed"
    for i in RlistNP:
        print os.path.basename(i)
	Lfile.write(os.path.basename(i))

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
#ipat=RlistNP[0]
	
#*************************************************
# get path of image
	# import image
#calling process as function
def correct(ipat):
    fileName = ipat
    baseName = os.path.basename(dem)[0:-4]
    orImg = QgsRasterLayer(fileName, baseName)
    if not orImg.isValid():
        print "\nLayer failed to load!"
    
    #check of reference system and reprojection
    imgCrs= orImg.crs()
    print "\nImage CRS :", imgCrs.description()

    if QgsRasterLayer(dem).crs() != imgCrs:
        print "\nreprojecting DEM to %s" %(imgCrs.description())
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
    dateS=baseName.split("_")[2]
    print "date of image %s is %s" %(baseName,dateS)
    year=dateS[0:4]
    month=dateS[4:6]
    day=dateS[6:8]

    hours=dateS[9:11]
    minutes=dateS[11:13]
    seconds=dateS[13:15]
    # hours and day in decimal time
    dmin=round(100*float(minutes)/60,0)

    dtime=str(hours)+"."+str(dmin/100)[2:]

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

    try:
        corrDic
    except NameError:
        corrDic={}
            
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
        ds = gdal.Open(dem)
	myarray = np.array(ds.GetRasterBand(1).ReadAsArray())
        pMin=np.nanmax(myarray)
        pMax=np.nanmin(myarray)
        pRange=str(pMin)+","+str(pMax)
	print 'pixel range is %s' %(pRange)
        # launch athmospheric correction
        
	print "launching athmospheric correction on image"+baseName[-10:]
        corrImg=p.runalg("grass7:i.atcorr",bRast,pRange,None, None,Spath,pRange,False,True,False,False,extImg,0,None)
        #corrImg2=p.runalg("gdalogr:translate",corrImg['output'],100,True,"",0,"",extImg,False,6,4,75,6,1,False,0,False,"",None)
	if QgsRasterLayer(corrImg['output']).isValid:
		print "athmospheric correction is valid"
        	corrDic[band]=corrImg['output']

    # preparing list of inputs for topographic correction
    inpList=[corrDic[x] for x in blist ]
    #### TOPOGRAPHIC CORRECTION
    # preparation
    #calculating sun azimuth and zenith

    #sunMod= p.runalg("grass7:r.sunhours",year,month,day,hours,minutes,seconds,"","",False,False,extImg,0,None,None,None)
    #
    ##function to extract minimum value from metadata
    #def getMin(rast):
    #    layer=QgsRasterLayer(rast).metadata()
    #    text1=layer.split("STATISTICS_MINIMUM")[1]
    #    text2=text1.split("</p")[0][1:]
    #    return float(text2)
    #    
    ##calling function on results of Sun Mod
    #elevation=getMin(sunMod['elevation'])
    #zenith=90-elevation
    #azimuth=getMin(sunMod['azimuth'])
    ##illumination model
    #ilMod=p.runalg("grass7:i.topo.coor.ill",dem,elevation,azimuth,extImg,0,None)


    ##actual topographic correction
    #topocorr=p.runalg("grass7:i.topo.corr",inpList,ilMod['output'],zenith,0,False,extImg,None)
    #
    ##extracting path to topo corrected tif files
    #topocList=[]
    #for r,d,files in os.walk(topocorr['output']):
    #        for f in files:
    #            if f.endswith(".tif"):
    #                topocList.append(os.path.join(r,f))
    #
    ##verify topographically corrected files
    #for i in topocList:
    #    if not QgsRasterLayer(i).isValid():
    #        print "problem with topographically corrected files"
    #    else:
    #        print " all bands have been topographically corrected"


    #Exporting Images
    #scene idnetifier for folder
    scId=baseName.split("_")[5]
    outpath=os.path.join(outd,scId)
    if not os.path.exists(outpath):
        os.makedirs(outpath)

    outpath2=outpath+"/"+baseName+".tif"
    final=p.runalg("gdalogr:merge",inpList,False,True,6,outpath2)
    
    #cleanup
    bPatDic={}
    corrDic={}
    
    return final['OUTPUT']
    
#calling function
pool=Pool(88)
results=pool.map(correct, RlistNP)
#print RlistNP
#for ipat in RlistNP:
    #print ipat
    #res=correct(ipat)
    
    
    
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
#Log conclude
timestr2=(
    '1{date:%Y-%m-%d %H:%M:%S}'.format( date=datetime.datetime.now() )
    )
    
logstr="Corrected images are available in %s" %(outd)
logstr2="Script finished correctly at %s" %(timestr2)


# When your script is complete, call exitQgis() to remove the provider and
# layer registries from memory
qgs.exitQgis()




