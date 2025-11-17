"""Get raw features from OpenStreetMap for selected cities."""

import geopandas as gpd
import osmnx as ox
import tqdm
import os
from B_get_graph_raw import FOLDERPATH_POLY, FOLDERPATH_CITIES, CITIES


RECOMPUTE = True
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


if __name__ == "__main__":
    ox.settings.requests_timeout = 1200
    for cityname in tqdm.tqdm(CITIES):
        outfolder = FOLDERPATH_CITIES + cityname + "/"
        if (os.path.exists(outfolder + cityname + "_features_0_raw.gpkg") and RECOMPUTE) or (not os.path.exists(outfolder + cityname + "_features_0_raw.gpkg")):
            print(cityname)
            poly = gpd.read_file(FOLDERPATH_POLY + cityname + ".gpkg")
            gdf = ox.features_from_polygon(
                poly.geometry[0],
                tags=AMENITIES_DICT,
            )
            if "FIXME" in gdf.columns:
                gdf = gdf.drop(columns="FIXME")
            gdf.to_file(outfolder + cityname + "_features_0_raw.gpkg", index=True)