from eppy.modeleditor import IDF
import pandas as pd
import os

IDF.setiddname(r'C:\EnergyPlusV8-9-0\Energy+.idd') #move elsewhere
idf = IDF('base.idf')

def create_const_dicts_csv(df):
    const_dict = []
    for _, row in df.iterrows():
        dictionary = {}
        for i, content in enumerate(row):
            label = row.index[i]
            if not pd.isna(content) and not label == 'Notes':
                dictionary[label] = content
        const_dict.append(dictionary)
    return const_dict

# create a list of the specific instances of materials needed
# i.e. extract material names from constructions in use
def get_required_materials(const):
    materials_list = []
    for item in const:
        materials = list(item.values())[1:] #ignore construction names
        materials_list = [y for x in [materials_list, materials] for y in x]

    dict_list=[]
    for b in set(materials_list): #get unique
        d = {}
        d['Name'] = b 
        dict_list.append(d)
    return dict_list

def create_mat_dicts_csv(df):
    materials_dict = []
    for _, row in df.iterrows():
        dictionary = {}
        for i, content in enumerate(row):
            label = row.index[i]
            if not pd.isna(content) and not label == 'Notes':
                dictionary[label] = content
        materials_dict.append(dictionary)
    return materials_dict

def add_constructions(construction_dict):
    for const in construction_dict:
        idf.newidfobject("CONSTRUCTION",**const)

def add_materials(material_file, dict_list):
    materials = create_mat_dicts_csv(pd.read_csv(material_file.path))#read in the material details
    material_type = material_file.name[9:-4].replace("_", ":") #change names to match energyplus fields (excel doesn't allow ':' in sheet name)
    
    #add the material properties to the specific instance of the material
    new_list=[]    
    for mat in materials:
        for item in dict_list:
            if item['Name']==mat['MatName']:
                new_item=dict(item,**mat)
                new_list.append(new_item)
                   
    for el in new_list:
        del(el['MatName'])#remove the temporary matname field
        idf.newidfobject(material_type,**el) #expand each dictionary as a new material of the relevant type

database_dir = os.path.abspath('Database')
database_files = [file for file in os.scandir(database_dir) if file.name[:9] == "Database-"]
construction_file = os.path.join(database_dir, "Database-CONSTRUCTION.csv")
material_files = [file for file in database_files if "MATERIAL" in file.name]
constructions_csv = pd.read_csv(construction_file)

const = create_const_dicts_csv(constructions_csv)
print(const)
add_constructions(const)
used_materials = get_required_materials(const)

for file in material_files:
    add_materials(file, used_materials)

#idf.saveas('basic_settings.idf')