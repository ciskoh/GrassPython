##DetailedProdAnalysis=group
##showplots
##degMap=raster
##poly=vector
##output=file

##to remove for QGIS plugin####
pathRast="C:/Users/jkm2/Dropbox/ongoing/BFH-Pastures/gis data/Analysis/degMap/degMap_ts3.tif"
pathVect="C:/Users/jkm2/Dropbox/ongoing/BFH-Pastures/gis data/Analysis/RQgis-test"


degMap=brick(pathRast)
polyMask=readOGR(dsn = pathVect, "poly")

#----------------------------BODY
library(raster)
library(rgdal)

# extracting values from raster
vals=as.integer(unlist(extract(degMap, polyMask)))
                
# calculating sum and average
cVals=na.omit(vals)
sumProd=sum(cVals, na.rm=T)
countProd=length(cVals)
avgProd=round(sumProd/countProd)
hecArea=round(countProd/1000)

#--------preparing subset of map

# function to change CRS of polygon if needed
trCRS<-function(rast, poly){
  # input: rast - RASTER        - raster for reference
  #        poly - SPATIALPOLYGON - polygon to be checked
  # output: SPATIALPOLYGON with same CRS as raster
  
  projRast=crs(rast)
  projPoly=crs(poly)
  
  
  if (as.character(projPoly)==as.character(projRast)) {
    newPoly=poly
  } else {
    newPoly=spTransform(poly, projRast)
  }
  return(newPoly)
}

#call function above on PolyMask
newPoly=trCRS(degMap, polyMask)

# creating extent for the map

extPoly=extent(newPoly)
#enalrging extent
xBuff=(extPoly[2]-extPoly[1])/2
yBuff=(extPoly[4]-extPoly[3])/2

newExtPoly=extent(extPoly[1]-xBuff,extPoly[2]+xBuff, extPoly[3]-yBuff, extPoly[4]+yBuff)

# ------------Graphics

# parameters for graph
par(mfcol=c(1,2),      # divide plot in 2 slots
    main=c(5,4,4,2),    # margin size
    pin=c(3, 3)  # plot size
    )
#palette
plotPal=c("red", "orange", "green", "dark green")
#YminMax
maxFreq=max(table(vals), na.rm=TRUE)
yMax=round(maxFreq, -(nchar(as.character(maxFreq))-1))
yMM=c(0, yMax)

#X min and Max
xMax=length(unique(vals))
xMM=c(0, xMax)

# x labels
perc=round(table(vals)/sum(table(vals))*100)
percStr=paste("(", perc, "%", ")", sep="")
xLabs=c("tres peu productive", "peu productive", "productive", "tres productive")
xCats=paste(xLabs, percStr)

#5 Main title
mTit="Productivite de la vegetation dans la zone selectionnee"

# draw graph
pie(x = table(vals), 
    edges = 360, 
    radius = 0.9, 
    init.angle = 90, 
    col = plotPal, 
    clockwise = 1, 
    labels=xCats)

title(main=mTit, adj=0)

text.default(x = -1.9 , y=-0.9, paste(labels="surface selectionnee: ", hecArea, "hectares" ),adj = c(0,0), font=2)
text.default(x = -1.9 , y=-1, paste(labels="capacite de charge: ", sumProd, "petits ruminants", "(environ", avgProd, "par hectare )"),adj = c(0,0), font=2)

#plotting map

plot(degMap, col=plotPal, colNA="black", ext=newExtPoly, axes=F, legend=F, box=F)
plot(newPoly, col=rgb(1,0,1,0.1), add=TRUE)

                                      