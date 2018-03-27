# -*- coding: utf-8 -*-
"""
Created on Mon Mar 26 17:22:04 2018

@author: matt
"""

#!/usr/bin/env python
#----------------------------DESCRIPTION
#Script to preprocess sentinel images and obtain ONLY NDVI values

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
#remote 
dem="/home/jkm2/GIS/DEM/ASTER_big/asterDemUTM/asterDemUTM_comp.tif"
#local dem="/home/matt/Dropbox/ongoing/BFH-Pastures/gis data/DEM/ASTER_big/asterDemUTM/asterDemUTM_comp.tif"

# output directory
#local dir outd="/home/matt/Dropbox/ongoing/BFH-Pastures/gis data/Sentinel_preprocess/test/output"
#remote dir 
outd="/home/jkm2/GIS/Sentinel_preprocess/test/output"
# working folder for temporary folders
temp1="/tmp"
#-------------------------------FUNCTIONS---------------------------------

#### 1 TRIGGER 

#1.1 function to search for images recursively
# Inputs:input iDir-folder empty list for root of images, tiles-code of tiles for area of interest)
# Output: double list with name and path of images in iDir

def srcImg(iDir, tiles):
    multifolds1=(iDir +"/"+ tile for tile in tiles)
    bnlist=[]
    rlist=[]
    #search for tiff files in folder
    for i in folds:
        for r,d,files in os.walk(i):
            for f in files:
                if f.endswith(".tif"):
                    bnlist.append(f)
                    rlist.append(os.path.join(r,f))
    finlist=[bnlist, rlist]
    print "output of function 1.1 srcImg:\n\n %s"
    for i in finlist[0:50]:
        print i
    return finlist

#1.2 function to compare two lists and decide if the script continues
#input two double (full path and basename) image lists, unprocessed and processed: 
#Orlist- Non processed, Outlist - Processed images
#Output: either a quit signal or a list of image to be processed

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

#2 IMAGE METADATA AND LAYER
# input: ipat-path to unprocessed image
# output: Dictionary with the following data: 
#{ key : value  : type }

#  baseName : basename without extension : STRING
#  orImg : Qgs layer of Image : LAYER
#  extImg : Image extension : STRING
#  imgCrs : reference system : CRSOBJECT
#  
def imgMd(ipat):
    
    baseName = os.path.basename(ipat)[0:-4]
    orImg = QgsRasterLayer(ipat, baseName)
    if not orImg.isValid():
        print "\nLayer failed to load!\n\n -->quitting script on image %s" % baseName
        quit()
    # image extension as string
    extImg="%f,%f,%f,%f" %(orImg.extent().xMinimum(),\
        orImg.extent().xMaximum(),\
        orImg.extent().yMinimum(),\
        orImg.extent().yMaximum())
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

# 2.1 create working directory
# input: baseName (STRING) : name of image to be processed
#        temp1 (STRING) : path to main working directory

# output : path to this image working directory (STRING)

def makeWod(baseName, temp1):
    directory=temp1+"/"+baseName
    if not os.path.exists(directory):
        os.makedirs(directory)
        print "output of function 2.1 makeWod, %s" %directory
    return directory
    
#3 DEM RESOLUTION CHECK AND TRANSFORM
#input: dem (STRING) - path to DEM, 
#      imgCrs (CRSOBJECT) - Reference system of Image to be corrected, 
#      wod (STRING) - path to working directory
    
#output: dem - path to new reprojected layer 
def demCheck(dem, ImgCrs, wod ):
    demCrs=QgsRasterLayer(dem).crs()
    print "\nImage CRS :%s\n dem crs:%s" %(imgCrs.description(), demCrs.description())

    if demCrs != imgCrs:
        print "\nreprojecting DEM to %s" %(imgCrs.description())
        ldem=QgsRasterLayer(dem)
        extdem="%f,%f,%f,%f" %(ldem.extent().xMinimum(),\
                ldem.extent().xMaximum(),\
                ldem.extent().yMinimum(),\
                ldem.extent().yMaximum())
        crsStr=imgCrs.authid()
        newdem=p.runalg("gdalogr:warpreproject",ldem,"",crsStr,"",30,0,False,extdem,"",5,4,75,6,1,False,0,False,"",None)
        LnDem=QgsRasterLayer(newdem['OUTPUT'])
        if LnDem.isValid():
            print "dem reprojected correctly"
            dem=newdem['OUTPUT']
            print "output of function 3 demCheck:\n\n %s" %dem
    else:
        print "\nall files are in the same CRS!"    
    return dem
    
