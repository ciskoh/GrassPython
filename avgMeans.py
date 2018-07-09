import os
import gdal
import numpy as np
import osgeo.osr as osr
#-----------------------PAR--------------------------------------

path="/media/matt/DAFOTEC/output/"
outN="avgMeans_final"

#--------------------CODE
# create output folder
parDir=os.path.dirname(os.path.dirname(path))

outDir=os.path.join(parDir, outN)
tempDir=os.path.join(outDir, "workFiles")
finDir=os.path.join(outDir, "finOutput")

if not os.path.exists(outDir):
    os.mkdir(outDir)
    os.mkdir(tempDir)
    os.mkdir(finDir)
    
# find file in folder
pImg=[]
pDate=[]
for r,d,f in os.walk(path):
    for file in f:
        
        if file.endswith(".tif"):
            pImg.append(os.path.join(r,file))
            pDate.append(file[2:8])
           

pDate=list(set(pDate))
pDate.sort()

#get images in the same month
for d in pDate:
    print "date is: "+str(d)
    mP=[k for k in pImg if d in k]
    print "small list is"+str(mP)
    
    #calculate mean of band 1
    for i, tiff in enumerate(mP):
        print "working on image number %s for date %s: %s" %(i, d, tiff)
        gd_obj = gdal.Open(tiff)
        array = gd_obj.GetRasterBand(1).ReadAsArray()
        array = np.expand_dims(array,2)
        array[(array==999) & (array<=0)]=np.nan
        if i == 0:
            allarrays = array
        else:
            allarrays = np.concatenate((allarrays, array), axis=2)
    print "this is the array band 1:"
    print allarrays.shape
    print allarrays.max()
    b1Mean = np.nanmean(allarrays, axis=2)
    b1Mean[np.isnan(b1Mean)]=999
    print "band 1 created"
    del allarrays
    
    #calculate mode of band 2
    for i, tiff in enumerate(mP):
        print"creating band 2 for date %s: image %s" %(d,tiff)
        gd_obj = gdal.Open(tiff)
        Barray = gd_obj.GetRasterBand(2).ReadAsArray()
        Barray = np.expand_dims(Barray,2)
        Barray[Barray>4]=np.nan
        if i == 0:
            Ballarrays = Barray
        else:
            Ballarrays = np.concatenate((Ballarrays, Barray), axis=2)
    b2ModeT=np.nanmean(Ballarrays, axis=2)
    b2Mode=np.rint(b2ModeT)
    b2Mode[np.isnan(b2Mode)]=999
    print "band 2 created"
    print b2Mode
    del Ballarrays
    
    #write new file
    outName=os.path.join(finDir, "mt"+d+".tiff")
    rfGeo=gd_obj.GetGeoTransform()
    drv = gdal.GetDriverByName("GTiff")
    ds = drv.Create(outName,gd_obj.RasterXSize, gd_obj.RasterYSize, 2, gdal.GDT_Float32)
    ds.SetGeoTransform(rfGeo)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(32630)
    ds.SetProjection(srs.ExportToWkt())
    ds.GetRasterBand(1).WriteArray(b1Mean)
    ds.GetRasterBand(2).WriteArray(b2Mode)
    
    del b1Mean
    del b2Mode
    
    ds=None
    print "finished writing file at %s for date %s" %(outName, d)
    
    