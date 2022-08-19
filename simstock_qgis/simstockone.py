import os
import pandas as pd
from ast import literal_eval
from shapely.ops import unary_union, linemerge
from shapely.wkt import loads, dumps
from time import time, localtime, strftime
from shapely.geometry import Polygon, LineString, MultiLineString, LinearRing, MultiPolygon


ROOT_DIR = os.path.abspath(os.path.dirname(__file__))

tolerance = 0.1  # minimum allowed distance between 2 coordinates [m]


def main():
    start = time()
    print('__________________________________________________________________',
          flush=True)
    print(strftime('%d/%m/%Y %H:%M:%S', localtime()),
          '- {} start time'.format(os.path.basename(__file__)), flush=True)

    # Load the raw data into pandas dataframe
    df = pd.read_csv(os.path.join(ROOT_DIR, 'sa_data.csv'))

    # Check for nested polygons
    df = check_for_multipolygon(df)

    # Test polygons for validity and coordinates direction
    df['sa_reverse_coordinates'] = False
    df = polygon_testing(df)
    reverse_coordinates_no = df['sa_reverse_coordinates'].sum()
    if reverse_coordinates_no > 0:
        df = reverse_coordinates(df)
    df = df.drop(['sa_reverse_coordinates'], axis=1)

    # Remove duplicated coordinates (if any) from polygon coordinates
    df = remove_duplicated_coordinates(df)

    # Check polygon topology (no intersection allowed)
    df = polygon_topology(df, 'sa_initial_touching', 'sa_initial_intersect')

    # Simplify polygons to preserve custom defined minimum allowed distance
    # between two consecutive coordinates
    df = polygon_tolerance(df)
    simplify_polygon_no = df['sa_polygon_simplify'].sum()
    if simplify_polygon_no > 0:
        df = polygon_simplification(df, simplify_polygon_no)

    # Check polygon topology after simplification (no intersection allowed)
    df = polygon_topology(df, 'sa_simplified_touching',
                          'sa_simplified_intersect')

    # Remove collinear points and determine exterior surfaces coordinates
    df = collinear_exterior(df)

    # Check polygon topology after collinearity check (no intersection allowed)
    df = polygon_topology(df, 'sa_collinear_touching',
                          'sa_collinear_intersect')

    # Adds a column denoting built islands if applicable
    newdf = bi_adj(df)
    
    # save preprocessed file
    newdf.to_csv(os.path.join(ROOT_DIR, 'sa_preprocessed.csv'), index=False)

    pt('##### preprocessing completed in:', start)


# END OF MAIN  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def check_for_multipolygon(df):
    """
    Hand-drawn polygons can be multipolygons with len 1, i.e. a nested 
    polygon within a multipolygon wrapper. This aims to extract them.
    """
    for index, row in df.iterrows(): #TODO: re-write with itertuples
        polygon = loads(row.polygon)
        if isinstance(polygon, MultiPolygon):
            if len(polygon) == 1:
                df.at[index, 'polygon'] = str(polygon[0])
            else:
                raise RuntimeError("Polygon for '%s' is a multipolygon." % row.osgb)
    return df

def bi_adj(df):
    df['sa_polygon'] = df['sa_polygon'].apply(loads)
    #gdf = gpd.GeoDataFrame(df, geometry='polygon')
    #polygon_union = gdf.polygon.unary_union
    gdf = df.copy(deep=True) #recoded to avoid using geopandas
    polygon_union = unary_union(gdf.sa_polygon)

    if polygon_union.type == "MultiPolygon":
        for i, bi in enumerate(polygon_union):
            # Get a unique name for the BI which is based on a point
            # within the BI so that it doesn't change if new areas are lassoed
            rep_point = bi.representative_point()
            bi_name = "bi_" + str(round(rep_point.x, 2)) + "_" + str(round(rep_point.y, 2))
            bi_name = bi_name.replace(".", "-") #replace dots with dashes for filename compatibility
            for index, row in gdf.iterrows():
                if row['sa_polygon'].within(bi):
                    gdf.at[index, 'bi'] = bi_name

        ### The following part just checks consistency against internal simstock
        ### adjacent polygon calculations. Not necessary but nice to have. Needs
        ### to be recoded without geopandas
        
        # for index, row in gdf.iterrows():
        #     touching = gdf[gdf.polygon.touches(row['polygon'])]
        #     adj_checked = []
        #     for i, building in touching.iterrows():
        #             if row['polygon'].intersection(building['polygon']).type in ["LineString", "MultiLineString"]:
        #                 adj_checked.append(building['osgb'])
        #     gdf.at[index, "adjacent"] = str(adj_checked)
            
        # for i, row in gdf.iterrows():
        #     if row['sa_collinear_touching'] != row['adjacent']:
        #         raise RuntimeError("built island mismatch")
        # Can drop the adjacent column at this point
                
        modal_bi = gdf.bi.mode().values
        modal_bi_num = sum(gdf.bi.isin([modal_bi[0]]).values)
        print("The BI(s) with the most buildings: %s with %s buildings" % (modal_bi, modal_bi_num))
        return gdf
    else:
        return gdf

