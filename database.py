#!/usr/bin/python
#Script to combine different sentinel Granules and transform them into an array for further analysis

#------------------------------SETTINGS-------------------------
# Prepare the environment
import sys
import os
import qgis
from qgis.core import *
from PyQt4.QtGui import *
from PyQt4.QtCore import *

QgsApplication.setPrefixPath("/usr", False)
app = QgsApplication([], False)
app.initQgis()
sys.path.append('/usr/share/qgis/python/plugins')
sys.path.append('/home/jkm2/GIT/QGIS-scripts/pyModule')

from processing.core.Processing import Processing
Processing.initialize()
import processing as p
import shutil
import sqlite3

#-----------------------------PARAMETERS-------------------------
#### ---folders
# folder containing preprocessed NDVI raster images
imgFold="/home/jkm2/GIS/Sentinel_preprocess/test/ndvi_output22"
# path to landscape map /study area map
lsc="/home/jkm2/GIS/Analysis/Lsc_Map_FAO30/finalOutput/lsc_map.shp"
# working directory for temporary and output folders
parent="/home/jkm2/GIS/Sentinel_preprocess/"
orWodName="database"

###--settings

#starting Date as YYYYMDD

startD=20160101

#-----------------------------FUNCTIONS--------------------------

def mkWod(parent, orWodName):
# 0.1 create or define working folder
#input: wod (STRING)     - path to parent directory
#       wodName (STRING) - name of folder
#output:global variables wod - main folder
#                        tempWod - working folder ~/workingFiles
#                        finWod  - output folder ~/output

# create folder names
    global wod
    global tempWod 
    global finWod
    wod=os.path.join(parent, orWodName)
    tempWod=os.path.join(wod,"workingFiles")
    finWod=os.path.join(wod, "output")
    # remove previous folders
    if not os.path.exists(wod):
        os.makedirs(wod)
    if os.path.exists(tempWod):
        shutil.rmtree(tempWod)

    #create new folders
    os.makedirs(tempWod)
    if not os.path.exists(finWod):
        os.makedirs(finWod)
    # check
    if not os.path.exists(wod):
         print "problem creating working directory"
    else:
        print "created working folder  at %s\n" %(wod)

#TODO: function not used yet
def checkLst(Orlist, Outlist):
    #comparing image lists
    RlistNP=[y for y in Orlist[1] if os.path.basename(y) not in Outlist[0]]
    #if sublist is of length 0 exit right now
    if len(RlistNP) == 0:
        print "no image to correct.\n\n -->quitting script on trigger"
        quit()
    else:
        logstr2= "\nfound %d unprocessed images" %(len(RlistNP))
        Lfile.write(logstr2)
        print logstr2
        print "\nthe following images will be processed"
        print "output of function checkList:\n\n"
        for i in RlistNP:
            print os.path.basename(i)
    return RlistNP

def imgMd(ipat, stArea):
#2 IMAGE METADATA AND LAYER
    # input: ipat (STRING)   - path to unprocessed image
    #      : stArea (VECTOR) - path to study area vector file
    # output: Dictionary with the following data:
    #{ key : value  : type }

    #  baseName : basename without extension : STRING
    #  orImg : Qgs layer of Image : LAYER
    #  extImg : Image extension : STRING
    #  imgCrs : reference system : CRSOBJECT
    global  baseName
    global orImg
    global extImg
    global imgCrs
    baseName = os.path.basename(ipat)[0:-4]
    orImg = QgsRasterLayer(ipat, baseName)
    if not orImg.isValid():
        print "\nLayer failed to load!\n\n -->quitting script on image %s" % baseName
        raise SystemExit
    # image extension as string ADDED new extension to include only parts overlapping study site
    oldExt=orImg.extent()
    stExt=QgsVectorLayer(stArea, "stArea", "ogr").extent()
    newExt=oldExt.intersect(stExt)
    extImg=newExt.toString().replace(" : ",",")
    #check of reference system and reprojection
    imgCrs= orImg.crs()
    #output dictionary
    mdImg={}
    mdImg["baseName"]=baseName
    mdImg["orImg"]=orImg
    mdImg["extImg"]=extImg
    mdImg["imgCrs"]=imgCrs
    
    print "output of function 2 imgMd:\n\n %s" %str(mdImg)
    return mdImg

