import os
from eppy.modeleditor import IDF
import pandas as pd
import numpy as np

def main():
    ### SET ENERGYPLUS IDD FILE:
    IDF.setiddname(r"EnergyPlus\ep8.9_windows\Energy+.idd")

    ### SET THE IDF FILE TO BE CONVERTED:
    idf = IDF("basic_settings backup.idf")

    ### THE OBJECTS TO BE RETRIEVED FROM THE IDF FILE:
    # More can be added here if required - the dictonary key name needs to
    # match the idf object name exactly, except replacing ":" with "_"
    # and also it is not case-sensitive
    object_dict = {"material" : idf.idfobjects['MATERIAL'],
               "material_nomass" : idf.idfobjects['MATERIAL:NOMASS'],
               "material_infraredtransparent" : idf.idfobjects['MATERIAL:INFRAREDTRANSPARENT'],
               "material_airgap" : idf.idfobjects['MATERIAL:AIRGAP'],
               "windowmaterial_glazing" : idf.idfobjects['WINDOWMATERIAL:GLAZING'],
               "windowmaterial_gas" : idf.idfobjects['WINDOWMATERIAL:GAS'],
               "construction" : idf.idfobjects['CONSTRUCTION']}
    
    ### CONVERT TO CSV FILES:
    # Note that if the csv files already exist, they will be appended to
    object_dict = convert_object_dicts(object_dict)
    dict_to_csv(object_dict)

################################################################################

def to_dict(objects, is_material):
    dicts = []
    for object in objects:
        dict = {}
        no_objs = len(object.obj) #no of values
        no_objls = len(object.objls) #no of fields
        for i in range(no_objls + 1):
            if i < no_objs:
                if object.objls[i] == "key":
                    continue
                elif object.objls[i] == "Name":
                    if is_material:
                        dict["MatName"] = object.obj[i]
                    else:
                        dict[object.objls[i]] = object.obj[i]
                else:
                    dict[object.objls[i]] = object.obj[i]
            elif i < no_objls:
                dict[object.objls[i]] = np.nan
            else:
                dict["Notes"] = np.nan
        dicts.append(dict)
    return dicts

def convert_object_dicts(object_dict: dict):
    """Converts list of idf objects into a dictionary, matching the field names 
    with their values."""
    for object_type, objects in object_dict.items():
        if "material" in object_type:
            is_material = True
        else:
            is_material = False
        object_dict[object_type] = to_dict(objects, is_material)
    return object_dict

def dict_to_csv(object_dict):
    for object_type, objects in object_dict.items():
        if len(objects) != 0:
            filename = "Database-" + object_type.upper() + ".csv"
            df = pd.DataFrame.from_dict(objects)
            if os.path.exists(filename):
                print("File: '%s' found. Appending to csv..." % filename)
            df.to_csv(filename, mode='a', header=not os.path.exists(filename), index=False)

if __name__ == "__main__":
    main()