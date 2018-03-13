#!/usr/bin/python
#Script to create landscape unit map using land use and land cover raster

#-----------------------PARAMETERS------------------------------------------
#### ALTERNATIVE PATH TO INPUT FILES FOR TESTING
dem="/home/matt/Dropbox/ongoing/BFH-Pastures/gis data/DEM/complete_dem_Filled.tif"
lu="/home/matt/Dropbox/ongoing/BFH-Pastures/gis data/land cover/LandCover_updated/Land_cover_updated.tif"

#Output directory
wod="/home/matt/Dropbox/ongoing/BFH-Pastures/gis data/Analysis/"

#crs of utm zone
ref=32630

#### ASPECT PARAMETERS
asrul="0 thru 45 = 1 north\n315 thru 360 = 1 north\n45 thru 135 = 2 east\n135 thru 225 = 3 south\n225 thru 315 = 4 west\n\n"

#### SLOPE PARAMETERS
slorul="0 thru 10 = 1 flat\n10 thru 15 = 2 sloping\n15 thru 30 = 3 steep\n30 thru 100 = 4 very steep"

### Minimum area size of landscape units in sq m
minar=20000

### Pixel resolution in meters
utmPix=30

#Method for generalisation
meth=2
#options: 0 -average, 2 -median,3 -mode, 4 -minimum, 5 -maximum,
# 5 -range, 7 -stddev, 8 -sum, 9 -count, 10 -variance, 11 -diversity,
# 12 -interspersion, 13 -quart1, 14 -quart3, 
# 15 -perc90, 16 -quantile

#---------------------------------------------------------------------------

from PyQt4.QtGui import *
from PyQt4.QtCore import *
import sys
import processing as p
import os
from math import sqrt
# 0 Preprocessing
# creating output directory
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

# 0.2 TODO: Allignment and resolution check
#Resolution check
llures=llu.rasterUnitsPerPixelX()
demres=ldem.rasterUnitsPerPixelX()

bigres=max(llures,demres)
print "llures", llures
print "demres", demres



#creating object for refrence crs system
#to get EPSG id crs.postgisSrid()

cref=QgsCoordinateReferenceSystem(ref)
#string for epsg

### reprojecting DEM
crefstr="EPSG:"+str(ref)
#extension of layer
extdem="%f,%f,%f,%f" %(ldem.extent().xMinimum(),\
    ldem.extent().xMaximum(),\
    ldem.extent().yMinimum(),\
    ldem.extent().yMaximum())
    
if ldem.crs() != QgsCoordinateReferenceSystem(ref):
    newdem=p.runalg("gdalogr:warpreproject",dem,"",crefstr,"",utmPix,0,False,extdem,"",5,4,75,6,1,False,0,False,"",None)
    
    if not QgsRasterLayer(newdem['OUTPUT']).isValid():
        print "DEM layer transformation not valid"
    else:
        ldem= QgsRasterLayer(newdem['OUTPUT'])
        extdem="%f,%f,%f,%f" %(ldem.extent().xMinimum(),\
            ldem.extent().xMaximum(),\
            ldem.extent().yMinimum(),\
            ldem.extent().yMaximum())

### reprojecting LUS
crefstr="EPSG:"+str(ref)
#extension of layer
extllu="%f,%f,%f,%f" %(llu.extent().xMinimum(),\
    llu.extent().xMaximum(),\
    llu.extent().yMinimum(),\
    llu.extent().yMaximum())
    
if llu.crs() != QgsCoordinateReferenceSystem(ref):
    newlu=p.runalg("gdalogr:warpreproject",lu,"",crefstr,"",utmPix,0,False,extllu,"",5,4,75,6,1,False,0,False,"",None)
    
    if not QgsRasterLayer(newlu['OUTPUT']).isValid():
        print "land cover layer transformation not valid"
    else:
        llu= QgsRasterLayer(newlu['OUTPUT'])
        extllu="%f,%f,%f,%f" %(llu.extent().xMinimum(),\
            llu.extent().xMaximum(),\
            llu.extent().yMinimum(),\
            llu.extent().yMaximum())
    
#### 1 ASPECT from DEM

# calculate aspect
tempasp=p.runalg("gdalogr:aspect", ldem ,1,False,False,False,True,None)


###2 SLOPE
tempslo=p.runalg("gdalogr:slope",ldem,1,False,False,True,1,None)

# reclassify aspect and slopein classes based on asprul and slorule
aspclass=p.runalg("grass7:r.reclass", tempasp['OUTPUT']\
,"", asrul,extdem,0,None)
sloclass=p.runalg("grass7:r.reclass",tempslo['OUTPUT'],"",slorul,extdem,0,None)

## 3 classify areas under 5 degrees of slope as flat: 0 aspect and 0 slope
newasp=p.runalg("gdalogr:rastercalculator",tempslo['OUTPUT'],"1",aspclass['output'],"1",None,"1",None,"1",None,"1",None,"1","0*(A<=5)+B*(A>5)","",5,"",None)
ewslo=p.runalg("gdalogr:rastercalculator",tempslo['OUTPUT'],"1",sloclass['output'],"1",None,"1",None,"1",None,"1",None,"1","0*(A<=5)+B*(A>5)","",5,"",None)

#### 4 simplification
print "resolution of rasters", utmPix
print "minimum area in sq. meters", minar
minpix= int(round(sqrt(minar)/utmPix))

# ratio resolution to minimum area

if minpix%2 == 0:
    minpix=minpix+1

print "newminpix", minpix
print "size of area in pixels", minpix**2
##function to simplify raster 
#########################################################TODO: function not working
sizelist=[minpix, minpix+2, minpix+4]

def simp(rawRast):
        rawRast=QgsRasterLayer(rawRast['OUTPUT'])
        # get extension of raster
        neigh=list()
        coords="%f,%f,%f,%f" %(rawRast.extent().xMinimum(),\
            rawRast.extent().xMaximum(),\
            rawRast.extent().yMinimum(),\
            rawRast.extent().yMaximum())
    
        for i in sizelist:
            #calling command
            n=p.runalg("grass7:r.neighbors", rawRast, meth, i, True, False, "", coords, 0, None)
            #add  to list of rasters
            # na=QgsRasterLayer(n['output'])
            neigh.append(QgsRasterLayer(n['output']))

        print neigh

       #patch rasters to obtain generalized map
        a=p.runalg("grass7:r.patch",list(reversed(neigh)),False,coords,0,None)
#
#        #sieve to remove small patches
#        b=p.runalg("gdalogr:sieve",\
#        #input file
#        a['output'],\
#        #minimum area in pixels
#        minpix**2,\
#        #connection: 0-->4 way; 1-->8 ways
#        0,\
#        None)
#
#        return b
##call function to aspect
testaspect=simp(newasp)
##call function to alope
##
##call function to land cover

# output file
iface.addRasterLayer(newasp['OUTPUT'], "asp")
iface.addRasterLayer(testaspect['OUTPUT'], "simp asp")
