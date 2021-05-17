# simstock-model
Simstock core model 

CEPT_SWS_Winterschool branch has working shapefile version of code.

## 1_Shapefile_processing.py
Converts shapefiles to polygons

The following data is also imported from the shapefiles:
osgb: building identifier
age: building age, used to assign constructions
condition: building condition, not currently used
floors: used in 2_AMD_idf_geometry.py with fixed floor to floor height to create 3D geometry
use: used in 2_AMD_idf_geometry.py to assign occupancy and equipment schedules

Contains the following functions:
Preprocessing - converts shapefiles to pandas dataframe
  Expand_floors - create a separate entry for each floor, assign mixed use to commercial for ground floor and residential above
  Combine_uses - combine uses to simplify model
  catchment_area - intended to define shading based on configuration file - not used in this version.

Preprocessing_constructions
  defines 3 construction sets with lists of materials, these can either be assigned by age or randomly.
  
remove_duplicated_coordinates(df):
    Function which removes duplicated coordinates from Polygons within Pandas
    DataFrame  

def polygon_topology_check(df, touching, intersect, perimeter,
                           exposed, partition):
    Function which checks the relationship between polygons (separated,
    touching, intersected). Intersected polygons are not permitted. It also
    calculates the basic polygon parameters such as total perimeter length,
    exposed perimeter length and partition perimeter length.
    
def polygon_tolerance(df):
    Function which checks whether polygon simplification is required or not.
    Simplification is required if the difference between two consecutive
    Polygon coordinates is less than a tolerance previously defined (default
    0.1m)

def distance_within_tolerance(coords_list, tolerance):
    Internal function which loops through the list of coordinates and check
    the distance between two consecutive coordinates. If the distance is
    less than a tolerance the looping stops and True is returned. Otherwise
    the False is returned.
    
def polygon_simplification(df, df_removed, simplify_polygon_no):
    Function which simplifies polygons. During simplification procedure some
    polygons initial excluded from simplification might be affected and get to
    the shape to require simplification. That's the reason of checking
    tolerance after simplification procedure and repeats simplification if
    there is a need for.
    
def polygon_buffer(df):
        Internal function which searches for invalid polygons; buffer them; and
        than check for removed coordinates after buffering in order to update
        affected adjacent polygons (if any)
        
def collinear_exterior(df):
    Function which searches for collinear points and creates the polygon which
    is used for horizontal surfaces (roof/ceiling/floor). Also checks for
    non-convex horizontal surfaces



