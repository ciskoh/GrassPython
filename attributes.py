asplist=["Flat", "North", "East", "South", "West"]
slolist=["Flat","Gently sloping" ,"Sloping", "Steep", "Very steep"]
# To be checked
lulist=["Grassland", "Open shrubland", "Dense shrubland", "Open forest", "Dense forest", "Agriculture"]

def attr(numb):
    a,b,c=str(numb)
    # add land use
    print(lulist[int(a)-1])
    
    # add slope
    print(slolist[int(b)])
    
    # add aspect
    print(asplist[int(c)])

import sys
import os
print os.getcwdu()