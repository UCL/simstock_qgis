# Simstock pilot study version
Used to convert footprint and building height data from Edina Digimap into extruded 3D model idf file. Allows selection of basic construction types to be used in the generation of the energy model. Uses occupancy schedules from Pamela, Paul and Ivan's uSIM2020 paper which were derived from NCM.

## Create and activate conda environment (simstock)
```
conda create -n simstock
conda activate simstock
```

## Install necessary python modules (within simstock environment)
```
conda install -c conda-forge pandas shapely
pip install eppy
pip install geopandas==0.9.0
```

## 1_preprocessing.py

Changeable fields:
* tolerance (minimum allowed distance between 2 coordinates [m], default=0.1)

Load the raw data into pandas dataframe

Test polygons for validity and coordinates direction

Remove duplicated coordinates (if any) from polygon coordinates

Check polygon topology (no intersection allowed)

Simplify polygons to preserve custom defined minimum allowed distance between two consecutive coordinates

Check polygon topology after simplification (no intersection allowed)

Remove collinear points and determine exterior surfaces coordinates

Check polygon topology after collinearity check (no intersection allowed)

save preprocessed file


## 2_idf_geometry.py

Changeable fields:
* min_avail_width_for_window = 1 (Do not place window if the wall width is less than this number, default=1)
* min_avail_height (Do not place window if partially exposed external wall is less than this number % of zone height, default=80)

Find the computer's operating system and set path to E+ idd file

Change the name field of the building object

Load input data (preprocessing outputs)

Move all objects towards origins

Shading volumes converted to shading objects: Function which generates idf geometry for surrounding Build Blocks. All elements are converted to shading objects

Polygons with zones converted to thermal zones based on floor number: [summary]

Extract names of thermal zones

Create a 'Dwell' zone list with all thermal zones. "Dwell" appears in all objects which refer to all zones (thermostat, people, etc.)

Ideal loads system

Save idf file
