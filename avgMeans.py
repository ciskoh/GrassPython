import os
#-------------------------------------------------------------

path="/media/matt/DAFOTEC SAS/output/"

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
print pDate

for d in pDate:
    print d
    mP=[k for k in pImg if d in k]
    print "small list is"+str(mP)
    