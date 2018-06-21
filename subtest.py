
#!/usr/bin/python
#Script to create landscape unit map using land use and land cover raster
#CONFIGURATION: FAO land cover map 
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

from pyproj import Proj, transform
from multiprocessing import Pool
import datetime
import numpy as np
from osgeo import gdal
import shutil
import ogr2ogr
import gdal_reclassify
from math import sqrt
from shutil import copyfile
import time

#-----------------------PARAMETERS------------------------------------------
#### Linux Server PATH TO INPUT FILES FOR TESTING
dem="/home/jkm2/GIS/DEM/complete_dem_Filled.tif"
lu="/home/jkm2/GIS/land_cover/FAO/LandCoverFAO_30.tif"

#### Linux local
# DEM dem="/home/matt/Dropbox/ongoing/BFH-Pastures/gis data/DEM/complete_dem_Filled.tif"
# LAND COVER lu="/home/matt/Dropbox/ongoing/BFH-Pastures/gis data/land cover/FAO/LandCoverFAO_30.tif"

#### Output directory location & name
# linux server 
parent="/home/jkm2/GIS/Analysis"
# linux local wod="/home/matt/Dropbox/ongoing/BFH-Pastures/gis data/Analysis"
orWodName="Lsc_Map_FAO2"

#### MAP CREATION PARAMETERS
#crs of utm zone
ref=32630
#### Land use categories
lulist=["Irrig. agriculture", "Dry agriculture", "Steppa", "Open shrubland", "Open forest", "Dense forest"]

#### ASPECT PARAMETERS and category names
asrul="0 thru 90 = 1 north\n270 thru 360 = 1 north\n90 thru 270 = 2 east"
asplist=["North", "South"]

#### SLOPE PARAMETERS
slorul="0 thru 10 = 1 flat\n10 thru 15 = 2 sloping\n15 thru 30 = 3 steep\n30 thru 100 = 4 very steep"
slolist=["Flat","Gently sloping" ,"Sloping", "Steep", "Very steep"]

### Minimum area size of landscape units in sq m
minAr=20000

### Pixel resolution in meters
utmPix=30

#----------------------------------------FUNCTIONS
# 0.1 Importing files interactively

####  TODO: remove "#" from the lines before 
## invoking screen to select dtm and land use raster
#qfd = QFileDialog()
#title = ' **** SELECT LAND USE *****'
#path = "/home/jkm2/GIS/Analysis"
#lu = QFileDialog.getOpenFileName(qfd, title, path)
#
#title = ' **** SELECT DTM *****'
#dem = QFileDialog.getOpenFileName(qfd, title, path)
# simplify function needs a string path to "rawrast" files
## 5. function to simplify rasters 

def fileImport(path):
# 0.2 Import files
# input: path to file
# output: QgsRasterLayer

    fileName = path
    fileInfo = QFileInfo(fileName)
    baseName = fileInfo.baseName()
    lay = QgsRasterLayer(fileName, baseName)
    if not lay.isValid():
	print "Layer failed to load!"
    else:
        return lay
def mkWod(parent, orWodName):
# 0.3 create or define working folder
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
    if os.path.exists(wod):
        shutil.rmtree(wod)
    #create new folders
    os.makedirs(wod)
    os.makedirs(tempWod)
    os.makedirs(finWod)
    # check
    if not os.path.exists(wod):
         print "problem creating working directory"

def getCoord(lay, form):
# 1.1 Get layer extension as string
# input: lay (QgsRasterLayer) - path to layer 
#        form (boolean)       - 0 for string 1 for list
# output: string/List of coordinates in layer CRS
    extLay=lay.extent().toString().replace(" : ",",")
    if form == 0: 
        return extLay
    else:
        return extLay.split(",")


def reproj(lay, ref, utmPix):
# 1.2 reprojecting layers to UTM 
# input: lay - layer to reproject, ref - UTM reference code ("EPSG"), utmPix - pixel resolution in meters
# output: reprojected layer
    refStr="EPSG:"+str(ref)
    
    if lay.crs() != QgsCoordinateReferenceSystem(ref):
        #parameters
        newRast=os.path.join(tempWod, "reprLay.tif")
        #gdal command
        cmd="gdalwarp -s_srs %s -t_srs %s -tr %s %s %s %s" %(lay.crs().authid(), refStr,utmPix, utmPix, lay.source(), newRast)
        print cmd
        os.system(cmd)

        newLay=QgsRasterLayer(newRast)
    else:
        print "layer already in CRS % s" %(refStr)
        newLay=lay 
    
    if not newLay.isValid():
        print "layer transformation not valid"
        raise SystemExit
    else:
        return newLay

def sameExt(rast1,rast2):
# function to make two overlapping raster the same extent
#input: rast1 (STRING) - path to raster 1
#       rast2 (STRING) - path to raster 2

#output: list of Strings -[0]path to new raster1 
#                         [1]path to new raster2

