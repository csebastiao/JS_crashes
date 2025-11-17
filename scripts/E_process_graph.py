"""Process graphs for selected cities."""

import os
import geopandas as gpd
import osmnx as ox
import tqdm
import pandas as pd
from B_get_graph_raw import FOLDERPATH_CITIES, CITIES
import shapely

RECOMPUTE = False
HIGHWAY_DICT = {  # Hierarchy in the road network
    "motorway": 1,
    "trunk": 2,
    "primary": 3,
    "secondary": 4,
    "tertiary": 5,
    "unclassified": 6,
    "residential": 7,
    "living_street": 7,
    "busway": 8,
    "bus_stop": 8,
    "service": 8,
    "services": 8,
    "track": 8,
    "emergency_bay": 8,
    "road": 8,
    "cycleway": 9,
    "footway": 10,
}
BUFFER_NEARBY = 15  # Buffer in meter to know if a polygon amenity is near a road


if __name__ == "__main__":
    for cityname in tqdm.tqdm(CITIES):
        outfolder = FOLDERPATH_CITIES + cityname + "/"
        if (os.path.exists(outfolder + cityname + "_graph_2_dense.graphml") and RECOMPUTE) or (not os.path.exists(outfolder + cityname + "_graph_2_dense.graphml")):
            print(cityname)
            G = ox.load_graphml(outfolder + cityname + "_graph_0_raw.graphml")
            gdf_nodes, gdf_edges = ox.graph_to_gdfs(G, nodes=True, edges=True)
            gdf_simple = gpd.read_file(outfolder + cityname + "_features_3_dense.gpkg")
            proj_crs = gdf_simple.estimate_utm_crs()
            gdf_simple_poly = gdf_simple[
                gdf_simple.geometry.apply(
                    lambda x: True
                    if isinstance(x, shapely.MultiPolygon) or isinstance(x, shapely.Polygon)
                    else False
                )
            ]
            # Divide MultiPolygons into multiple Polygon entries
            gdf_simple_poly_exploded = gdf_simple_poly.explode()
            gdf_simple_poly_exploded = gdf_simple_poly_exploded.to_crs(
                proj_crs
            )  # Project to use buffer
            gdf_simple_poly_exploded.geometry = gdf_simple_poly_exploded.buffer(BUFFER_NEARBY)
            gdf_edges = gdf_edges.to_crs(proj_crs)
            # Find roads nearby polygons
            res = gpd.sjoin(
                gdf_edges, gdf_simple_poly_exploded, how="left", predicate="intersects"
            )
            # Group the results to have a unique set of nearby amenities for each road
            grouped_res = res.groupby(["u", "v", "key"])["type"].agg(set)
            # Create boolean attribute to simplify search
            gdf_edges["near_parking"] = [
                True if "parking" in x else False for x in grouped_res.values
            ]
            gdf_edges["near_park"] = [
                True if "green_area" in x else False for x in grouped_res.values
            ]
            gdf_edges["near_square"] = [
                True if "public_square" in x else False for x in grouped_res.values
            ]
            # Merge left and right parking into a single street parking attribute
            if "parking:left" in gdf_edges:
                left_parking = [
                    True if (not pd.isna(val) and val != "no") else False
                    for val in gdf_edges["parking:left"].values
                ]
            else:
                left_parking = [False] * len(gdf_edges)
            if "parking:right" in gdf_edges:
                right_parking = [
                    True if (not pd.isna(val) and val != "no") else False
                    for val in gdf_edges["parking:right"].values
                ]
            else:
                right_parking = [False] * len(gdf_edges)
            gdf_edges["street_parking"] = [
                left or right for left, right in zip(left_parking, right_parking)
            ]
            # Simplify highway type into numbered hierarchy
            gdf_edges["hierarchy"] = gdf_edges["highway"]
            gdf_edges["hierarchy"] = gdf_edges["hierarchy"].apply(
                lambda x: x.removesuffix("_link")
            )
            gdf_edges["hierarchy"] = gdf_edges["hierarchy"].apply(
                lambda x: HIGHWAY_DICT[x] if x in HIGHWAY_DICT else 8
            )
            gdf_edges = gdf_edges.to_crs(epsg=4326)
            # Some nodes from the road also have traffic signals or crossings
            gdf_nodes["traffic_signals"] = [
                True if (isinstance(val, str) and "traffic_signals" in val) else False
                for val in gdf_nodes["highway"].values
            ]
            gdf_nodes["crossing"] = [
                True if (isinstance(val, str) and "crossing" in val) else False
                for val in gdf_nodes["highway"].values
            ]
            G = ox.graph_from_gdfs(
                gdf_nodes=gdf_nodes, gdf_edges=gdf_edges, graph_attrs=G.graph
            )
            ox.save_graphml(G, outfolder + cityname + "_graph_1_all.graphml")
            ox.save_graph_geopackage(G, outfolder + cityname + "_graph_1_all.gpkg")
            # Remove useless attributes
            for edge_col_to_drop in [
                    "lanes",
                    "junction",
                    "ref",
                    "bridge",
                    "tunnel",
                    "width",
                    "access",
                    "est_width",
                    "reversed",
                    "parking:right",
                    "parking:left",
                    "maxspeed",
            ]:
                if edge_col_to_drop in gdf_edges:
                    gdf_edges = gdf_edges.drop(
                        edge_col_to_drop,
                        axis=1,
                    )
            for node_col_to_drop in [
                "highway",
                "ref",
                "junction",
                "railway",
            ]:
                if node_col_to_drop in gdf_nodes:
                    gdf_nodes = gdf_nodes.drop(
                        node_col_to_drop, axis=1
                    )
            G = ox.graph_from_gdfs(
                gdf_nodes=gdf_nodes,
                gdf_edges=gdf_edges,
                graph_attrs=G.graph,
            )
            ox.save_graphml(G, outfolder + cityname + "_graph_2_dense.graphml")
            ox.save_graph_geopackage(G, outfolder + cityname + "_graph_2_dense.gpkg")
