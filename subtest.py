#!/usr/bin/python
#Script to create landscape unit map using land use and land cover raster
#CONFIGURATION: FAO land cover map 
#-----------------------PARAMETERS------------------------------------------
#### Linux Server PATH TO INPUT FILES FOR TESTING
dem="/home/jkm2/GIS/DEM/complete_dem_Filled.tif"
lu="/home/jkm2/GIS/land cover/FAO/LandCoverFAO_30.tif"

#### Linux local
# DEM dem="/home/matt/Dropbox/ongoing/BFH-Pastures/gis data/DEM/complete_dem_Filled.tif"
# LAND COVER lu="/home/matt/Dropbox/ongoing/BFH-Pastures/gis data/land cover/FAO/LandCoverFAO_30.tif"

#### Output directory location & name
# linux server 
wod="/home/jkm2/GIS/Analysis"
# linux local wod="/home/matt/Dropbox/ongoing/BFH-Pastures/gis data/Analysis"
wodName="Lsc_Map_FAO2"

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
minar=20000

### Pixel resolution in meters
utmPix=30

#---------------------------------------------------------------------------

from PyQt4.QtGui import *
from PyQt4.QtCore import *
import sys
import processing as p
import os
from math import sqrt
from shutil import copyfile
import time

#----------------------------------------FUNCTIONS
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
# simplify function needs a string path to "rawrast" files
## 5. function to simplify rasters 

# 0.2 Import files
# input: path to file
# output: QgsRasterLayer

def fileImport(path):
    fileName = path
    fileInfo = QFileInfo(fileName)
    baseName = fileInfo.baseName()
    lay = QgsRasterLayer(fileName, baseName)
    if not lay.isValid():
	print "Layer failed to load!"
    else:
        return lay

# 1.1 Get layer extension as string
# input: lay - layer, form (boolean)- 0 for string 1 for list
# output: string/List of coordinates in layer CRS
def getCoord(lay, form):
    if form == 0:
    	extLay=lay.extent().toString().replace(" : ",",")
    else:
        extLay=[lay.extent().xMinimum(),\
            lay.extent().xMaximum(),\
            lay.extent().yMinimum(),\
            lay.extent().yMaximum()]
    return extLay

# 1.2 reprojecting layers to UTM 
# input: lay - layer to reproject, ref - UTM reference code ("EPSG"), utmPix - pixel resolution in meters
# output: reprojected layer

def reproj(lay, ref, utmPix):
    refStr="EPSG:"+str(ref)
    #extension of layer
    extLay=getCoord(lay, 0)
    
    if lay.crs() != QgsCoordinateReferenceSystem(ref):
        newRast=p.runalg("gdalogr:warpreproject",lay,lay.crs().authid(),refStr,"",utmPix,0,False,extLay,"",5,4,75,6,1,False,0,False,"",None)
        newLay=QgsRasterLayer(newRast['OUTPUT'])
    else:
        print "layer already in CRS %s" %(refStr)
        newLay=lay 
    
    if not newLay.isValid():
        print "layer transformation not valid"
    else:
        return newLay



# simplify raster based on minimum area
# input: lay - raster layer, minar - size of min. homogeneous area
# implicit input: dirPart - folder for working files
# output: simplified layer


def simp(lay, minar):
    res=lay.rasterUnitsPerPixelX()
    
    minPix= int(round(sqrt(minar)/res))
    if minPix%2 == 0:
        minPix=minPix+1
    
    minHec=minar/10000
    
    
    # get extension of raster
    coords=getCoord(lay, 0)
    
    # get layer with areas above minimum threshold
    pathLayBig=os.path.join(dirPart, "layBig.tif")
    layBig=p.runalg("grass7:r.reclass.area.greater",lay,0,minHec,coords,0,pathLayBig)
    # create multiple rasters at different size
    sizeList=[minPix*2+1, minPix*4+1, minPix*8+1]
    sizeList.reverse()
    neigh=list()
    neigh.append(layBig)
        
    for i in sizeList:
    	pathToFile=os.path.join(dirPart, "simple_"+str(i)+".tif")
        #calling command
        simple=p.runalg("grass7:r.neighbors", layBig, 3, i, True, False, "", coords, 0, pathToFile)
        #add to list of rasters
        neigh.append(pathToFile)
    print "list of files to be patched is :"
    print neigh
    #patch rasters to obtain generalized map
    path2=os.path.join(dirPart, "simplePatched.tif")
    simpPatch=p.runalg("grass7:r.patch",neigh,False,coords,0,path2)
    print simpPatch 
    return QgsRasterLayer(simpPatch)