# New extent as Gdal formatted list (xmin, ymax, xmax, ymin)
    print "starting function sameExt\n"
    rast1ex=QgsRasterLayer(rast1).extent()
    rast2ex=QgsRasterLayer(rast2).extent()
    global newExt
    newExt=rast1ex.intersect(rast2ex).toString().replace(" : ", ",")
    gdalExt=newExt.split(",")
    gdalExt=[gdalExt[i] for i in [0,3,1,2]]
# setting new extension to raster 1
    newRast1 = os.path.join(tempWod, "newRast1.tif")
    cmd="gdal_translate -projwin %s %s %s %s %s %s " %(gdalExt[0], gdalExt[1], gdalExt[2], gdalExt[3],rast1, newRast1)
    print cmd
    os.system(cmd)
    # check
    if not QgsRasterLayer(newRast1).isValid():
        print "problem resizing raster 1"
        raise SystemExit
# setting new extension to raster 2
    newRast2=os.path.join(tempWod, "newRast2.tif")
    cmd="gdal_translate -ot UInt32 -projwin %s %s %s %s %s %s " %(gdalExt[0], gdalExt[1], gdalExt[2], gdalExt[3],rast2, newRast2)
    print cmd
    os.system(cmd)
# check
    if not QgsRasterLayer(newRast2).isValid():
        print "problem resizing raster 2"
        raise SystemExit
    else:
        print "completed translating raster to same extension\n"
        return [newRast1, newRast2] 

def compoRast(lc,slo,asp,tempWod):
# combine land cover , slope and aspect to create landscape map
# input, lc      - STRING - path to land cover raster
#        slo     - STRING - path to slope raster
#        asp     - STRING - path to aspect raster
#        tempWod - STRING - path to working folder
# output - STRING - path to new composite raster
    print "starting function compoRast"
    lscUnit=os.path.join(tempWod,"lsc_Unit.tif")
    cmd="gdal_calc.py -A %s -B %s -C %s --outfile=%s --calc='(A*100)+(B*10)+C'" %(lc, slo, asp, lscUnit)
    print(cmd)
    os.system(cmd)
    #check
    if not QgsRasterLayer(lscUnit).isValid():
        print "problem combining lc, slope and aspect"
        raise SystemExit
    else: 
        print "Landscape map created\n"
        return lscUnit


def simp2(lay,minAr):
# simplify raster based on minimum area
# input: lay - , minAr - size of min. homogeneous area
# implicit input: tempWod - folder for working files
# output: simplified layer
    print "starting function simp2\n"
    res=lay.rasterUnitsPerPixelX()
# calculating  minimum area in pixels
    minPix= int(round(sqrt(minAr)/res))
    if minPix%2 == 0:
        minPix=minPix+1
# removing areas smaller than minPix
#destination file
    simpRast=os.path.join(tempWod, "simpRast.tif")
    cmd="gdal_sieve.py -st %s -8 %s %s" %(str(minPix), lay.source(),simpRast)
    print cmd
    os.system(cmd)
# check
    if not QgsRasterLayer(simpRast).isValid():
        print "problem removing small area from the raster %s\n" %(lay.source())
        raise SystemExit
    else:
        print "removed small areas from raster %s" %(lay.source())
        print "new simplified raster located in %s\n" %(simpRast)
        return simpRast 

####-------------------CODE----------------------------

### A-  Importing and preprocessing

mkWod(parent,orWodName)
print "working directory path:"
print wod
print tempWod
print finWod

# import dem as layer ldem
ldem=fileImport(dem)

# import land cover as layer llu
llu=fileImport(lu)

#reproject dem
newDem=reproj(ldem, ref, utmPix)

# reproject land cover
newLu=reproj(llu, ref, utmPix)
# Allignment and resolution check
print "Land cover (newLu) and dem (newDem) were reprojcted to %f " %(ref)
     
### making layer same extension
newRastList=sameExt(newLu.source(), newDem.source())
newLu2=newRastList[0]
newDem2=newRastList[1]
#### B- ASPECT and slope from DEM

# calculate aspect
print "start creating aspect and slope rasters\n"
tempAsp=os.path.join(tempWod, "asp.tif")
cmd="gdaldem aspect %s %s" %(newDem2, tempAsp)
os.system(cmd)
# asp=p.runalg("gdalogr:aspect", newDem2,1,False,False,False,True,None)
#tempAsp=asp['OUTPUT']
###2 SLOPE
tempSlo=os.path.join(tempWod, "slo.tif")
cmd="gdaldem slope -p %s %s" %(newDem2, tempSlo)
os.system(cmd)
if QgsRasterLayer(tempAsp).isValid() and QgsRasterLayer(tempSlo).isValid():
    print "slope and aspect calculation successfull"
else:
    print "problem creating aspect and slope raster\n"
    raise SystemExit

