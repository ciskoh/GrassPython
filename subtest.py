#!/usr/bin/python
#Script to create landscape unit map using land use and land cover raster

#-----------------------PARAMETERS------------------------------------------
#### ALTERNATIVE PATH TO INPUT FILES FOR TESTING
dem="/home/jkm2/GIS/DEM/complete_dem_Filled.tif"
lu="/home/jkm2/GIS/land cover/LandCover_updated/Land_cover_updated.tif"

#Output directory
wod="/home/jkm2/GIS/Analysis/"

#crs of utm zone
ref=32630

#### ASPECT PARAMETERS
asrul="0 thru 45 = 1 north\n315 thru 360 = 1 north\n45 thru 135 = 2 east\n135 thru 225 = 3 south\n225 thru 315 = 4 west\n\n"

#### SLOPE PARAMETERS
slorul="0 thru 10 = 1 flat\n10 thru 15 = 2 sloping\n15 thru 30 = 3 steep\n30 thru 100 = 4 very steep"

#---------------------------------------------------------------------------

from PyQt4.QtGui import *
from PyQt4.QtCore import *
import sys
import processing as p
import os

# 0 Preprocessing
# cretaing output directory
directory=wod+"/lscMap-script"
dirPart=directory+"/workingFiles"
dirFin=directory+"/finalOutput"
if not os.path.exists(directory):
    os.makedirs(directory)
    os.makedirs(dirPart)
    os.makedirs(dirFin)

# 0.1 Importing files

####  TODO: remove "#" from the lines before 
## invoking screen to select dtm and land use raster
#qfd = QFileDialog()
#title = ' **** SELECT LAND USE *****'
#path = "/home/jkm2/GIS/Analysis"
#lu = QFileDialog.getOpenFileName(qfd, title, path)
#
#title = ' **** SELECT DTM *****'
#dem = QFileDialog.getOpenFileName(qfd, title, path)


# import dem as layer ldem
fileName = dem
fileInfo = QFileInfo(fileName)
baseName = fileInfo.baseName()
ldem = QgsRasterLayer(fileName, baseName)
if not ldem.isValid():
  print "Layer failed to load!"

# import land cover as layer llu
fileName = lu
fileInfo = QFileInfo(fileName)
baseName = fileInfo.baseName()
llu = QgsRasterLayer(fileName, baseName)
if not llu.isValid():
  print "Layer failed to load!"

# 0.2 Allignment and resolution check
#### TODO: check alignment of rasters and resolution to ensure they are the same 

#creating object for refrence crs system
#to get EPSG id crs.postgisSrid()

cref=QgsCoordinateReferenceSystem(ref)
#string for epsg

### reprojecting DEM
crefstr="EPSG:"+str(ref)
#extension of layer
extstr="%f,%f,%f,%f" %(ldem.extent().xMinimum(),\
    ldem.extent().xMaximum(),\
    ldem.extent().yMinimum(),\
    ldem.extent().yMaximum())
    
if ldem.crs() != QgsCoordinateReferenceSystem(ref):
    newdem=p.runalg("gdalogr:warpreproject",dem,"",crefstr,"",0,0,False,extstr,"",5,4,75,6,1,False,0,False,"",None)
    
    if not QgsRasterLayer(newdem['OUTPUT']).isValid():
        print "DEM layer transformation not valid"
    else:
        ldem= QgsRasterLayer(newdem['OUTPUT'])
        

### reprojecting LUS
crefstr="EPSG:"+str(ref)
#extension of layer
extstr="%f,%f,%f,%f" %(llu.extent().xMinimum(),\
    llu.extent().xMaximum(),\
    llu.extent().yMinimum(),\
    llu.extent().yMaximum())
    
if llu.crs() != QgsCoordinateReferenceSystem(ref):
    newlu=p.runalg("gdalogr:warpreproject",lu,"",crefstr,"",0,0,False,extstr,"",5,4,75,6,1,False,0,False,"",None)
    
    if not QgsRasterLayer(newlu['OUTPUT']).isValid():
        print "land cover layer transformation not valid"
    else:
        llu= QgsRasterLayer(newlu['OUTPUT'])
    
#### 1 ASPECT from DEM

# calculate aspect
tempasp=p.runalg("gdalogr:aspect", ldem ,1,False,False,False,True,None)
# reclassify aspect in classes based on asprul
aspclass=p.runalg("grass7:r.reclass", tempasp['OUTPUT']\
,"", asrul,"-5.29951733222,-4.64824575667,32.3035089114,32.8301755786",0,None)

##TODO: get area of DEM to remove coordinates from reclass command

###2 SLOPE
tempslo=p.runalg("gdalogr:slope",ldem,1,False,False,True,1,None)
sloclass=p.runalg("grass7:r.reclass",tempslo['OUTPUT'],"",slorul,"-5.29951733222,-4.64824575667,32.3035089114,32.8301755786",0,"/home/jkm2/.qgis2//processing/outputs/slope reclass reference")







# output file
#iface.addRasterLayer(tempslo['OUTPUT'], "Output of script")
iface.addRasterLayer(newdem['OUTPUT'], "Output of script")