def pt(printout, pst):
    pft = time()
    process_time = pft - pst
    if process_time <= 60:
        unit = 'sec'
    elif process_time <= 3600:
        process_time = process_time / 60
        unit = 'min'
    else:
        process_time = process_time / 3600
        unit = 'hr'
    loctime = strftime('%d/%m/%Y %H:%M:%S', localtime())
    print('{0} - {1} {2:.2f} {3}'.format(loctime,
                                         printout, process_time, unit), flush=True)
    return

# END OF FUNCTION  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


def polygon_testing(df):
    for row in df.itertuples():
        osgb = row.osgb
        polygon = loads(row.polygon)

        if not polygon.is_valid:
            print('{} polygon is not valid'.format(osgb))

        if polygon.exterior.is_ccw:
            print('{} polygon outer ring is not clock-wise'.format(osgb))
            df.loc[row.Index, 'sa_reverse_coordinates'] = True
        if polygon.interiors:
            for inner_ring in polygon.interiors:
                if not inner_ring.is_ccw:
                    df.loc[row.Index, 'sa_reverse_coordinates'] = True
                    print(
                        '{} polygon inner ring is not counter clock-wise'.format(osgb))
    return df

# END OF FUNCTION  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


def reverse_coordinates(df):
    for row in df.itertuples():
        if row.sa_reverse_coordinates:
            polygon = loads(row.polygon)
            if polygon.exterior.is_ccw:
                ext_ring_coords = list(polygon.exterior.coords[::-1])
            else:
                ext_ring_coords = list(polygon.exterior.coords)
            int_ring = list()
            if polygon.interiors:
                for item in polygon.interiors:
                    if not item.is_ccw:
                        item_coords = list(item.coords[::-1])
                    else:
                        item_coords = list(item.coords)
                    int_ring.append(item_coords)
            polygon_reversed = Polygon(ext_ring_coords, int_ring)
            df.loc[row.Index, 'polygon'] = dumps(
                polygon_reversed, rounding_precision=2)
    return df

# END OF FUNCTION  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


def remove_duplicated_coordinates(df):
    for row in df.itertuples():
        polygon = loads(row.polygon)
        ext_ring_coords = list(polygon.exterior.coords)
        ext_ring_no_dup = remove_duplicated_coords_from_list(ext_ring_coords)
        int_ring_no_dup_list = list()
        if polygon.interiors:
            for item in polygon.interiors:
                item_coords = list(item.coords)
                int_ring_no_dup = remove_duplicated_coords_from_list(
                    item_coords)
                int_ring_no_dup_list.append(int_ring_no_dup)
        polygon_no_dup = Polygon(ext_ring_no_dup, int_ring_no_dup_list)
        df.loc[row.Index, 'sa_polygon'] = dumps(
            polygon_no_dup, rounding_precision=2)
    return df

# END OF FUNCTION  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


