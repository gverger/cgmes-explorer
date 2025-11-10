from datetime import datetime
from pathlib import Path
import pickle
import dash
import dash_cytoscape as cyto
from dash import Input, Output, html
from loguru import logger

import cgmes
import graphs

grid = "small"
grid = "large"
# grid = "elia"
max_nodes_one_way = 1000


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


def load_elements():
    start = datetime.now()
    pickle_filename = f"{grid}.pickle"
    if grid == "small":
        graph = load_cached(pickle_filename, "./samples/smallgrid")

        identifier = graph.identifier_for(
            "20171002T0930Z_BE_EQ_2.xml", "_17086487-56ba-4979-b8de-064025a6b4da"
        )
    elif grid == "elia":
        graph = load_cached(pickle_filename, "./samples/elia")

        identifier = graph.identifier_for(
            # "20250825T1130Z_1D_ELIA_EQ_000.xml",
            # "_d68b6a7e-09cd-e6e3-9d08-ec5501d60acf"
            # "20250825T1130Z_ENTSO-E_EQ_BD_000.xml",
            # "_b8e17237e0ca4fca9e4e285b80ab30d0",
            "20250825T1130Z_1D_ELIA_EQ_000(20).xml",
            "_9e536b97-dd05-1718-ce43-815b1f7ffc82",
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

    all = [
        identifier.split(":")[1]
        for identifier in set(
            [identifier]
            + graph.descendants(identifier, depth=1000, max_seen=max_nodes_one_way)
            + graph.ascendants(identifier, depth=1000, max_seen=max_nodes_one_way)
        )
    ]
    logger.info(f"found {len(all)} nodes")
    logger.info(all)

    logger.info("getting properties...")
    nodes = {nid: graph.properties(":" + nid) for nid in all}
    logger.info("done visu")
    # titles = {nid: f"{graphs.node_details(nid, nodes[nid])}" for nid in nodes}

    elements = []
    for identifier, n in nodes.items():
        details = graphs.node_details(graph, n)
        logger.info("{}:\n n={}\ndetails={}", identifier, n, details)
        node = dict(
            data=dict(
                id=identifier.split(":")[-1],
                label=f"{details.name} [{details.type}]",
                description=f"{details}",
            )
        )
        elements.append(node)

        for c in n.children:
            if n.children[c].split(":")[1] not in all:
                continue
            elements.append(
                dict(
                    data=dict(
                        source=identifier,
                        target=n.children[c].split(":")[-1],
                    )
                )
            )

    return elements


def run():
    elements = load_elements()
    cyto.load_extra_layouts()

    app = dash.Dash(__name__)

    @app.callback(Output("output", "children"), Input("graph", "tapNode"))
    def on_hover(node):
        if node:
            return dash.html.Pre(
                node["data"]["description"],
                style={
                    "background-color": "white",
                    "border": 1,
                    "z-index": 10,
                    "position": "absolute",
                    "padding": "1em",
                },
            )

    app.layout = html.Div(
        [
            cyto.Cytoscape(
                id="graph",
                # layout={"name": "dagre"},
                layout={"name": "cose-bilkent"},
                # style={"width": "100%", "height": "1000px"},
                style={
                    "position": "absolute",
                    "width": "100%",
                    "height": "100%",
                    "z-index": 1,
                },
                elements=elements,
                stylesheet=[
                    {
                        "selector": "edge",
                        "style": {
                            "curve-style": "bezier",
                            "target-arrow-shape": "triangle",
                        },
                    },
                    {
                        "selector": "node",
                        "style": {
                            "label": "data(label)",
                        },
                    }
                ],
                responsive=True,
                boxSelectionEnabled=True,
            ),
            html.Div(id="output"),
        ]
    )

    app.run(debug=True, use_reloader=False)