####-------------------CODE----------------------------

### A-  Importing and preprocessing

directory=wod+"/"+wodName+str(utmPix)
dirPart=directory+"/workingFiles"
dirFin=directory+"/finalOutput"
if not os.path.exists(directory):
    os.makedirs(directory)
    os.makedirs(dirPart)
    os.makedirs(dirFin)

print "working directory path:"
print directory
print dirPart
print dirFin

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
# New extent as list
lluex=getCoord(newLu, 1)
demex=getCoord(newDem, 1)
newext=[max(lluex[0], demex[0]), min(lluex[1], demex[1]), max(lluex[2], demex[2]), min(lluex[3], demex[3])]
newextStr=str(newext[0])+","+str(newext[1])+","+str(newext[2])+","+str(newext[3])

# setting new extension to both rasters
newLu2=QgsRasterLayer(p.runalg("gdalogr:cliprasterbyextent",newLu,"",newextStr,5,4,75,6,1,False,0,False,"",None)['OUTPUT'])
newDem2=QgsRasterLayer(p.runalg("gdalogr:cliprasterbyextent",newDem,"",newextStr,5,4,75,6,1,False,0,False,"",None)['OUTPUT'])
if newLu2.isValid() and newDem2.isValid():
    print "new extensions:", "land cover", newLu2.extent().toString(), "dem", newDem2.extent().toString()
else:
    print "problem correcting raster extension"

#### B- ASPECT and slope from DEM

# calculate aspect
asp=p.runalg("gdalogr:aspect", newDem2,1,False,False,False,True,None)
tempAsp=asp['OUTPUT']
###2 SLOPE
slo=p.runalg("gdalogr:slope",newDem2,1,False,False,True,1,None)
tempSlo=slo['OUTPUT']
# reclassify aspect and slope in classes based on asprul and slorule
extdem=getCoord(newDem2,0)
aspClass=p.runalg("grass7:r.reclass", tempAsp,"",asrul,extdem,0,None)
sloClass=p.runalg("grass7:r.reclass",tempSlo,"",slorul,extdem,0,None)

#### C - Combining all layers and simplifying

#call function to aspect

simpAsp=simp(QgsRasterLayer(aspClass['output']), minar)
if simpAsp.isValid():
    print "aspect is simplified"
else:
    print "problem with aspect simplification"
#call function to slope
simpSlope=simp(QgsRasterLayer(sloClass['output']), minar)
if simpSlope.isValid():
    print "slope is simplified"
else:
    print "problem with slope simplification"

#call function to land cover
#simplu=simp(llu.source())['OUTPUT']
simpLu=simp(llu, minar)
if simpLu.isValid():
    print "land use is simplified"
else:
    print "problem with land use simplification"

#putting together the rasters
lscUnit=p.runalg("gdalogr:rastercalculator",simplu,"1",simpasp,"1",simpslope,"1",None,"1",None,"1",None,"1","(A*100)+(B*10)+C","",5,"",os.path.join(dirPart,"lscUnit.tif"))
if QgsRasterLayer(lscUnit['OUTPUT']).isValid():
    print "raw landscape units raster is %f" %(lscUnit.source())
    print lscUnit
    iface.addRasterLayer(lscUnit['OUTPUT'], "simplified landscape unit")


# simplify landscape unit map
    lscUnitSimp=simp(lscUnit['OUTPUT'])
    print "landscape unit map produced"

### D translating raster to vector

lscVect=p.runalg("gdalogr:polygonize",lscUnitSimp,"code",None)

#add attributes "land use", "slope", "aspect", "area"
vect = QgsVectorLayer(lscVect['OUTPUT'], "lsc vector", "ogr")

#dissolve polygons by code
vectDiss=p.runalg("gdalogr:dissolvepolygons",vect,"geometry","code",True,False,False,False,False,None,"",None)
LvectDiss=QgsVectorLayer(vectDiss['OUTPUT_LAYER'], "dissolved", "ogr")
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
QgsVectorFileWriter.writeAsVectorFormat(layer, dirFin+'/lsc_map.shp', "", None, "ESRI Shapefile")

# exporting raster map
copyfile(lscUnitSimp, dirFin+"/lsc_map.tif")


#exporting source files
copyfile(dem,dirPart+"/Original_dem.tif")
copyfile(lu,dirPart+"/Original_land_cover.tif")

#TODO: create readme
f = open(dirFin+"/lsc_mapREADME.txt", "w")
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
QgsMapLayerRegistry.instance().addMapLayer(layer)