def remove_duplicated_coords_from_list(coords_list):
    coords_list_no_dup = list()
    if coords_list[0] == coords_list[-1]:
        del coords_list[-1]
        if len(coords_list) != len(set(coords_list)):
            [coords_list_no_dup.append(x)
                for x in coords_list if x not in coords_list_no_dup]
        else:
            coords_list_no_dup = coords_list
        coords_list_no_dup.append(coords_list_no_dup[0])
    else:
        if len(coords_list) != len(set(coords_list)):
            [coords_list_no_dup.append(x)
                for x in coords_list if x not in coords_list_no_dup]
        else:
            coords_list_no_dup = coords_list
    return coords_list_no_dup

# END OF FUNCTION  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


def polygon_topology(df, touching, intersect):
    df[touching] = '[]'
    df[intersect] = '[]'
    osgb_polygon_pairs = variable_polygon_pairs(df, 'osgb', 'sa_polygon')
    for osgb, osgb_polygon in osgb_polygon_pairs:
        osgb_touching, osgb_intersect = list(), list()
        for osgb_adj, adj_polygon in osgb_polygon_pairs:
            if osgb_adj != osgb:
                if osgb_polygon.touches(adj_polygon) and (
                        osgb_polygon.intersection(
                            adj_polygon).geom_type not in ['Point']):
                    osgb_touching.append(osgb_adj)
                if osgb_polygon.intersects(adj_polygon) and (
                        osgb_polygon.intersection(
                            adj_polygon).geom_type not in ['Point']):
                    osgb_intersect.append(osgb_adj)
        df.loc[df['osgb'] == osgb, touching] = str(osgb_touching)
        df.loc[df['osgb'] == osgb, intersect] = str(osgb_intersect)
        if len(osgb_touching) < len(osgb_intersect):
            difference = list(set(osgb_intersect) - set(osgb_touching))
            print('***WARNING: OSGB {} intersects following polygon(s): {}'.format(osgb,
                                                                                   difference), flush=True)
    df = df.drop([intersect], axis=1)
    return df

# END OF FUNCTION  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


def variable_polygon_pairs(df, variable_value, polygon_value):
    variable_polygon_values = df[[variable_value, polygon_value]].values
    variable_polygon = list()
    for variable, polygon in variable_polygon_values:
        polygon = loads(polygon)
        variable_polygon.append([variable, polygon])
    return variable_polygon

# END OF FUNCTION  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


def polygon_tolerance(df):

    def distance_within_tolerance(coords_list):
        for i, coord in enumerate(coords_list[:-1]):
            first = coords_list[i]
            second = coords_list[i + 1]
            distance = LineString([first, second]).length
            if distance < tolerance:
                return True
        return False

    for row in df.itertuples():
        polygon = loads(row.sa_polygon)
        ext_ring_coords = list(polygon.exterior.coords)
        simplify_required = distance_within_tolerance(ext_ring_coords)
        df.loc[row.Index, 'sa_polygon_simplify'] = simplify_required
        if simplify_required:
            continue
        if polygon.interiors:
            for item in polygon.interiors:
                item_coords = list(item.coords)
                simplify_required = distance_within_tolerance(item_coords)
                if simplify_required:
                    df.loc[row.Index, 'sa_polygon_simplify'] = simplify_required
                    break
    return df

# END OF FUNCTION  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


