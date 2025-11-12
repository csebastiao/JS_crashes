"""Get data from OpenStreetMap on road features and amenities that could impact crashes in the city of Milan."""

import geopandas as gpd
import igraph as ig
import numpy as np
import osmnx as ox
import pandas as pd
import shapely


def sort_values(x):
    """Sort values from the AMENITIES_DICT to a list of types."""
    val = []
    if x["public_transport"] == "platform" or x["highway"] == "bus_stop":
        val += ["public_transport_platform"]
    if x["leisure"] in ["park", "garden"] and x["amenity"] != "parking":
        val += ["green_area"]
    if (
        (x["place"] == "square" or x["amenity"] == "marketplace")
        and (x["leisure"] not in ["park", "garden"])
        and (x["amenity"] != "parking")
    ):
        val += ["public_square"]
    if not pd.isna(x["shop"]):
        val += ["shop"]
    if (x["amenity"] == "parking" or x["building"] == "parking") and pd.isna(x["shop"]):
        val += ["parking"]
    if x["amenity"] == "bicycle_parking":
        val += ["bicycle_parking"]
    if x["highway"] in [
        "crossing",
        "cyclist_waiting_aid",
        "traffic_signals",
        "street_lamp",
        "traffic_mirror",
    ]:
        val += [x["highway"]]
    if len(val) < 1:
        val += [None]
    return val


FALLBACK_SPEED = 50  # Speed by default if no other computation found
BUFFER_DUPLICATE_LS = (
    8  # Buffer in meter to find duplicate amenities between points and linestrings
)
BUFFER_NEARBY = 15  # Buffer in meter to know if a polygon amenity is near a road
USEFUL_TAGS = [
    "parking:left",
    "parking:right",
    "cycleway",
    "footway",
]  # Additional tags to extract for the road network
AMENITIES_DICT = {  # List of amenities from tags and values to extract
    "public_transport": ["platform"],
    "highway": [
        "crossing",
        "cyclist_waiting_aid",
        "traffic_signals",
        "street_lamp",
        "traffic_mirror",
        "bus_stop",
    ],
    "amenity": ["bicycle_parking", "parking", "marketplace"],
    "building": ["parking"],
    "place": ["square"],
    "leisure": ["park", "garden"],
    "shop": True,
    "osmid": True,
}
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

# TODO make bikeways and footways attribute from highway tags