#slo=p.runalg("gdalogr:slope",newDem2,1,False,False,True,1,None)
#tempSlo=slo['OUTPUT']

# reclassify aspect and slope in classes based on asprul and slorule
print "starting aspect and slope reclassification\n"
#slope reclass
classSlo=tempWod+"classAsp.tif"

cmd="gdal_reclassify.py -c '<90,<270,<360' -r '1,2,1' %s %s" %(tempSlo, classSlo)
print cmd
#os.system(cmd)

aspClass=os.path.join(tempWod, "aspClass.tif")
sloClass=os.path.join(tempWod, "sloClass.tif")


p.runalg("grass7:r.reclass", tempAsp,"",asrul,newExt,0,aspClass)
p.runalg("grass7:r.reclass",tempSlo,"",slorul,newExt,0,sloClass)

if QgsRasterLayer(aspClass).isValid() and QgsRasterLayer(sloClass).isValid():
    print "\naspect and slope classification successfull\n"
else:
    print "problem classifying aspect and slope"
    raise SystemExit

#### C - Combining all layers and simplifying
# combining all raster layer in one landscape map
lscUnit=compoRast(newLu2, sloClass, aspClass, tempWod)

#simplify landscape map
lscLay=QgsRasterLayer(lscUnit)
lscUnitSimp=simp2(lscLay, minAr)
### d translating raster to vector
lscVect=os.path.join(tempWod, "lscVect.shp")
cmd="gdal_polygonize.py %s -f 'ESRI Shapefile' %s " %(lscUnitSimp, lscVect)
os.system(cmd)
#lscvect=p.runalg("gdalogr:polygonize",lscUnitSimp,"code",none)

#add attributes "land use", "slope", "aspect", "area"
vect = QgsVectorLayer(lscVect, "lsc", "ogr")

#dissolve polygons by code

vectDiss=os.path.join(tempWod, "vectDiss.shp")
vectDiss=p.runalg("gdalogr:dissolvepolygons",lscVect,"geometry","code",True,False,False,False,False,None,"",vectDiss)['OUTPUT_LAYER']
LvectDiss=QgsVectorLayer(vectDiss, "dissolved", "ogr")
#Add Attributes:
res = LvectDiss.dataProvider().addAttributes([\
    QgsField("landCover", QVariant.String ),\
    QgsField("aspect", QVariant.String),\
    QgsField("slope", QVariant.String),\
    ])
LvectDiss.updateFields()

layer=LvectDiss
layer.startEditing()
# removing null area
expr = QgsExpression( "\"code\"=0" )
it = layer.getFeatures( QgsFeatureRequest( expr ) )
ids = [i.id() for i in it]
layer.setSelectedFeatures( ids )
for fid in ids:
    layer.deleteFeature(fid)

layer.commitChanges()


#fill attributes with category names


layer.startEditing()
iter = layer.getFeatures()
for feature in iter:
    numb=feature['code']
    
    a,b,c=str(numb)
    feature['landCover'] = lulist[int(a)-1]
    feature['aspect']= asplist[int(b)-1]
    feature['slope'] = slolist[int(c)-1]
    #print numb, feature['land_use'], feature['slope'], feature['aspect']
    layer.updateFeature(feature)

layer.commitChanges()



####Export all layers

#exporting final landscape map "lsc_map"
QgsVectorFileWriter.writeAsVectorFormat(layer, finWod+'/lsc_map.shp', "", None, "ESRI Shapefile")

# exporting raster map
copyfile(lscUnitSimp, finWod+"/lsc_map.tif")


#exporting source files
copyfile(dem,tempWod+"/Original_dem.tif")
copyfile(lu,tempWod+"/Original_land_cover.tif")

#TODO: create readme
f = open(finWod+"/lsc_mapREADME.txt", "w")
date = time.strftime("%x")+"  "+time.strftime("%X")
f.write("Landscape map created on the %s using script subtest.py\n" %date )
f.write("using the following files as input:\n DEM:\n %s\n\nLand cover: %s\n" %(dem, lu))
f.write("and this classification categories:\nASPECT:%s\n\nSLOPE: %s" %(asrul, slorul))
f.write("\n\n***!!!!Script finished correctly!!!!***")
f.close()


#### output file
#iface.addRasterLayer(lu, "asp")
#QgsMapLayerRegistry.instance().addMapLayer(simplu)
#iface.addRasterLayer(simpasp['OUTPUT'], "simp asp")
#iface.addRasterLayer(simpslope['OUTPUT'], "simp slope")
#iface.addRasterLayer(lscUnitSimp['OUTPUT'], "landscape unit")
#iface.addVectorLayer(lscVect['OUTPUT'], "lsc tvector", "ogr")

#to add exsting layer
#QgsMapLayerRegistry.instance().addMapLayer(LvectDiss)
#QgsMapLayerRegistry.instance().addMapLayer(layer)