#4 BAND SEPARATION
# inputs: ipat (STRING) - path to multiband image to be processed, 
#         bNum (INTEGER) - number of band to be extracted
#         wod (STRING) - working directory to save geoTiff files    
         
# output: path to single-band geotiff
    
def bndSep(ipat, bNum, wod):
    sBand={}
    #band name and path
    bname="band"+str(bNum)
    directory=wod
    path=directory+"/"+bname+".tif"
    # call to gdal translate with option
    gdal.Translate(path, ipat, bandList=[i])
    if not QgsRasterLayer(path).isValid():
        print "problem saving single band %s!\n\n -->quitting script on image %s, function bndSep" %(i,baseName)          
        quit()
    print " output of function 4 bndSep:\n\n %s" %path
    return path

#TODO 5.0 Altitude average uaing dem (as separate function)
#    demStats=p.runalg("grass7:r.univar",dem,None,"","",False,extImg,None)
#    statFile=open(demStats['output'], "r")
#    line=statFile.read().splitlines()[1]

#### 5 PARAMETERS FOR S6 ATHMOSPHERIC CORRECTION
# input: baseName (STRING) - name of image to be processed
#        bNum (INTEGER) - number of band to be used
#        wod (STRING) - working directory to save geoTiff files    
# output: (STRING) path to parameter file
def makePar(baseName, bNum, wod):
    
    # preparation parameters for 6S 
    #path to parameter file
    band="band"+str(bNum)
    Spath=str(wod+band+"_.atcorParam.txt")
    #Writing paramater file    
    Sfile=open(Spath, "w")
    
    #FIRST LINE : satellite type
    firstLine="25\n"
    Sfile.write(firstLine)
    #SECOND LINE
    #read end of basename for date and time
    dateS=baseName.split("_")[2]

    month=dateS[4:6]
    day=dateS[6:8]

    hours=dateS[9:11]
    minutes=dateS[11:13]
    # hours and day in decimal time
    dmin=round(100*float(minutes)/60,0)
    dtime=str(hours)+"."+str(dmin/100)[2:]

    #long lat (centre point) in WGS84
    long=orImg.extent().xMinimum()+((orImg.extent().xMaximum()-orImg.extent().xMinimum())/2)
    lat=orImg.extent().yMinimum()+((orImg.extent().yMaximum()-orImg.extent().yMinimum())/2)
    # transform long and lat in WGS 84
    crsDest=QgsCoordinateReferenceSystem(4326)
    xform = QgsCoordinateTransform(orImg.crs(), crsDest)
    ncoord=xform.transform(QgsPoint(long,lat))
    
    #print secondline
    secondLine=str(month)+" "+str(day)+" "+str(dtime)+" "+str(ncoord.x())+" "+str(ncoord.y())+"\n"
    Sfile.write(secondLine)
        
    #THIRD LINE of parameter file athmospheric model (1) continental
    if month < 3 or month > 10:
        atmMod=3
    else:
        atmMod=2
    thirdLine="%s \n" %atmMod
    #print third line
    Sfile.write(thirdLine)
    
    #FOURTH LINE: 1 continental model
    fourthLine="1\n"
    Sfile.write(fourthLine)
    
    #FIFTH LINE: Aerosol concentration model (visibility)
    fifthLine="-1\n"
    Sfile.write(fifthLine)
    
    #SIXTH LINE: Aerosol concentration model (visibility)
    sixthLine="0\n"
    Sfile.write(sixthLine)

    #SEVENTH LINE (average altitude in negative km)
