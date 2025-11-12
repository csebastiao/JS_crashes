"""Get raw graphs from OpenStreetMap in selected cities."""

import geopandas as gpd
import osmnx as ox
import tqdm
import os

RECOMPUTE = False
FALLBACK_SPEED = 50  # Speed by default if no other computation found
BUFFER_NEARBY = 15  # Buffer in meter to know if a polygon amenity is near a road
USEFUL_TAGS = [
    "parking:left",
    "parking:right",
    "cycleway",
    "footway",
]  # Additional tags to extract for the road network
FOLDERPATH_POLY = "./data/processed/0_cities_polygons/"
FOLDERPATH_CITIES = "./data/processed/"
CITIES = [
    "Braga",
    "Camden",
    "Cugir",
    "Kozani",
    "Lambeth",
    "Milan_metropolitan",
    "Riga",
    "Westminster",
    "Zaragoza",
]
NETWORK_TYPE = "all"


if __name__ == "__main__":
    ox.settings.useful_tags_way += USEFUL_TAGS
    for cityname in tqdm.tqdm(CITIES):
        #TODO fix for Milan metropolitan because multipolygon and not polygon
        outfolder = FOLDERPATH_CITIES + cityname + "/"
        if (os.path.exists(outfolder + cityname + "_graph_0_raw.graphml") and RECOMPUTE) or (not os.path.exists(outfolder + cityname + "_graph_0_raw.graphml")):
            if not os.path.exists(outfolder):
                os.makedirs(outfolder)
            poly = gpd.read_file(FOLDERPATH_POLY + cityname + ".gpkg")
            G = ox.graph_from_polygon(
                poly.geometry[0], network_type=NETWORK_TYPE, simplify=False
            )
            # Simplify while discriminate for relevant attributes
            G = ox.simplify_graph(
                G, edge_attrs_differ=["highway", "parking:left", "parking:right", "maxspeed"]
            )
            # Simplify footways' values in highway tag
            for e in G.edges:
                if G.edges[e]["highway"] in [
                    "corridor",
                    "bridleway",
                    "pedestrian",
                    "path",
                    "steps",
                ]:
                    G.edges[e]["highway"] = "footway"
            # Add presence of cycling infrastructure boolean
            for e in G.edges:
                if G.edges[e]["highway"] == "cycleway":
                    G.edges[e]["cycling_infrastructure"] = True
                elif "cycleway" in G.edges[e]:
                    if G.edges[e]["cycleway"] != "no":
                        G.edges[e]["cycling_infrastructure"] = True
                else:
                    G.edges[e]["cycling_infrastructure"] = False
            # Add presence of pedestrian infrastructure boolean
            for e in G.edges:
                if G.edges[e]["highway"] == "footway":
                    G.edges[e]["pedestrian_infrastructure"] = True
                elif "footway" in G.edges[e]:
                    if G.edges[e]["footway"] != "no":
                        G.edges[e]["pedestrian_infrastructure"] = True
                else:
                    G.edges[e]["pedestrian_infrastructure"] = False
            # Compute travel time to increase centrality of high speed roads
            # For maxspeed, compute average of roads with same highway attribute, else use fallback
            G = ox.add_edge_speeds(G, fallback=FALLBACK_SPEED)
            # Round estimated speed to have a realistic estimated speed
            for e in G.edges:
                G.edges[e]["speed_kph"] = int(round(G.edges[e]["speed_kph"], -1))
            G = ox.add_edge_travel_times(G)
            # Separate between intersections and other nodes, dead-ends and interstitial ones
            # From OSMnx simplification function
            for node in G.nodes:
                neighbors = set(list(G.predecessors(node)) + list(G.successors(node)))
                n = len(neighbors)
                d = G.degree(node)
                if node in neighbors:
                    G.nodes[node]["intersection"] = True
                    continue
                if G.out_degree(node) == 0 or G.in_degree(node) == 0:
                    G.nodes[node]["intersection"] = True
                    continue
                if not ((n == 2) and (d in {2, 4})):
                    if n == 1:
                        G.nodes[node]["intersection"] = False
                    else:
                        G.nodes[node]["intersection"] = True
                    continue
                G.nodes[node]["intersection"] = False
            gdf_nodes, gdf_edges = ox.graph_to_gdfs(G, nodes=True, edges=True)
            ox.save_graphml(G, outfolder + cityname + "_graph_0_raw.graphml")
            ox.save_graph_geopackage(G, outfolder + cityname + "_graph_0_raw.gpkg")