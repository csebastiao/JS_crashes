"""Merge graphs and features for selected cities."""

import os
import geopandas as gpd
import osmnx as ox
import tqdm
import pandas as pd
from B_get_graph_raw import FOLDERPATH_CITIES, CITIES
import shapely

# Can be eitehr from script E (2_dense) or F (3_metrics)
SUFFIX_GRAPH = "2_dense"
RECOMPUTE = False


if __name__ == "__main__":
    #TODO add recompute
    for cityname in tqdm.tqdm(CITIES):
        outfolder = FOLDERPATH_CITIES + cityname + "/"
        if (os.path.exists(outfolder + cityname + "_all.gpkg") and RECOMPUTE) or (not os.path.exists(outfolder + cityname + "_all.gpkg")):
            print(cityname)
            G = ox.load_graphml(outfolder + cityname + "_graph_" + SUFFIX_GRAPH + ".graphml")
            gdf_nodes, gdf_edges = ox.graph_to_gdfs(G, nodes=True, edges=True)
            gdf_simple = gpd.read_file(outfolder + cityname + "_features_3_dense.gpkg")
            gdf_simple = gdf_simple.set_index("osmid")
            hnodes, hedges = ox.graph_to_gdfs(G)
            gdf_edges_simplified = hedges.copy()
            # Homogeneize osmid between amenities and roads
            gdf_edges_simplified["osmid"] = hedges["osmid"].apply(
                lambda x: "W" + str(x)
                if not isinstance(x, list)
                else ["W" + str(val) for val in x]
            )
            gdf_edges_simplified = hedges.set_index(keys="osmid")
            # gdf_edges_simplified = gdf_edges_simplified.drop("_igraph_index", axis=1)
            gdf_nodes_simplified = hnodes.copy()
            gdf_nodes_simplified.index = ["N" + str(x) for x in gdf_nodes_simplified.index]
            # gdf_nodes_simplified = gdf_nodes_simplified.drop("_igraph_index", axis=1)
            # Get origin for all kind of geodata to join them all
            gdf_edges_simplified["origin"] = "road"
            gdf_nodes_simplified["origin"] = "node"
            gdf_simple["origin"] = "features"
            # Find nodes that are both in the amenities and the street network to remove them
            nf = gpd.sjoin(
                gdf_simple[
                    gdf_simple.geometry.apply(
                        lambda x: True if isinstance(x, shapely.Point) else False
                    )
                ],
                gdf_nodes_simplified,
                how="left",
                predicate="intersects",
            )
            duplicates = nf[pd.notna(nf["origin_right"])].index.values
            indlist = list(gdf_nodes_simplified.index)
            duplicates = [val for val in duplicates if val in indlist]
            gdf_nodes_simplified_curated = gdf_nodes_simplified.drop(duplicates, axis=0)
            # Keep only nodes not already in amenities and that are intersections
            gdf_nodes_simplified_curated = gdf_nodes_simplified_curated[
                [bool(val) for val in gdf_nodes_simplified_curated["intersection"].values]
            ]
            gdf_nodes_simplified_curated["type"] = "intersection"
            gdf_simple_curated = gdf_simple.copy()
            gdf_simple_curated["origin"] = [
                [row["origin"], "node"] if ind in duplicates else row["origin"]
                for ind, row in gdf_simple_curated.iterrows()
            ]
            # Remove duplicate features having the same geometry and type
            gdf_simple_curated = gdf_simple_curated.drop_duplicates(
                subset=["geometry", "type"], keep="first"
            )
            # Join roads, intersections, and amenities into a single file
            joined = pd.concat(
                [gdf_simple_curated, gdf_edges_simplified, gdf_nodes_simplified_curated]
            )
            joined.to_file(outfolder + cityname + "_all.gpkg")