#    missing: actual calculation of average altitude avgAlt
    avgAlt=1400
    avgDem=-1*float(avgAlt)/1000
    seventhLine=str(avgDem)+"\n"
    Sfile.write(seventhLine)
    # EIGHTH LINE: sensor altitude
    eighthLine="-1000\n"
    Sfile.write(eighthLine)
    
    # F : sensor band code
    bcodes=range(166, 179)
    ninthLine=str(bcodes[bNum-1])+"\n"
    Sfile.write(ninthLine)
    
    #output
    Sfile.close() 
    print "output of function 5 makePar is:\n\n"
    print "1st line of 6S parameter file (SATELLITE TYPE) is %s\n" %firstLine
    print "2nd line of 6S parameter file is (month, day, hh.ddd, long, lat):\n %s" %secondLine
    print "3rd line of 6S parameter file is  (Athmospheric model):\n %s" %thirdLine
    print "4th line of 6S parameter file is (Aereosol model):\n %s" %fourthLine
    print "5th and 6th line of 6S parameter file is (Visibility model):\n %s and %s" %(fifthLine, sixthLine)
    print "7th and 8th lines of 6S parameter file (target and sensor altitude are:\n %s %s " %(seventhLine, eighthLine)
    print "9th line of 6S parameter file (band code) is %s " %(ninthLine)
    return Spath

#5.1 RANGE OF PIXEL VALUES: minimum and maximum pixel value
# input: singImg (STRING) - path to single band image
#        wod (STRING) - path to working directory

# output: STRING range of pixel values per band
def pixRange(singImg, wod):    
    #range of values
    ds = gdal.Open(dem)
    myarray = np.array(ds.GetRasterBand(1).ReadAsArray())
    pMin=np.nanmax(myarray)
    pMax=np.nanmin(myarray)
    pRange=str(pMin)+","+str(pMax)
    print "output of function 5.1 pixRange is:"
    print 'pixel range is %s' %(pRange)
    return pRange

#6 Athmospheric correction
#input: singImg (STRING) - path to single band image
#       baseName (STRING) - name of image being processed
#       par (STRING) - path to parameter file
#       pRange (STRING) - range of pixel values
#       bNum (INTEGER) - band number
#       extImg (STRING) - Image extension 
#       wod (STRING) - path to working directory

#output: (STRING) path to single band corrected image       
def atCorr(singImg, baseName, par, pRange, bNum, extImg, wod):
    # double check of input files
    if not QgsRasterLayer(singImg).isValid():
        print "problem with input image before atmospheric correction!\n\n -->quitting script on image %s" % baseName
        quit()
    print "launching athmospheric correction on image "+baseName[-10:]
    #path to corrected image
    bname="band"+str(bNum)
    corPath=wod+"corr"+bname+".tif"
    corrImg=p.runalg("grass7:i.atcorr",singImg,pRange,None, None,par,pRange,False,True,False,False,extImg,0,corPath)
    if not QgsRasterLayer(corPath).isValid():
        print "problem correcting the image!\n\n -->quitting script on image %s" % baseName
        quit()
    if corrImg['output'] != corPath:
        print "problem with corrected image location"
    else:  
        print "output of function 6 atCorr is: \n\n"
        print corPath
    return corPath
    
#TODO: vector mask

#7 NDVI calculation
#input: Red (STRING) - path to Red band
#       Nir (STRING) - path to NIR band
#       wod (STRING) - path to working directory
#output: path to NDVI image
def ndCalc(Red, Nir, wod):
    fStr=Nir+Red/Nir-Red
    #gdal calc
    

#TODO output
#TODO main function

#100.1 Stop and go function based on user input
#input lNum (INTEGER) - Line number 
#      baseName (STRING) - name of image being processed
#output: either quit signal or nothing

def stopGo(lNum, basename):
    cont=raw_input("script at line %s, \n CONTINUE? Y/n?" %lNum)
    if cont == "n":
        print "stop signal received from user for image %s at line %s" %(baseName, lNum)
        print "\n\n -->quitting script on user input"
        quit()
    
        
# 100 MAIN FUNCTION to perfom athmospheric correction and NDVI calculation using all functions above
#input : ipat (STRING) - path to image to be processed
#        bnum ( LIST of integers) - band numbers to be processed
#        outd (STRING) - path to output folder

#output : string to final image (corrected and masked ndvi)



def main(ipat):
    
