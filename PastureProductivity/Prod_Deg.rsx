## Analyse de la productivite des paturages=group
##showplots
##CarteDesPaturages= raster
##Polygone= vector

# SCRIPT TO ANALYSE MAP OF VEGETATION PRODUCTIVITY IN A SPECIFIC AREA.
# SELECTS PIXELS INSIDE A SPECIFIED AREA (USING A POLYGON) AND OUTPUTS A PIE CHART OF DEGRADATION, INFORMATION ON THE SURFACE SELECTED AND ON THE CARRYING CAPACITY
# REQUIRES R AND QGIS AND MADE FOR WINDOWS 7 (ALLTHOUGH MIGHT BE PORTABLE)

#----------------------------CODE
library(raster)
library(rgdal)

rast=stack(CarteDesPaturages)
degMap=rast[[1]]
degMap2=rast[[2]]
polyMask=Polygone
print(CarteDesPaturages)
# extracting values from raster
vals=as.integer(unlist(extract(degMap, polyMask)))
vals2=as.integer(unlist(extract(degMap2, polyMask)))
# calculating sum and average
cVals=na.omit(vals)
sumProd=sum(as.numeric(cVals), na.rm=T)
countProd=length(cVals)
avgProd=round(sumProd/countProd)
hecArea=round(countProd/1000)
# calculating carrying capacity
#formula for carrying capacity calculation: CC=(P-R)/(C*T)
#P: productivity - sum of biomass
#R: reserve - By judgement (30%)
#C: consume per head (30 % of body weight) -avg body weight : 10 kg
#T: Time (1 month)

P=sumProd
R=0.4*sumProd

C=10000*0.3
#carrying capacity
CC=round((P-R)/(C*30))
#average carrying capacity per hectare
avCC=round(CC/hecArea, 2)
# ------------Graphics

# parameters for graph

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
#TODO problem with basename of le
bn=names(rast)[1]
mois=substr(bn, 7, 8)
an=substr(bn, 3,6)

mTit=paste("Productivite de la vegetation pour le mois", mois, "de l'annee", an)

# draw graph
pie(x = table(vals2),
edges = 360,
radius = 0.6,
init.angle = 90,
col = plotPal,
clockwise = 1,
labels=xCats)

title(main=mTit, adj=0)

text.default(x = -0.9 , y=-0.9, paste(labels="-->surface selectionnee: ", hecArea, "hectares" ),adj = c(0,0), font=2)
text.default(x = -0.9 , y=-1, paste(labels="-->capacite de charge: ",CC, "petits ruminants", "(~", avCC, "/Hect. )"),adj = c(0,0), font=2)
