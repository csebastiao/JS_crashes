"""Process features for selected cities."""


import os
import numpy as np
import geopandas as gpd
import shapely
import tqdm
import pandas as pd
from B_get_graph_raw import FOLDERPATH_CITIES, CITIES


def sort_values(row):
    """Sort values from the AMENITIES_DICT to a list of types."""
    val = []
    x = row.copy()
    for key in [
        "public_transport",
        "highway",
        "leisure",
        "amenity",
        "place",
        "shop",
        "building",
    ]:
        if key not in x:
            x[key] = np.nan
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
    elif not pd.isna(x["shop"]):
        val += ["shop"]
    if (x["amenity"] == "parking" or x["building"] == "parking") and pd.isna(x["shop"]):
        val += ["parking"]
    if x["amenity"] == "bicycle_parking" and x["highway"] != "crossing":
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

RECOMPUTE = True
BUFFER_DUPLICATE_LS = (
    8  # Buffer in meter to find duplicate amenities between points and linestrings
)


if __name__ == "__main__":
    for cityname in tqdm.tqdm(CITIES):
        outfolder = FOLDERPATH_CITIES + cityname + "/"
        if (os.path.exists(outfolder + cityname + "_features_3_dense.gpkg") and RECOMPUTE) or (not os.path.exists(outfolder + cityname + "_features_3_dense.gpkg")):
            print(cityname)
            gdf = gpd.read_file(outfolder + cityname + "_features_0_raw.gpkg")
            gdf = gdf.set_index("id")
            proj_crs = gdf.estimate_utm_crs()
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
            gdf.to_file(outfolder + cityname + "_features_1_classified.gpkg", index=True, overwrite=True)
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
            gdf_cleaned.to_file(outfolder + cityname + "_features_2_classified_wols.gpkg", index=True, overwrite=True)
            # Keep only important attributes to create lighter file
            gdf_simple = gdf_cleaned[["element", "type", "geometry"]].copy()
            vals = []
            # Simplify OSMID by putting first capitalized letter of type and numbers
            for ind, row in gdf_simple.iterrows():
                vals.append(row.element[0].upper() + str(ind))
            gdf_simple.loc[:, "osmid"] = vals
            gdf_simple = gdf_simple.set_index("osmid")
            gdf_simple = gdf_simple.drop("element", axis=1)
            gdf_simple.to_file(outfolder + cityname + "_features_3_dense.gpkg", index=True, overwrite=True)