##   call function to get image metadata
    mdDic=imgMD(ipat)
    
    #output should be dictionary
    baseName=mdDic['baseName']
    
    a=stopGO(378, baseName)
    
    ## function to create working directory for this image
    wod=makeWod(baseName, temp1)
    
    #output is working folder path
    
    ## function to check for dem crs
    
    #parameters
    imgCrs=mdDic["imgCrs"]
    global dem
    dem=demCheck(dem, imgCrs, wod)
    
    #output is path to (new) dem
    
    a=stopGO(394, baseName)
    ##------- RED IMAGE
    ## function to seprate multilayer image in single band (RED)
    bNum=4
    Red=bndSep(ipat, bNum, wod)
    #output is path to RED band geotiff
    
    ## function to create parameters for athm. corr. in single band image (RED)
    redPar=makePar(baseName, bNum, wod)
    
    ## function to calculate pixel range in band (RED)
    redRange=pixRange(Red, wod)
    
    ## function to perform athm. corr. on single band image (RED)
    extImg=mdDic['extImg']
    redCor=atCorr(Red, baseName, redPar, redRange, bNum, extImg, wod )
    
    # output should be path to corrected image (RED)
    print "corrected image is %s" %redCor
    
    a=stopGO(400, baseName)
    
    ###------- NIR IMAGE
    ## function to seprate multilayer image in single band (NIR)
    bNum=8
    Nir=bndSep(ipat, bNum, wod)
    #output is path to NIR band geotiff
    
    ## function to create parameters for athm. corr. in single band image (NIR)
    nirRPar=makePar(baseName, bNum, wod)
    
    ## function to calculate pixel range in band (NIR)
    nirRange=pixRange(Nir, wod)
    
    ## function to perform athm. corr. on single band image (NIR)
    extImg=mdDic['extImg']
    nirCor=atCorr(Nir, baseName, nirPar, nirRange, bNum, extImg, wod )
    
    print "corrected image is %s" %nirCor
    # output should be path to corrected image (NIR)
    a=stopGO(400, baseName)
    
    #Function to calculate NDVI
    
        
#-------------------------------code---------------------------------

