import processing as p
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
#--------------DESCRIPTION------------------------------------
#Script to generalize Landscape units map
#using r.neighbor from GRASS 7

#---------------PARAMETERS----------------------------------
#Path to raw landscape layer
rawRast="C:\Users\jkm2\Dropbox\ongoing\BFH-Pastures\gis data\Analysis\landscape map\Landscape_raw.tif"
#window sizes
win=[3, 5, 7]# window sizes
#---------------CODE--------------------------------
print ("raw landscape is" + str(rawRast))

# neighborhood analysis at different window sizes
neigh=list()

for i in win:
    #calling command
    n=p.runalg("grass7:r.neighbors",\
    #input raster
    rawRast ,\
    #method
    2,
    # WINDOW SIZE
    i,\
    # circular neighborhood
    True,\
    # do not Align
    False,\
    #weight 
    "",\
    #grass region
    "-5.35092942972,-4.58733748111,32.2911493106,32.841026215",\
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
 "-5.35092942972,-4.58733748111,32.2911493106,32.841026215",\
 #gras cellsize
 0,\
#output
None)

#sieve to remove small patches
b=runalg("gdalogr:sieve",\
#input file
a['output'],\
#minimum area
9,\
#connection: 0-->4 way; 1-->8 ways
0,\
None)
iface.addRasterLayer(b['OUTPUT'], "simplified landscape unit map")

