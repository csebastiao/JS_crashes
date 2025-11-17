"""Compute centrality metrics on the network for selected cities. Optional, as very slow."""

import os
import osmnx as ox
import tqdm
import igraph as ig
import numpy as np
from B_get_graph_raw import FOLDERPATH_CITIES, CITIES

RECOMPUTE = False

if __name__ == "__main__":
    #TODO add recompute
    for cityname in tqdm.tqdm(CITIES):
        outfolder = FOLDERPATH_CITIES + cityname + "/"
        if (os.path.exists(outfolder + cityname + "_graph_3_metrics.graphml") and RECOMPUTE) or (not os.path.exists(outfolder + cityname + "_graph_3_metrics.graphml")):
            print(cityname)
            G = ox.load_graphml(outfolder + cityname + "_graph_2_dense.graphml")
            G_ig = ig.Graph.from_networkx(G)
            bet_length = G_ig.edge_betweenness(directed=True, weights="length")
            G_ig.es["edge_betweenness_centrality_length"] = np.array(bet_length) / (
                len(G.edges) * (len(G.edges) - 1)
            )
            bet_time = G_ig.edge_betweenness(directed=True, weights="travel_time")
            G_ig.es["edge_betweenness_centrality_time"] = np.array(bet_time) / (
                len(G.edges) * (len(G.edges) - 1)
            )
            G = G_ig.to_networkx()
            ox.save_graphml(G, outfolder + cityname + "_graph_3_metrics.graphml")
            ox.save_graph_geopackage(G, outfolder + cityname + "_graph_3_metrics.gpkg")