#!/usr/bin/python
#Script to calculate productivity based on regression values of ndvi vs biomass assessment (pre-made). Lso outputs degradation assesments based on productivity and landscape map. Inputs: numpy arrays; outputs: ??? 

#------------------------------SETTINGS-------------------------
# Prepare the environment
import sys
import os
import qgis
from qgis.core import *
from PyQt4.QtGui import *
from PyQt4.QtCore import *

#TODO check if QGIS is actually needed

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
from decimal import *
import numpy as np
import gdal
import osgeo.osr as osr
import multiprocessing as mu

#-----------------------------PARAMETERS-------------------------
#folder with numpyarrays for each image
inFold="/home/jkm2/GIS/Sentinel_preprocess/database/output"

#landscape map
lsc="/home/jkm2/GIS/Analysis/Lsc_Map_FAO30/finalOutput/lsc_map.tif"

# working directory for temporary and output folders
parent="/home/jkm2/GIS/Sentinel_preprocess/"
orWodName="productivity"

# Values for productivity calculations
#slope

sloProd=38325.390
# intercept
intProd=-2738

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
    #if os.path.exists(tempWod):
     #   shutil.rmtree(tempWod)

    #create new folders
    if not os.path.exists(tempWod):
        os.makedirs(tempWod)
    if not os.path.exists(finWod):
        os.makedirs(finWod)
    # check
    if not os.path.exists(wod):
         print "problem creating working directory"
    else:
        print "created working folder  at %s\n" %(wod)

def checkLst(orList, outList):
    # function to compare different lists and return only the ones that are not present in the second
    # input: orList  - LIST - list of dates to be processed
    #        outList - LIST - list of already processed images
    #comparing image lists
    RlistNP=[y for y in orList if y not in outList]
    #if sublist is of length 0 exit right now
    if len(RlistNP) == 0:
        print  "no image to correct.\n\n -->quitting script on trigger"
        raise SystemExit
    else:
        logstr2=  "\nfound %d unprocessed images" %(len(RlistNP))
        print logstr2
        print "\nthe following images will be processed"
        print "output of function checkList:\n\n"
        return RlistNP

def makeSim(refLay, rast):
# function to convert raster to a shape equal to the reference and extract array
#input:refLay - QGSRASTERLAYER - reference layer
#      rast - STRING - raster to be changed

# output: ARRAY
    refCrs=refRast.crs().authid()
    destRast=os.path.join(tempWod, "newLsc.tif")
    gdalExt=[refRast.extent().xMinimum(), refRast.extent().yMinimum(),  refRast.extent().xMaximum(), refRast.extent().yMaximum()]
    gdalExtSt="%s %s %s %s" %(gdalExt[0],gdalExt[1], gdalExt[2], gdalExt[3])
    #build gdal call
    cmd="gdalwarp -of GTiff -ot Int16 -t_srs %s -te %s -tr 10 10 -r mode %s %s" %(refCrs, gdalExtSt,lsc, destRast)
    # execute gdal call
    print cmd
    global cmd
    #test=input("\nis cmd correct?")
    if not os.path.exists(destRast):
        os.system(cmd)
    rast=gdal.Open(destRast)
    band=rast.GetRasterBand(1)
    array=band.ReadAsArray()
    return array

def mkBio(arr, sloProd, intProd):
#function to translate NDVI values to biomass quantity (in grams)
# input: arr - ARRAY - array with ndvi values
#        sloProd - FLOAT - slope of regression analysis
#        intProd - FLOAT - intercept of regression analysis
#output: ARRAY with biomass values

    prodAr=(arr*sloProd)-intProd
    return prodAr

def maskAr(ar1, ar2, val):
# function to mask Ar2 based on values in Ar1
# input: ar1 - ARRAY - array to create the mask
#        ar2 - ARRAY - array to be masked
#        val - NUMBER- value to search for in Ar1

# output: ARRAY wiith Ar2 values only where Ar1 value is VAL

#create mask on landscape map
    #apply mask on biomass array
    #TODO problem with this operation!
    mAr=np.ma.masked_where(ar1!=val, ar2)
    print "avg value of category %s is %s" %(val, np.average(mAr))
    return mAr