def polygon_simplification(df, simplify_polygon_no):

    def polygon_within_hole(df):
        for row in df.itertuples():
            osgb_polygon = loads(row.sa_polygon)
            osgb_within_hole = list()
            if osgb_polygon.interiors:
                osgb = row.osgb
                osgb_polygon_pairs = variable_polygon_pairs(
                    df, 'osgb', 'sa_polygon')
                for item in osgb_polygon.interiors:
                    item_polygon = Polygon(item.coords[::-1])
                    for osgb_adj, adj_polygon in osgb_polygon_pairs:
                        if osgb_adj != osgb:
                            if item_polygon.contains(adj_polygon) and osgb_polygon.touches(adj_polygon):
                                osgb_within_hole.append(osgb_adj)
            df.loc[row.Index, 'sa_polygon_within_hole'] = str(
                osgb_within_hole)
        return df

    def polygon_simplify(df):

        def touching_poly(df, osgb, polygon, osgb_list, osgb_touching):
            for t in osgb_list:
                if t != osgb:
                    if df.loc[df['osgb'] == t, 'sa_polygon'].values[0]:
                        t_polygon = loads(
                            df.loc[df['osgb'] == t, 'sa_polygon'].values[0])
                        if polygon.touches(t_polygon):
                            osgb_touching.append(t)
            return osgb_touching

        def polygon_simplifying(polygon, df, osgb, osgb_touching):

            def coords_cleaning(coords, remove_leave_pairs):

                def radial_dist_simplify(coords):

                    def remove_item_from_list(coords, item):
                        if coords[0] == coords[-1]:
                            coords = [x for x in coords if x != item]
                            if coords[0] != coords[-1]:
                                coords.append(coords[0])
                        else:
                            coords = [x for x in coords if x != item]
                        return coords

                    remove_leave_pair = list()
                    for i, coord in enumerate(coords[:-1]):
                        first = coords[i]
                        second = coords[i + 1]
                        distance = LineString([first, second]).length
                        if distance <= tolerance:
                            if i < (len(coords) - 2):
                                coord_remove = second
                                coord_leave = first
                            else:
                                coord_remove = first
                                coord_leave = second
                            remove_leave_pair = [coord_remove, coord_leave]
                            coords = remove_item_from_list(
                                coords, coord_remove)
                            return coords, remove_leave_pair
                    return coords, remove_leave_pair

                coords_lenght = len(coords) + 1
                while (len(coords) < coords_lenght) and (len(coords) > 3):
                    coords_lenght = len(coords)
                    coords, r_l_pair = radial_dist_simplify(coords)
                    if r_l_pair:
                        remove_leave_pairs.append(r_l_pair)
                return coords, remove_leave_pairs

            def simplified_coords(polygon, ring_position,
                                  remove_leave_pairs):
                if ring_position == 'outer':
                    coords = list(polygon.exterior.coords)
                    coords, remove_leave_pairs = coords_cleaning(
                        coords, remove_leave_pairs)
                    return coords, remove_leave_pairs
                elif ring_position == 'inner':
                    inner_coords_list = list()
                    for inner in polygon.interiors:
                        coords = list(inner.coords)
                        coords, remove_leave_pairs = coords_cleaning(
                            coords, remove_leave_pairs)
                        if len(coords) > 3:
                            inner_coords_list.append(coords)
                    return inner_coords_list, remove_leave_pairs

            def remove_cleaned_coordinates(coords, remove_leave_pairs):
                for pair in remove_leave_pairs:
                    for i, coord in enumerate(coords):
                        if coord == pair[0]:
                            coords[i] = pair[1]
                coords = remove_duplicated_coords_from_list(coords)
                return coords

            def simplification_affects_inner_ring(
                    adjacent_polygon, polygon, remove_leave_pairs):
                adjacent_inner_coords_list = list()
                for inner in adjacent_polygon.interiors:
                    inner_coords = list(inner.coords)
                    inner_polygon = Polygon(inner_coords)
                    if inner_polygon.contains(polygon):
                        inner_coords = remove_cleaned_coordinates(
                            inner_coords, remove_leave_pairs)
                    adjacent_inner_coords_list.append(inner_coords)
                adjacent_polygon = Polygon(adjacent_polygon.exterior,
                                           adjacent_inner_coords_list)
                return adjacent_polygon

            def ccw_iterior_ring(coords):
                if not LinearRing(coords).is_ccw:
                    coords = coords[::-1]
                return coords

            def not_valid_polygons(osgb, polygon, df, outer_coords,
                                   polygon_within_hole,
                                   remove_leave_pairs):

                def remove_hole_if_inner_is_removed(
                        df, inner_polygon, polygon_within_hole):
                    for p in polygon_within_hole:
                        p_polygon = df.loc[df['osgb'] ==
                                           p, 'sa_polygon'].values[0]
                        if p_polygon:
                            p_polygon = loads(p_polygon)
                            if inner_polygon.contains(p_polygon):
                                df.loc[df['osgb'] == p,
                                       'sa_polygon'] = False
                                p_polygon_within_hole = literal_eval(
                                    df.loc[df['osgb'] == p,
                                           'sa_polygon_within_hole'].values[0])
                                if p_polygon_within_hole:
                                    df = remove_holes(
                                        df, p_polygon_within_hole)
                    return df

                def p_is_not_valid(p):
                    ex = LinearRing(p.exterior)
                    for i, inner in enumerate(p.interiors):
                        in_i = Polygon(inner.coords)
                        if not ex.touches(in_i):
                            if ex.intersects(in_i):
                                return True
                    return False

                if p_is_not_valid(polygon):
                    eroded_outer = Polygon(outer_coords).buffer(-tolerance)
                    eroded_inner_list = list()
                    for inner in polygon.interiors:
                        inner_polygon = Polygon(inner.coords)
                        if inner_polygon.within(eroded_outer):
                            eroded_inner_list.append(inner)
                        else:
                            if eroded_outer.intersects(inner_polygon):
                                new_inner_polygon = eroded_outer.intersection(
                                    inner_polygon)
                                new_inner_coords = list(
                                    new_inner_polygon.exterior.coords)
                                if len(new_inner_coords) > 3:
                                    if polygon_within_hole:
                                        for p in polygon_within_hole:
                                            p_polygon = df.loc[df['osgb'] ==
                                                               p, 'sa_polygon'].values[0]
                                            if p_polygon:
                                                p_polygon = loads(
                                                    p_polygon)
                                                if inner_polygon.contains(p_polygon):
                                                    p_outer_coords = list(
                                                        p_polygon.exterior.coords)
                                                    p_outer_coords = remove_cleaned_coordinates(
                                                        p_outer_coords, remove_leave_pairs)
                                                    new_p_polygon = Polygon(new_inner_coords).intersection(
                                                        Polygon(p_outer_coords))
                                                    new_inner_diff = Polygon(new_inner_coords).difference(
                                                        Polygon(p_outer_coords))
                                                    united_inner_polygon = unary_union(
                                                        (new_inner_diff, new_p_polygon))
                                                    remove_leave_pairs_inner = list()
                                                    new_inner_coords, remove_leave_pairs_inner = simplified_coords(
                                                        united_inner_polygon, 'outer', remove_leave_pairs_inner)
                                                    p_outer_coords = list(
                                                        new_p_polygon.exterior.coords)
                                                    p_outer_coords = remove_cleaned_coordinates(
                                                        p_outer_coords, remove_leave_pairs_inner)
                                                    if len(p_outer_coords) > 3:
                                                        if p_polygon.interiors:
                                                            new_p_polygon = Polygon(
                                                                p_outer_coords, p_polygon.interiors)
                                                            p_polygon_within_hole = literal_eval(
                                                                df.loc[df['osgb'] == p, 'sa_polygon_within_hole'].values[0])
                                                            mock_list = list()
                                                            df, new_p_polygon = not_valid_polygons(
                                                                p, new_p_polygon, df, p_outer_coords, p_polygon_within_hole, mock_list)
                                                        else:
                                                            new_p_polygon = Polygon(
                                                                p_outer_coords)
                                                        df.loc[df['osgb'] == p, 'sa_polygon'] = dumps(
                                                            new_p_polygon, rounding_precision=2)
                                                    else:
                                                        df.loc[df['osgb'] == p,
                                                               'sa_polygon'] = False
                                    else:
                                        mock_list = list()
                                        new_inner_coords, _ = simplified_coords(
                                            new_inner_polygon, 'outer', mock_list)
                                    if len(new_inner_coords) > 3:
                                        new_inner_coords = ccw_iterior_ring(
                                            new_inner_coords)
                                        eroded_inner_list.append(
                                            new_inner_coords)
                                elif polygon_within_hole:
                                    df = remove_hole_if_inner_is_removed(
                                        df, inner_polygon, polygon_within_hole)
                            elif polygon_within_hole:
                                df = remove_hole_if_inner_is_removed(
                                    df, inner_polygon, polygon_within_hole)
                    polygon = Polygon(outer_coords, eroded_inner_list)
                return df, polygon

            def remove_holes(df, polygon_within_hole):
                if polygon_within_hole:
                    for p in polygon_within_hole:
                        p_polygon = df.loc[df['osgb'] ==
                                           p, 'sa_polygon'].values[0]
                        p_polygon_within_hole = literal_eval(
                            df.loc[df['osgb'] == p, 'sa_polygon_within_hole'].values[0])
                        if p_polygon and p_polygon_within_hole:
                            df = remove_holes(df, p_polygon_within_hole)
                        df.loc[df['osgb'] == p, 'sa_polygon'] = False
                return df

            polygon_within_hole = literal_eval(
                df.loc[df['osgb'] == osgb, 'sa_polygon_within_hole'].values[0])
            rlp = list()
            outer_coords, rlp = simplified_coords(polygon, 'outer', rlp)
            if len(outer_coords) > 3:
                if polygon.interiors:
                    inner_coords_list, rlp = simplified_coords(
                        polygon, 'inner', rlp)
                    new_polygon = Polygon(outer_coords, inner_coords_list)
                    if not inner_coords_list:
                        df = remove_holes(df, polygon_within_hole)
                    df, new_polygon = not_valid_polygons(
                        osgb, new_polygon, df, outer_coords,
                        polygon_within_hole, rlp)
                else:
                    new_polygon = Polygon(outer_coords)
                df.loc[df['osgb'] == osgb,
                       'sa_polygon'] = dumps(new_polygon, rounding_precision=2)
            else:
                df.loc[df['osgb'] == osgb, 'sa_polygon'] = False
                df = remove_holes(df, polygon_within_hole)

            if rlp and osgb_touching:
                for t in osgb_touching:
                    t_polygon = df.loc[df['osgb'] ==
                                       t, 'sa_polygon'].values[0]
                    if t_polygon:
                        t_polygon_within_hole = literal_eval(
                            df.loc[df['osgb'] == t,
                                   'sa_polygon_within_hole'].values[0])
                        t_polygon = loads(t_polygon)
                        osgb_polygon = df.loc[df['osgb'] == osgb,
                                              'sa_polygon'].values[0]
                        if osgb_polygon and t_polygon_within_hole and (osgb in t_polygon_within_hole):
                            t_polygon = simplification_affects_inner_ring(
                                t_polygon, polygon, rlp)
                        t_outer_coords = list(t_polygon.exterior.coords)
                        t_outer_coords = remove_cleaned_coordinates(
                            t_outer_coords, rlp)
                        if len(t_outer_coords) > 3:
                            if t_polygon.interiors:
                                t_polygon = Polygon(t_outer_coords,
                                                    t_polygon.interiors)
                                df, t_polygon = not_valid_polygons(
                                    t, t_polygon, df, t_outer_coords,
                                    t_polygon_within_hole, rlp)
                            else:
                                t_polygon = Polygon(t_outer_coords)
                            df.loc[df['osgb'] == t, 'sa_polygon'] = dumps(
                                t_polygon, rounding_precision=2)
                        else:
                            df.loc[df['osgb'] == t, 'sa_polygon'] = False
                            df = remove_holes(df, t_polygon_within_hole)
            return df

        osgb_list = df['osgb'].unique().tolist()
        for osgb in osgb_list:
            if df.loc[df['osgb'] == osgb, 'sa_polygon_simplify'].values[0]:
                osgb_touching = list()
                polygon = df.loc[df['osgb'] == osgb, 'sa_polygon'].values[0]
                if polygon:
                    osgb_polygon = loads(polygon)
                    osgb_touching = touching_poly(
                        df, osgb, osgb_polygon, osgb_list, osgb_touching)
                    df = polygon_simplifying(
                        osgb_polygon, df, osgb, osgb_touching)
        return df

    def polygon_buffer(df):

        def remove_buffered_coordinates(osgb, coords, new, removed):
            for r_c in removed:
                for i, coord in enumerate(coords):
                    if coord == r_c:
                        minimum_dist = LineString([r_c, new[0]]).length
                        replacement_coord = new[0]
                        for n_c in new:
                            dist = LineString([r_c, n_c]).length
                            if dist < minimum_dist:
                                minimum_dist = dist
                                replacement_coord = n_c
                        coords[i] = replacement_coord
            coords = remove_duplicated_coords_from_list(coords)
            return coords

        for row in df.itertuples():
            polygon = loads(row.sa_polygon)
            if not polygon.is_valid:
                new_polygon = polygon.buffer(0)
                df.loc[row.Index, 'sa_polygon'] = dumps(
                    new_polygon, rounding_precision=2)
                new_polygon = loads(
                    dumps(new_polygon, rounding_precision=2))
                osgb_touching = literal_eval(row.sa_initial_touching)
                if osgb_touching:
                    new_coords = list(
                        set(list(new_polygon.exterior.coords)) - set(list(polygon.exterior.coords)))
                    removed_coords = list(
                        set(list(polygon.exterior.coords)) - set(list(new_polygon.exterior.coords)))
                    if new_coords:
                        for t in osgb_touching:
                            t_polygon = loads(
                                df.loc[df['osgb'] == t, 'sa_polygon'].values[0])
                            t_polygon_coords = list(
                                t_polygon.exterior.coords)
                            t_polygon_coords = remove_buffered_coordinates(
                                t, t_polygon_coords, new_coords, removed_coords)
                            new_t_polygon = Polygon(t_polygon_coords,
                                                    t_polygon.interiors)
                            df.loc[df['osgb'] == t, 'sa_polygon'] = dumps(
                                new_t_polygon, rounding_precision=2)
        return df

    while simplify_polygon_no > 0:
        df = polygon_within_hole(df)
        df = polygon_simplify(df)
        df = df.loc[~df['sa_polygon'].isin(
            [False])].reset_index(drop=True)
        df = polygon_buffer(df)
        df = polygon_tolerance(df)
        simplify_polygon_no = df['sa_polygon_simplify'].sum()
    df = df.drop(['sa_polygon_simplify',
                  'sa_polygon_within_hole'], axis=1)
    return df