#
#####LOG
#timestr=(
#    '1{date:%Y-%m-%d %H:%M:%S}'.format( date=datetime.datetime.now() )
#    )
#    
#logpath=outd+"/"+"log.txt"
#Lfile=open(logpath, "w")
#logtext= "\nAthmospheric correction using SentinelPreprocessing.py started at %s" %(timestr)
#Lfile.write(logtext)
#print logtext
#
##### 0- TRIGGER
##TRIGGER to check if there are new images
#
###Search for images in input directory
##function to search for images recursively
## empty list with root
#
####Search in input directory
#
#Orlist=srcImg(multifolds1)
###Search in output directory
#
#Outlist=srcImg(multifolds2)
#####list of output images
## get sublist of missing/non processed images
#
#RlistNP=[y for y in Orlist[1] if os.path.basename(y) not in Outlist[0]]
#
##if sublist is of length 0 exit right now
#
#
## get path of image
#    # import image
##calling process as function
#def correct(ipat):
#    # use global variables
#    global dem
#    global outd
#    global temp
#    #get baseName
#  
#    #### 3 Athmospheric correction
## paramters
#
#    # For seventh line (average altitude in km)
#    #altitude average
#    demStats=p.runalg("grass7:r.univar",dem,None,"","",False,extImg,None)
#    statFile=open(demStats['output'], "r")
#    line=statFile.read().splitlines()[1]
#    #negative altitude average in km
#    avgDem=-1*float(line.split('|')[6])/1000
#
#    #For eighth line (Sensor band)
#    # band codes as dictionary
#    bcodes=range(166, 179)
#
#    try:
#        corrDic
#    except NameError:
#        corrDic={}
#            
#    ####---- Loop through bands
#    for i in brange:
#        band="band"+str(i)
#        bRast=QgsRasterLayer(bPatDic[band])
#    if not bRast.isValid():
#        print "problem with raster band image to correct"
#        print "\n path to image is: %s" %(bPatDic[band])
#        quit()
#        
#     
#
#        
#        
#
#        
#
#        
#        
#        
#        
#        # launch athmospheric correction
#        
#        print "launching athmospheric correction on image"+baseName[-10:]
#        corrImg=p.runalg("grass7:i.atcorr",bRast,pRange,None, None,Spath,pRange,False,True,False,False,extImg,0,None)
#        #corrImg2=p.runalg("gdalogr:translate",corrImg['output'],100,True,"",0,"",extImg,False,6,4,75,6,1,False,0,False,"",None)
#        if QgsRasterLayer(corrImg['output']).isValid:
#        print "athmospheric correction is valid"
#            corrDic[band]=corrImg['output']
#
#    # preparing list of inputs for topographic correction
#    inpList=[corrDic[x] for x in blist ]
#    #### TOPOGRAPHIC CORRECTION
#    # preparation
#    #calculating sun azimuth and zenith
#
#    #sunMod= p.runalg("grass7:r.sunhours",year,month,day,hours,minutes,seconds,"","",False,False,extImg,0,None,None,None)
#    #
#    ##function to extract minimum value from metadata
#    #def getMin(rast):
#    #    layer=QgsRasterLayer(rast).metadata()
#    #    text1=layer.split("STATISTICS_MINIMUM")[1]
#    #    text2=text1.split("</p")[0][1:]
#    #    return float(text2)
#    #    
#    ##calling function on results of Sun Mod
#    #elevation=getMin(sunMod['elevation'])
#    #zenith=90-elevation
#    #azimuth=getMin(sunMod['azimuth'])
#    ##illumination model
#    #ilMod=p.runalg("grass7:i.topo.coor.ill",dem,elevation,azimuth,extImg,0,None)
#
#
#    ##actual topographic correction
#    #topocorr=p.runalg("grass7:i.topo.corr",inpList,ilMod['output'],zenith,0,False,extImg,None)
#    #
#    ##extracting path to topo corrected tif files
#    #topocList=[]
#    #for r,d,files in os.walk(topocorr['output']):
#    #        for f in files:
#    #            if f.endswith(".tif"):
#    #                topocList.append(os.path.join(r,f))
#    #
#    ##verify topographically corrected files
#    #for i in topocList:
#    #    if not QgsRasterLayer(i).isValid():
#    #        print "problem with topographically corrected files"
#    #    else:
#    #        print " all bands have been topographically corrected"
#
#
#    #Exporting Images
#    #scene idnetifier for folder
#    scId=baseName.split("_")[5]
#    outpath=os.path.join(outd,scId)
#    if not os.path.exists(outpath):
#        os.makedirs(outpath)
#
#    outpath2=outpath+"/"+baseName+".tif"
#    final=p.runalg("gdalogr:merge",inpList,False,True,6,outpath2)
#    print "final multilayer image is saved"
#    #cleanup
#    bPatDic={}
#    corrDic={}
#    #remove corrected single bands 
#    clList=[corrDic[x] for x in blist ]
#    for y in clList:
#    os.path.remove(y)
#    # remove single bands
#    clList=[bPatDic[x] for x in blist ]
#    for z in clList:
#        os.path.remove(z)
#    print "all working files removed"
#    
#    
#    return final['OUTPUT']
#    
##calling function in parallel mode
#pool=Pool(10)
#results=pool.map(correct, RlistNP)
#
#### procedural run
#print "\n\n"+str(RlistNP)
#results=correct(RlistNP[0])
##for ipat in RlistNP:
##    print ipat
##    res=correct(ipat)
## end of cycle
#
#
#
#### 7 write logfile
#
## add script name
#
## add date and time
#
## add number of images
#
##8 Clean up
##Log conclude
#timestr2=(
#    '1{date:%Y-%m-%d %H:%M:%S}'.format( date=datetime.datetime.now() )
#    )
#    
#logstr="Corrected images are available in %s" %(outd)
#logstr2="Script finished correctly at %s" %(timestr2)
#
#Lfile.write(logstr)
#Lfile.write(logstr2)
#Lfile.close()
#print logstr
#print logstr2
## When your script is complete, call exitQgis() to remove the provider and
## layer registries from memory
##Qgs.exitQgis()
#
#