def getVals(Ar):
# function to get threshold values for categoring biomass differences
# input: Ar - ARRAY - array with biomass values
# output: LIST with minimum, Very degraded, Degraded, Healthy, Potential
    pot=Decimal(np.percentile(Ar, 90))
    arMin=Decimal(np.amin(Ar))
    rang=pot-arMin
    arVD=(rang*Decimal(0.25))+arMin
    arD=(rang*Decimal(0.5))+arMin
    arH=(rang*Decimal(0.75))+arMin
    finLst=[arMin, arVD, arD, arH, pot]
    #check
    print "threshold values are:\n %s %s %s %s %s" %(arMin, arVD, arD, arH, pot)
    #test=Decimal(len(Ar[Ar>pot]))/Decimal(len(Ar))
    #print "cells above 90th perc: %s" %(test)
    return finLst



#-----------------------------CODE-------------------------------
#create working directory
mkWod(parent, orWodName)

#Read files from input folder
inList={}
for r, d, files in os.walk(inFold):
    for f in files:
        if f.endswith(".tif"):
            date=f[2:10]
            print "date found :%s" %(date)
            inList[date]=(os.path.join(r,f))

#TODO: add trigger to eliminate already processed arrays:
print "\nfound images to be processed!\n"+" ".join(inList.keys())+"\n\n"

# make landscape map compatible with ndvi images and extract array
refRast= QgsRasterLayer(inList[inList.keys()[0]])
lscAr= makeSim(refRast, lsc)

# add cycle through list of arrays

for date in inList.keys():
    print "working on date %s\n" %(date)
    myArPath=inList[date]

    #load array
    myRast=gdal.Open(myArPath)
    band=myRast.GetRasterBand(1)
    arr=band.ReadAsArray()
    #TODO add collect metadata to create raster through gdal

    #TODO: add check between landscape and arr shape
    #Array preparation
    #remove values below 0 and nodata
    arr2=np.ma.masked_where(arr<=0, arr)
    arr3=np.ma.masked_invalid(arr2)

    #masking out areas outside landscape map
    arr4=np.ma.masked_where(lscAr<=0, arr3)
    # 1 Transform NDVI values to Biomass values in grams(?)
    bArr=mkBio(arr4, sloProd, intProd)

    global bArr
    #Degradation map
    #loop to unique values in landscape map
    lCat=list(np.unique(lscAr))
    lCat.remove(0)

    degAr=np.ma.copy(bArr)
    degAr2=np.ma.copy(bArr)
    degAr2.fill(999)

    #prepare for parallel processing with mapDeg function
    for lsCat in lCat:
        print "working o n category %s" %(lsCat)

        mAr=maskAr(lscAr, degAr, lsCat)
        tmask=mAr.mask
        
        mArClean=mAr[mAr.mask==False]
        mArClean2=mArClean[~np.isnan(mArClean)]
    #raise SystemExit

    #get threshold values for this area
                
    # condition to check if layer is not empty
        if np.ma.count(mArClean2)>5:
            tVals=getVals(mArClean2)

    # rescale values based on quantile calculation
            mArClean2[mArClean2<=tVals[1]]=1
            mArClean2[(mArClean2>=tVals[1]) & (mArClean2<tVals[2])]=2
            mArClean2[(mArClean2>=tVals[2]) & (mArClean2<tVals[3])]=3
            mArClean2[mArClean2>=tVals[3]]=4

            print "values of reclassed array are : %s" %(np.unique(mArClean2))
            degAr2[(tmask==False) & (~np.isnan(degAr))]=mArClean2
        else:
            print "no valid values in mask"
            

    # Filling values of DegAr
            degAr2[(tmask==False) & (~np.isnan(degAr))]=999

        print "cycle finished"

#temporary substitution



    # export array degAr to raster
    print "exporting array to raster"
    finRast=os.path.join(finWod, "PD"+date+".tif") 


    rfGeo=myRast.GetGeoTransform()

    drv = gdal.GetDriverByName("GTiff")
    ds = drv.Create(finRast,myRast.RasterXSize, myRast.RasterYSize, 2, gdal.GDT_Float32)
    ds.SetGeoTransform(rfGeo)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(32630)
    ds.SetProjection(srs.ExportToWkt())

    #actual writing of values
    ds.GetRasterBand(1).WriteArray(bArr)
    ds.GetRasterBand(2).WriteArray(degAr2)

    #just cleaning
    ds=None
    myRast=None
    del degAr
    del degAr2
    del mAr
    del mArClean
    del mArClean2

    print "finished creating raster for date %s" %(date)

print "all images processed. script finished"




#TODO add way to import already processed arrays

# 2 Merge images to obtain average values

#TODO add other functions depnding on 
