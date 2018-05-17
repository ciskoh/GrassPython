#!/usr/bin/python
#Script to create landscape unit map using land use and land cover raster
#CONFIGURATION: FAO land cover map 
#-----------------------PARAMETERS------------------------------------------
#### ALTERNATIVE PATH TO INPUT FILES FOR TESTING
dem="/home/jkm2/GIS/DEM/complete_dem_Filled.tif"
lu="/home/jkm2/GIS/land cover/FAO/LandCoverFAO_30.tif"

#Output directory location & name
wod="/home/jkm2/GIS/Analysis/"
wodName="Lsc_Map_FAO"

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

#Method for generalisation
meth=3
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
from shutil import copyfile
import time
# 0 Preprocessing
# creating output directory

directory=wod+wodName+str(utmPix)
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
    newdem=p.runalg("gdalogr:warpreproject",ldem,ldem.crs().authid(),crefstr,"",utmPix,0,False,extdem,"",5,4,75,6,1,False,0,False,"",None)
    
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
        print "land use extension", extllu    
            
# making layer same extension


#extent as list
lluex=[llu.extent().xMinimum(),\
    llu.extent().xMaximum(),\
    llu.extent().yMinimum(),\
    llu.extent().yMaximum()]

demex=[ldem.extent().xMinimum(),\
    ldem.extent().xMaximum(),\
    ldem.extent().yMinimum(),\
    ldem.extent().yMaximum()]
    



newext=[max(lluex[0], demex[0]), min(lluex[1], demex[1]), max(lluex[2], demex[2]), min(lluex[3], demex[3])]

newextStr=str(newext[0])+","+str(newext[1])+","+str(newext[2])+","+str(newext[3])


# setting new extension to both rasters
llu=QgsRasterLayer(p.runalg("gdalogr:cliprasterbyextent",llu,"",newextStr,5,4,75,6,1,False,0,False,"",None)['OUTPUT'])
ldem=QgsRasterLayer(p.runalg("gdalogr:cliprasterbyextent",ldem,"",newextStr,5,4,75,6,1,False,0,False,"",None)['OUTPUT'])

#check resolution
lluex=[llu.extent().xMinimum(),\
    llu.extent().xMaximum(),\
    llu.extent().yMinimum(),\
    llu.extent().yMaximum()]

demex=[ldem.extent().xMinimum(),\
    ldem.extent().xMaximum(),\
    ldem.extent().yMinimum(),\
    ldem.extent().yMaximum()]
    
print "new extensions:", "lu", lluex, "dem", demex
#### 1 ASPECT from DEM

# calculate aspect
tempasp=p.runalg("gdalogr:aspect", ldem ,1,False,False,False,True,None)


###2 SLOPE
tempslo=p.runalg("gdalogr:slope",ldem,1,False,False,True,1,None)

# reclassify aspect and slope in classes based on asprul and slorule
aspclass=p.runalg("grass7:r.reclass", tempasp['OUTPUT']\
,"", asrul,extdem,0,None)
sloclass=p.runalg("grass7:r.reclass",tempslo['OUTPUT'],"",slorul,extdem,0,None)

## 3 classify areas under 5 degrees of slope as flat: 0 aspect and 0 slope
newasp=p.runalg("gdalogr:rastercalculator",tempslo['OUTPUT'],"1",aspclass['output'],"1",None,"1",None,"1",None,"1",None,"1","0*(A<=5)+B*(A>5)","",5,"",None)
newslo=p.runalg("gdalogr:rastercalculator",tempslo['OUTPUT'],"1",sloclass['output'],"1",None,"1",None,"1",None,"1",None,"1","0*(A<=5)+B*(A>5)","",5,"",None)


#### 4 simplification
print "resolution of rasters", utmPix
print "minimum area in sq. meters", minar
minpix= int(round(sqrt(minar)/utmPix))

# ratio resolution to minimum area

if minpix%2 == 0:
    minpix=minpix+1

print "newminpix", minpix
print "size of area in pixels", minpix**2

## 5. function to simplify rasters 

sizelist=[minpix, minpix+2, minpix+4]
minHec=minar/10000
# simplify function needs a string path to "rawrast" files
def simp(rawrast):
            
    rawLay=QgsRasterLayer(rawrast)
    # get extension of raster
    coords="%f,%f,%f,%f" %(rawLay.extent().xMinimum(),\
        rawLay.extent().xMaximum(),\
        rawLay.extent().yMinimum(),\
        rawLay.extent().yMaximum())
        
    # remove small areas    
    rawRast2=p.runalg("grass7:r.reclass.area.greater",rawrast,0,minHec,coords,0,None)['output']
            
        
    neigh=list()
    neigh.append(rawRast2)
        
    s2=sizelist
    s2.reverse()
    for i in s2:
        #calling command
        n=p.runalg("grass7:r.neighbors", rawrast, meth, i, True, False, "", coords, 0, None)
        #add to list of rasters
        # na=QgsRasterLayer(n['output'])
        neigh.append(n['output'])
        
    

    #patch rasters to obtain generalized map
    a=p.runalg("grass7:r.patch",neigh,False,coords,0,None)['output']
        
    return a


##call function to aspect
#simpasp=simp(newasp)['OUTPUT']
simpasp=newasp['OUTPUT']
print "aspect is simplified"

##call function to slope
#simpslope=simp(newslo)['OUTPUT']
simpslope=newslo['OUTPUT']
print "slope is simplified"

##call function to land cover
#simplu=simp(llu.source())['OUTPUT']
simplu=llu.source()
print "land use is simplified"
print(simplu)

#### 6 putting together the rasters
lsc_unit=p.runalg("gdalogr:rastercalculator",simplu,"1",simpasp,"1",simpslope,"1",None,"1",None,"1",None,"1","(A*100)+(B*10)+C","",5,"",os.path.join(directory,"test.tif"))

print "raw landscape units raster is"
print lsc_unit
iface.addRasterLayer(lsc_unit['OUTPUT'], "simplified landscape unit")

if QgsRasterLayer(lsc_unit['OUTPUT']).isValid():
# simplify landscape unit map
    lsc_unit_simp=simp(lsc_unit['OUTPUT'])
    print "landscape unit map produced"




### 7 translating raster to vector

lsc_vect=p.runalg("gdalogr:polygonize",lsc_unit_simp,"code",None)

#add attributes "land use", "slope", "aspect", "area"
vect = QgsVectorLayer(lsc_vect['OUTPUT'], "lsc vector", "ogr")

#dissolve polygons by code
vect_diss=p.runalg("gdalogr:dissolvepolygons",vect,"geometry","code",True,False,False,False,False,None,"",None)
Lvect_diss=QgsVectorLayer(vect_diss['OUTPUT_LAYER'], "dissolved", "ogr")
#Add Attributes:
res = Lvect_diss.dataProvider().addAttributes([\
    QgsField("landCover", QVariant.String ),\
    QgsField("aspect", QVariant.String),\
    QgsField("slope", QVariant.String),\
    ])
Lvect_diss.updateFields()

layer=Lvect_diss
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
copyfile(lsc_unit_simp, dirFin+"/lsc_map.tif")


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
#iface.addRasterLayer(lsc_unit_simp['OUTPUT'], "landscape unit")
#iface.addVectorLayer(lsc_vect['OUTPUT'], "lsc tvector", "ogr")

#to add exsting layer
#QgsMapLayerRegistry.instance().addMapLayer(Lvect_diss)
QgsMapLayerRegistry.instance().addMapLayer(layer)