# END OF FUNCTION  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


def collinear_exterior(df):

    def collinear_points_list(objects_list):
        coll_list = list()
        if objects_list.geom_type in ['MultiLineString',
                                      'GeometryCollection']:
            for item in objects_list:
                coll_points = coollinear_points(list(item.coords))
                if coll_points:
                    coll_list.append(coll_points)
        elif objects_list.geom_type == 'LineString':
            coll_points = coollinear_points(list(objects_list.coords))
            if coll_points:
                coll_list.append(coll_points)
        collinear_points_list = list()
        for item in coll_list:
            for i in item:
                collinear_points_list.append(i)
        return collinear_points_list

    def coollinear_points(coord_list):

        def check_collinearity(f, m, l):
            if Polygon([f, m, l]).area <= 1e-9:
                return True
            else:
                return False

        removed_coll = list()
        if len(coord_list) >= 3:
            for i in range(len(coord_list) - 2):
                first = coord_list[i]
                middle = coord_list[i + 1]
                last = coord_list[i + 2]
                if check_collinearity(first, middle, last):
                    removed_coll.append(coord_list[i + 1])
        return removed_coll

    def update_polygon(polygon, points_to_remove):
        outer_ring = list(polygon.exterior.coords)
        new_outer_ring = remove_items_from_list(
            outer_ring, points_to_remove)
        new_inner_rings = list()
        if polygon.interiors:
            for item in polygon.interiors:
                inner_ring = list(item.coords)
                new_inner_ring = remove_items_from_list(inner_ring,
                                                        points_to_remove)
                new_inner_rings.append(new_inner_ring)
        new_polygon = Polygon(new_outer_ring, new_inner_rings)
        return new_polygon

    def remove_items_from_list(coords, items):
        if coords[0] == coords[-1]:
            for i in items:
                coords = [x for x in coords if x != i]
            if coords[0] != coords[-1]:
                coords.append(coords[0])
        else:
            for i in items:
                coords = [x for x in coords if x != i]
        return coords

    def update_exposed(exposed_ring, points_to_remove):
        if exposed_ring.geom_type == 'MultiLineString':
            new_ms = list()
            for item in exposed_ring:
                new_item = remove_items_from_list(list(item.coords),
                                                  points_to_remove)
                if len(new_item) > 1:
                    new_ms.append(new_item)
            if len(new_ms) > 1:
                new_exposed_ring = MultiLineString(new_ms)
            elif len(new_ms) == 1:
                new_exposed_ring = LineString(new_ms[0])
            else:
                new_exposed_ring = loads('GEOMETRYCOLLECTION EMPTY')
        elif exposed_ring.geom_type == 'LineString':
            new_item = remove_items_from_list(list(exposed_ring.coords),
                                              points_to_remove)
            if len(new_item) > 1:
                new_exposed_ring = LineString(new_item)
            else:
                new_exposed_ring = loads('GEOMETRYCOLLECTION EMPTY')
        else:
            new_exposed_ring = loads('GEOMETRYCOLLECTION EMPTY')
        return new_exposed_ring

    def remove_coollinear_points_horizontal(polygon):
        coll_list = list()
        o_r = LineString(polygon.exterior)
        i_r = MultiLineString(polygon.interiors)
        t_t = unary_union((o_r, i_r))
        if t_t.geom_type == 'MultiLineString':
            for item in t_t:
                coords = list(item.coords)
                coords.append(coords[1])
                coll_points = coollinear_points(coords)
                if coll_points:
                    coll_list.append(coll_points)
        elif t_t.geom_type == 'LineString':
            coords = list(t_t.coords)
            coords.append(coords[1])
            coll_points = coollinear_points(coords)
            if coll_points:
                coll_list.append(coll_points)
        collinear_points_list = list()
        for item in coll_list:
            for i in item:
                collinear_points_list.append(i)
        new_polygon = update_polygon(polygon, collinear_points_list)
        return new_polygon

    for row in df.itertuples():
        osgb_touching = literal_eval(row.sa_simplified_touching)
        polygon = loads(row.sa_polygon)
        osgb = row.osgb
        if osgb_touching:
            for t in osgb_touching:
                t_polygon = loads(
                    df.loc[df['osgb'] == t, 'sa_polygon'].values[0])
                partition = polygon.intersection(t_polygon)
                if partition.geom_type == 'MultiLineString':
                    partition = linemerge(partition)
                partition_collinear_points = collinear_points_list(
                    partition)
                if partition_collinear_points:
                    polygon = update_polygon(
                        polygon, partition_collinear_points)
                    t_polygon = update_polygon(
                        t_polygon, partition_collinear_points)
                    df.loc[df['osgb'] == t, 'sa_polygon'] = dumps(
                        t_polygon, rounding_precision=2)
                    df.loc[df['osgb'] == osgb, 'sa_polygon'] = dumps(
                        polygon, rounding_precision=2)

    for row in df.itertuples():
        osgb_touching = literal_eval(row.sa_simplified_touching)
        polygon = loads(row.sa_polygon)
        osgb = row.osgb
        if osgb_touching:
            outer_ring = LineString(polygon.exterior)
            inner_ring = MultiLineString(polygon.interiors)
            exposed = unary_union((outer_ring, inner_ring))
            for t in osgb_touching:
                t_polygon = loads(
                    df.loc[df['osgb'] == t, 'sa_polygon'].values[0])
                exposed -= polygon.intersection(t_polygon)
            exposed_collinear_points = collinear_points_list(exposed)
            if exposed_collinear_points:
                exposed = update_exposed(exposed, exposed_collinear_points)
                polygon = update_polygon(polygon, exposed_collinear_points)
            horizontal = remove_coollinear_points_horizontal(polygon)
        else:
            polygon = remove_coollinear_points_horizontal(polygon)
            horizontal = polygon
            outer_ring = LineString(polygon.exterior)
            inner_ring = MultiLineString(polygon.interiors)
            exposed = unary_union((outer_ring, inner_ring))

        df.loc[df['osgb'] == osgb, 'sa_polygon_exposed_wall'] = dumps(
            exposed, rounding_precision=2)
        df.loc[df['osgb'] == osgb, 'sa_polygon'] = dumps(
            polygon, rounding_precision=2)
        df.loc[df['osgb'] == osgb, 'sa_polygon_horizontal'] = dumps(
            horizontal, rounding_precision=2)
    return df

# END OF FUNCTION  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


if __name__ == '__main__':
    main()
