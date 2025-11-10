import pickle
from datetime import datetime
from pathlib import Path

import networkx as nx
import pyvis.network as pvn
from loguru import logger

import cgmes
import graphs
import visu

grid = "small"
# grid = "large"
max_nodes_one_way = 100


def load_cached(pickle_filename, folder):
    if Path(pickle_filename).exists():
        logger.info("loading cached file")
        with open(pickle_filename, "rb") as file:
            return pickle.load(file)

    logger.info("loading folder")
    graph = cgmes.load_folder(folder)
    logger.info("saving to cache")
    with open(f"{grid}.pickle", "wb") as file:
        pickle.dump(graph, file)

    return graph


def main():
    start = datetime.now()
    pickle_filename = f"{grid}.pickle"
    if grid == "small":
        graph = load_cached(pickle_filename, "./samples/smallgrid")

        identifier = graph.identifier_for(
            "20171002T0930Z_BE_EQ_2.xml", "_17086487-56ba-4979-b8de-064025a6b4da"
        )
    else:
        graph = load_cached(pickle_filename, "./samples/realgrid")
        identifier = graph.identifier_for(
            "CGMES_v2.4.15_RealGridTestConfiguration_EQ_V2.xml",
            "_426798065_ACLS",
            # "CGMES_v2.4.15_RealGridTestConfiguration_EQ_V2.xml", "_63_BV",
        )
    stop = datetime.now()
    logger.info(f"graph loaded in {stop - start}")

    all = list(
        set(
            [identifier]
            + graph.descendants(identifier, depth=1000, max_seen=max_nodes_one_way)
            + graph.ascendants(identifier, depth=1000, max_seen=max_nodes_one_way)
        )
    )
    logger.info(f"found {len(all)} nodes")

    logger.info("getting properties...")
    nodes = {identifier: graph.properties(identifier) for identifier in all}
    logger.info("done")
    # titles = {nid: f"{graphs.node_details(nid, nodes[nid])}" for nid in nodes}

    g = nx.DiGraph()
    g.add_nodes_from(all)

    for identifier, n in nodes.items():
        # for p in n.props:
        #     g.nodes[identifier][p] = n.props[p]
        details = graphs.node_details(identifier, n)
        g.nodes[identifier]["title"] = f"{details}"
        g.nodes[identifier]["label"] = f"{details.name} [{details.type}]"
        logger.info("title = " + g.nodes[identifier]["title"])

        for c in n.children:
            if n.children[c] not in all:
                continue
            g.add_edge(identifier, n.children[c], rel=c)

    logger.info(f"{len(g.nodes)} nodes")

    logger.info("creating vizualisation graph")
    pg = pvn.Network(height="1000px", cdn_resources="in_line")
    # pg.barnes_hut()
    # pg.force_atlas_2based()
    pg.repulsion(central_gravity=0)
    pg.from_nx(g)
    pg.toggle_physics(True)
    pg.show_buttons()
    logger.info("creating html")
    # pg.show("test.html")
    pg.write_html("test.html")
    logger.info("exiting")


if __name__ == "__main__":
    # main()
    visu.run()
