# %%
import pandas as pd
import numpy as np
from eppy.modeleditor import IDF

# %%
def getzones(idf):
    '''Finds zones in idf and outputs numpy array
    TODO:
        -Does it work with zone multipliers?
    '''
    zones = idf.idfobjects['ZONELIST'][0]      # get zonenames
    lst = [""]*len(zones.fieldnames)    # initiate blank list
    
    for i, fieldname in enumerate(zones.fieldnames):
        lst[i]=zones[fieldname]     # extract zonenames from eppy obj
    
    lst = np.array(lst)
    lst = lst[lst!=""]      # strip blank objects out
    zonelist = lst[2:]      # remove headers
    
    return zonelist

# %%
csv = r"C:\Users\biscu\Documents\phd\Internship\QGIS plugin\test working directory\idf_files\bi_528830-15_186037-12\eplusout.csv"
df = pd.read_csv(csv)
IDF.setiddname(r"EnergyPlus\ep8.9_windows\Energy+.idd")
idf = IDF(r"C:\Users\biscu\Documents\phd\Internship\QGIS plugin\test working directory\idf_files\bi_528830-15_186037-12.idf")

# %%
zones = getzones(idf)
threshold_value = 18.0
results = {}
def make_results_dict(zones, results):
    for zone in zones:
        zonename = zone.upper() #E+ outputs zone names in caps in results
        zonecols = [col for col in df.columns if zonename in col]
        results[zone] = df[zonecols]
    return results

def get_operative_threshold(results):
    for zone, df in results.items():
        output_name = "Zone Operative Temperature"
        operative_col = [col for col in df.columns if output_name in col]
        operative_series = df[operative_col[0]] #should only be one col
        above = operative_series[operative_series > 18].count()
        below = operative_series[operative_series <= 18].count()

        output_name = "Electricity"
        elec_col = [col for col in df.columns if output_name in col]
        elec_series = df[elec_col[0]] #should only be one col
        elec = elec_series.sum()
        print(zone,": ", above+below, elec)

results = make_results_dict(zones, results)
output_names = ['Zone Operative Temperature', 'Electricity']
get_operative_threshold(results)
# %%
