"""
Polygons for Cugir (RO), Metropolitan City of Milan (IT), London (UK,
the three boroughs Camden, Lambeth, and Westminster), Braga (PT), Riga (LV),
Kozani (GR), and Zaragoza (ES).
"""

import geopandas as gpd

FOLDERPATH_IN = "./data/raw/city_boundaries/"
FOLDERPATH_OUT = "./data/processed/0_cities_polygons/"
CITIES_RAW = [ # Cities given by PoliMi
    "Braga",
    "Camden",
    "Cugir",
    "Lambeth",
    "Milan_metropolitan",
    "Riga",
    "Westminster"
]
# Kozani given by municipality
# Zaragoza manually drawn within ring road

if __name__ == "__main__":
    for cityname in CITIES_RAW:
        if cityname == "Milan_metropolitan":
           poly_city = gpd.read_file(FOLDERPATH_IN + "Milano.shp")
           poly_all = gpd.read_file(FOLDERPATH_IN + "Milano_CMMI_province.shp")
           poly = poly_all.difference(poly_city)
        elif cityname == "Riga":
            poly = gpd.read_file(FOLDERPATH_IN + cityname + ".shp")
            poly = poly.polygonize()
        else:
            poly = gpd.read_file(FOLDERPATH_IN + cityname + ".shp")
        poly = poly.to_crs(epsg=4326)
        poly = gpd.GeoDataFrame(geometry=[poly.union_all()], crs="epsg:4326")
        poly.to_file(FOLDERPATH_OUT + cityname + ".gpkg")