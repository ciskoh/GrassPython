import processing as p
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
#--------------DESCRIPTION------------------------------------
#Script to generalize Landscape units map
#using r.neighbor from GRASS 7

#---------------PARAMETERS----------------------------------
#Path to input layer
rawRast="/home/jkm2/GIS/DEM/slopeUTM.tif"

# R.NEIGHBOURS PARAMETER
#Method for generalisation
meth=0
#options: 0 -average, 2 -median,3 -mode, 4 -minimum, 5 -maximum,
# 5 -range, 7 -stddev, 8 -sum, 9 -count, 10 -variance, 11 -diversity,
# 12 -interspersion, 13 -quart1, 14 -quart3, 
# 15 -perc90, 16 -quantile

#window sizes
win=[3, 5, 7]# window sizes

#Minimum area of landscape unit in pixels
minarea= 9

#---------------CODE--------------------------------
print ("raw landscape is" + str(rawRast))

# neighborhood analysis at different window sizes

# detect bounding box of raster
layer=QgsRasterLayer(rawRast)
ext=layer.extent()
(xmin, xmax, ymin, ymax) = (ext.xMinimum(), ext.xMaximum(),\
ext.yMinimum(), ext.yMaximum())
coords = "%f,%f,%f,%f" %(xmin, xmax, ymin, ymax)

neigh=list()

for i in win:
    #calling command
    n=p.runalg("grass7:r.neighbors",\
    #input raster
    rawRast ,\
    #method
    meth,
    # WINDOW SIZE
    i,\
    # circular neighborhood
    True,\
    # do not Align
    False,\
    #weight 
    "",\
    #grass region
    coords,\
    # cellsize
    0,\
    #ouput path
    None)
    #add  to list of rasters
    polygonLayer = p.getObject(n['output'])
    neigh.append(polygonLayer)

print neigh
#patch rasters to obtain generalized map
a=p.runalg("grass7:r.patch",\
## list of rasters to patch together
list(reversed(neigh)),\
##Zero for transparency
False,\
##grass region
 coords,\
 #gras cellsize
 0,\
#output
None)

#sieve to remove small patches
b=p.runalg("gdalogr:sieve",\
#input file
a['output'],\
#minimum area
minarea,\
#connection: 0-->4 way; 1-->8 ways
0,\
None)

#set no data value
provider = layer.dataProvider()

provider.setNoDataValue(1, -2147483648) #first one is referred to band number 

#OUTPUT
iface.addRasterLayer(b['OUTPUT'], "simplified landscape unit map")

