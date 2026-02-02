"""
Polygons for Cugir (RO), Metropolitan City of Milan (IT), London (UK,
the three boroughs Camden, Lambeth, and Westminster), Braga (PT), Riga (LV),
Kozani (GR), and Zaragoza (ES).
"""

import geopandas as gpd
import osmnx as ox
import shapely

FOLDERPATH_IN = "./data/raw/city_boundaries/"
FOLDERPATH_OUT = "./data/processed/1_cities_boundaries/"
CITIES_RAW = [ # Cities given by PoliMi
    "Braga",
    "Camden", # Ignored because have the true file from PoliMi
    "Cugir",
    "Lambeth", # Ignored because have the true file from PoliMi
    "Milan_metropolitan", # Ignored because have the true file from PoliMi
    "Riga", #
    "Westminster", # Ignored because have the true file from PoliMi
    "Kozani", # Ignored because have the true file from Tredit
    "Zaragoza",
]
COUNTRYNAMES = [
    "Portugal",
    "United Kingdom",
    "Romania",
    "United Kingdom",
    "Italy",
    "Latvia",
    "United Kingdom",
    "Greece",
    "Spain",
]
# Kozani given by municipality
# Zaragoza manually drawn within ring road

if __name__ == "__main__":
    for idx, cityname in enumerate(CITIES_RAW):
        if cityname == "Milan_metropolitan":
           poly_city = gpd.read_file(FOLDERPATH_IN + "Milano.shp")
           poly_all = gpd.read_file(FOLDERPATH_IN + "Milano_CMMI_province.shp")
           poly = poly_all.difference(poly_city)
        elif cityname == "Kozani":
            poly = gpd.read_file(FOLDERPATH_IN + f"{cityname}.shp")
            poly.geometry = [shapely.Polygon(poly.geometry[0].coords[:])]
        elif cityname in ["Camden", "Lambeth", "Westminster"]:
            poly = gpd.read_file(FOLDERPATH_IN + f"{cityname}.shp")
        else:
            poly = ox.geocode_to_gdf(f"{cityname}, {COUNTRYNAMES[idx]}")
        poly = poly.to_crs(epsg=4326)
        poly = gpd.GeoDataFrame(geometry=[poly.union_all()], crs="epsg:4326")
        poly.to_file(FOLDERPATH_OUT + cityname + ".gpkg")