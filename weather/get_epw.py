# %%
import xml.etree.ElementTree as ET
import pandas as pd
tree = ET.parse('kmls\Reg1_Africa_TMYx_EPW_Processing_locations.kml')
root = tree.getroot()

#for child in root.findall('.//{http://earth.google.com/kml/2.1}coordinates'):
#    print(child.text)
    
#for child in root.iter():
#    print(child)

children = [child for child in root[0] if "Placemark" in child.tag]

#alter this to use "coordinates" keyword in case the structure of the kml file changes in the future
epw_coords = [(child[0].text, child[3][1].text) for child in children]

names = []
coords = []

for child in children:
    names.extend([component.text for component in child if "name" in component.tag])
    descs = [component.text for component in child if "description" in component.tag]
    points = [component for component in child if "Point" in component.tag]
    coords.extend([component.text for component in points if "coordinates" in component.tag])

# %%
pd.read_html(children[5][1].text)[0]
children[5][1].text.split(" ")[-1]