def sameDate(imgList, date):
# group images with same date
# input: imgList - LIST - list of paths to images
#        date - STRING - date in YYYYMMDD format
# output: list of images with the same date 
    smallList=[]
    for inner in imgList:
        if os.path.basename(inner)[11:19] == str(date):
            smallList.append(inner)
    if len(smallList) < 4:
        print "for this date there are only %s images:\n" %(str(len(smallList)))
        print smallList
    return smallList

def mkOvr(groupImg):
# create virtual raster for each group of images
# input: imgList - LIST - list of paths to images to be grouped in one virtual layer
# output: path to virtual layer
    print "starting creation of virtual raster"
    res=QgsRasterLayer(groupImg[0]).rasterUnitsPerPixelX()
    destRast=os.path.join(tempWod, "ND"+date+".vrt")
    stList=" ".join(groupImg)
    cmd="gdalbuildvrt -tr %s %s -tap %s %s" %(str(res), str(res), destRast, stList)
    print cmd
    os.system(cmd)
    if not QgsRasterLayer(destRast).isValid():
        print "problem creating virtual raster"
        raise SystemExit
    else:
        print "virtual raster created"
        return destRast

def sAr(finWod, date, myArray):
# check that folder and files exists and save array as .np file
# input: finWod -STRING - path to final folder
#        date   -INTEGER - date of image being processed
#        myArray-NUMPY ARRAY - array to be saved 
# output: NONE

# make directory to store numpy array (if needed)
    arFold=os.path.join(finWod, "database")
    if not os.path.exists(arFold):
        os.makedirs(arFold)
    # save array as date if not already present
    arPath=os.path.join(finWod, str(date)+".np")
    if not os.path.exists(arPath):
        np.save(arPath, myArray)
    #check
    if not np.array_equal(myArray, np.load(arPath)):
        print "problem saving array %s " %(date)
        raise SystemExit
    else:
        print "saved array %s" %(date)
#-----------------------------CODE-------------------------------
# 0 create working folders
mkWod(parent, orWodName)

# 1 get images List and establish date list
imgList=[]

for r,d,files in os.walk(imgFold):
    for f in files:
        if f.endswith(".tif"):
            imgD=f[11:19]
            if imgD > startD:
                imgList.append(os.path.join(r, f))

# 1.1 start cycle through each image date available
uniqueDates=list(set([os.path.basename(inner)[11:19] for inner in imgList]))

for date in uniqueDates:
    print "\nworking on images for date %s\n" %(str(date))
    # 2 merge images of the same date and clip to landscape 
    # 2.1 create groups of images based on newList

    # define groups based on dates 
    groupImg=sameDate(imgList, date)
    print "groups of images by date created\n"

    #2.2 combine raster and 
    vrtRast=mkOvr(groupImg)
    # 2.3 clip to study site
    clipRast=os.path.join(tempWod, "cliprast.tif")
    cmd="gdalwarp -cutline %s %s %s" %(lsc, vrtRast, clipRast)
    print cmd
    os.system(cmd)
    if not QgsRasterLayer(clipRast).isValid():
        print "problem with clipped raster %s" %(clipRast)
        raise SystemExit
    else:
        print "clipped raster succesfully: %s" %(clipRast)
    
# 2 translate image to array
    rast=gdal.Open(clipRast)
    myArray=np.array(rast.GetRasterBand(1).ReadAsArray())
    print myArray.shape
# 3 save array as .np file


#save raster as array
#arPath=os.path.join(finW

# closing cycle
    check=raw_input("\ncycle finished!\n continue? y/N")
    if check <> "y":
        raise SystemExit