if __name__ == "__main__":
    ox.settings.useful_tags_way += USEFUL_TAGS
    # Shapefile is given
    milano_poly = gpd.read_file("./data/raw/city_boundaries/Milano.shp")
    proj_crs = milano_poly.crs
    milano_poly.to_crs(epsg=4326, inplace=True)
    # Take only drivable roads for crashes
    G = ox.graph_from_polygon(
        milano_poly.geometry[0], network_type="all", simplify=False
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
    ox.save_graphml(G, "./data/processed/Milan/Milan_graph_0_raw.graphml")
    ox.save_graph_geopackage(G, "../data/processed/Milan/Milan_graph_0_raw.gpkg")
    # Extract amenities in the area of study
    gdf = ox.features_from_polygon(
        milano_poly.geometry[0],
        tags=AMENITIES_DICT,
    )
    gdf.to_file("./data/processed/Milan/Milan_features_0_raw.gpkg")
    # Simplify in single attribute the different kind of amenities
    vals = []
    for ind, row in gdf.iterrows():
        vals.append(sort_values(row))
    gdf["type"] = vals
    # Check if an amenity has two type, which should not be the case here
    errors = gdf[
        gdf["type"].apply(lambda x: True if len(str(x).split(",")) > 1 else False)
    ]
    if len(errors) > 0:
        print("Some errors are found!")
        for i in range(len(errors)):
            print(
                errors.index[i],
                [
                    val
                    for val in errors.iloc[i].values
                    if (
                        isinstance(val, shapely.Geometry)
                        or isinstance(val, list)
                        or isinstance(val, str)
                    )
                ],
            )
    gdf["type"] = gdf["type"].apply(lambda x: x[0])
    gdf.to_file("./data/processed/Milan/Milan_features_1_classified.gpkg")
    gdf_cleaned = gdf.copy()
    gdf_po = gdf[
        gdf.geometry.apply(lambda x: True if isinstance(x, shapely.Point) else False)
    ]
    gdf_po = gdf_po.to_crs(proj_crs)
    gdf_ls = gdf[
        gdf.geometry.apply(
            lambda x: True if isinstance(x, shapely.LineString) else False
        )
    ]
    gdf_ls = gdf_ls.to_crs(proj_crs)  # Project to use buffer
    gdf_ls.geometry = gdf_ls.buffer(BUFFER_DUPLICATE_LS)
    # Find linestrings near a point of the same type to remove duplicates
    duplicates = gpd.sjoin(
        gdf_ls, gdf_po, how="inner", predicate="intersects", on_attribute="type"
    )
    gdf_cleaned = gdf_cleaned.drop(duplicates.index.values)
    # For other linestrings, take middle point
    gdf_cleaned.geometry = gdf_cleaned.geometry.apply(
        lambda x: x.interpolate(0.5, normalized=True)
        if isinstance(x, shapely.LineString)
        else x
    )
    gdf_cleaned.to_file("./data/processed/Milan/Milan_features_2_classified_wols.gpkg")
    # Keep only important attributes to create lighter file
    gdf_simple = gdf_cleaned[["type", "geometry"]].copy()
    vals = []
    # Simplify OSMID by putting first capitalized letter of type and numbers
    for ind, row in gdf_simple.iterrows():
        vals.append(ind[0][0].upper() + str(ind[1]))
    gdf_simple["osmid"] = vals
    gdf_simple = gdf_simple.set_index("osmid")
    gdf_simple.to_file("./data/processed/Milan/Milan_features_3_dense.gpkg")
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
    left_parking = [
        True if (not pd.isna(val) and val != "no") else False
        for val in gdf_edges["parking:left"].values
    ]
    right_parking = [
        True if (not pd.isna(val) and val != "no") else False
        for val in gdf_edges["parking:right"].values
    ]
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
    ox.save_graphml(G, "./data/processed/Milan/Milan_graph_1_all.graphml")
    ox.save_graph_geopackage(G, "./data/processed/Milan/Milan_graph_1_all.gpkg")
    # Remove useless attributes
    gdf_edges_simplified = gdf_edges.drop(
        [
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
        ],
        axis=1,
    )
    gdf_nodes_simplified = gdf_nodes.drop(
        ["highway", "ref", "junction", "railway"], axis=1
    )
    G = ox.graph_from_gdfs(
        gdf_nodes=gdf_nodes_simplified,
        gdf_edges=gdf_edges_simplified,
        graph_attrs=G.graph,
    )
    ox.save_graphml(G, "./data/processed/Milan/Milan_graph_2_dense.graphml")
    ox.save_graph_geopackage(G, "./data/processed/Milan/Milan_graph_2_dense.gpkg")
    # Use igraph to compute more quickly edge betweenness
    # Careful, very slow, so not great on small computer
    # G_ig = ig.Graph.from_networkx(G)
    # bet_length = G_ig.edge_betweenness(directed=True, weights="length")
    # G_ig.es["edge_betweenness_centrality_length"] = np.array(bet_length) / (
    #     len(G.edges) * (len(G.edges) - 1)
    # )
    # bet_time = G_ig.edge_betweenness(directed=True, weights="travel_time")
    # G_ig.es["edge_betweenness_centrality_time"] = np.array(bet_time) / (
    #     len(G.edges) * (len(G.edges) - 1)
    # )
    # G = G_ig.to_networkx()
    ox.save_graphml(G, "./data/processed/Milan/Milan_graph_3_metrics.graphml")
    ox.save_graph_geopackage(G, "./data/processed/Milan/Milan_graph_3_metrics.gpkg")
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
    # TODO fix problem
    duplicates = nf[pd.notna(nf["origin_right"])].index.values
    gdf_nodes_simplified_curated = gdf_nodes_simplified.drop(duplicates, axis=0)
    # Keep only nodes not already in amenities and that are intersections
    gdf_nodes_simplified_curated = gdf_nodes_simplified_curated[
        gdf_nodes_simplified_curated["intersection"].values
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
    joined.to_file("./data/processed/Milan/Milan_all.gpkg")
