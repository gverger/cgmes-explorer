from datetime import datetime
from pathlib import Path
import pickle
import random
import dash
import dash_cytoscape as cyto
from dash import Input, Output, State, dcc, html
from loguru import logger

import cgmes
import graphs
from visu import icons

grid = "small"
# grid = "large"
# grid = "elia"
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


def first_identifier(grid: str) -> str:
    if grid == "small":
        identifier = "_17086487-56ba-4979-b8de-064025a6b4da"
    elif grid == "elia":
        # identifier = "_d68b6a7e-09cd-e6e3-9d08-ec5501d60acf"
        # identifier = "_b8e17237e0ca4fca9e4e285b80ab30d0",
        identifier = "_9e536b97-dd05-1718-ce43-815b1f7ffc82"
    else:
        identifier = "_426798065_ACLS"
        # identifier = "_63_BV",

    return identifier


def load_graph() -> cgmes.Graph:
    start = datetime.now()
    pickle_filename = f"{grid}.pickle"
    if grid == "small":
        graph = load_cached(pickle_filename, "./samples/smallgrid")

        # identifier = graph.identifier_for(
        #     "20171002T0930Z_BE_EQ_2.xml", "_17086487-56ba-4979-b8de-064025a6b4da"
        # )
    elif grid == "elia":
        graph = load_cached(pickle_filename, "./samples/elia")

        # identifier = graph.identifier_for(
        #     # "20250825T1130Z_1D_ELIA_EQ_000.xml",
        #     # "_d68b6a7e-09cd-e6e3-9d08-ec5501d60acf"
        #     # "20250825T1130Z_ENTSO-E_EQ_BD_000.xml",
        #     # "_b8e17237e0ca4fca9e4e285b80ab30d0",
        #     "20250825T1130Z_1D_ELIA_EQ_000(20).xml",
        #     "_9e536b97-dd05-1718-ce43-815b1f7ffc82",
        # )
    else:
        graph = load_cached(pickle_filename, "./samples/realgrid")
        # identifier = graph.identifier_for(
        #     "CGMES_v2.4.15_RealGridTestConfiguration_EQ_V2.xml",
        #     "_426798065_ACLS",
        #     # "CGMES_v2.4.15_RealGridTestConfiguration_EQ_V2.xml", "_63_BV",
        # )
    stop = datetime.now()
    logger.info(f"graph loaded in {stop - start}")
    return graph


def load_elements(
    graph: cgmes.Graph,
    identifier: str,
    do_not_include: list[str] | None = None,
    depth=1000,
):
    do_not_include = do_not_include or []
    identifier = ":" + identifier
    all = [
        found.split(":")[1]
        for found in set(
            [identifier]
            + graph.descendants(identifier, depth=depth, max_seen=max_nodes_one_way)
            + graph.ascendants(identifier, depth=depth, max_seen=max_nodes_one_way)
        )
    ]
    logger.info(f"found {len(all)} nodes")
    logger.info(all)

    all = [i for i in all if i not in do_not_include]

    logger.info("getting properties...")
    nodes = {nid: graph.properties(":" + nid) for nid in all}
    logger.info("done visu")

    elements = []
    for identifier, n in nodes.items():
        details = graphs.node_details(graph, n)
        logger.info("{}:\n n={}\ndetails={}", identifier, n, details)
        node = {
            "data": dict(
                id=identifier.split(":")[-1],
                label=f"{details.name}\n[{details.type}]",
                description=f"{details}",
            ),
            "classes": details.type,
        }
        # if node["data"]["id"] not in do_not_include:
        elements.append(node)

        for c in n.children:
            childid = n.children[c].split(":")[1]
            if childid not in all:
                continue
            if node["data"]["id"] in do_not_include and childid in do_not_include:
                continue
            elements.append(dict(data=dict(source=identifier, target=childid)))

    return elements


def run():
    graph = load_graph()
    elements = load_elements(graph, first_identifier(grid))
    for e in elements:
        if "id" in e["data"]:
            e["position"] = {
                "x": random.randint(0, 1000),
                "y": random.randint(0, 1000),
            }

    cyto.load_extra_layouts()

    app = dash.Dash(__name__)

    state = {
        "loading_more": False,
        "clicked": "",
        "clicked_at": datetime.now(),
        "resetId": "",
    }

    @app.callback(Output("output", "children"), Input("graph", "selectedNodeData"))
    def on_hover(data):
        if data:
            return dash.html.Pre(
                data[0]["description"],
                style={
                    "background-color": "white",
                    "border": 1,
                    "z-index": 10,
                    "position": "absolute",
                    "padding": "1em",
                },
            )
        else:
            return ""

    @app.callback(Output("resetButton", "children"), Input("graph", "selectedNodeData"))
    def clickEmpty(data):
        if not data:
            state["resetId"] = ""
            return "Reset from start"
        state["resetId"] = data[0]["id"]
        return f"Reset exploration from {data[0]['label']}"

    @app.callback(
        Output("graph", "elements"),
        Input("graph", "tapNode"),
        Input("resetButton", "n_clicks"),
        Input("searchIdButton", "n_clicks"),
        State("searchId", "value"),
        State("graph", "elements"),
    )
    def on_click(node, resetButton, searchIdButton, searchId, elements):
        if dash.callback_context.triggered[0]["prop_id"] == "resetButton.n_clicks":
            if state["clicked"]:
                if state["resetId"]:
                    return load_elements(graph, state["resetId"])

            return load_elements(graph, first_identifier(grid))
        if dash.callback_context.triggered[0]["prop_id"] == "searchIdButton.n_clicks":
            return load_elements(graph, searchId.strip())

        if not node:
            state["clicked"] = ""
            return elements

        if (
            state["clicked"] != node["data"]["id"]
            or (datetime.now() - state["clicked_at"]).total_seconds() > 0.30
        ):
            state["clicked"] = node["data"]["id"]
            state["clicked_at"] = datetime.now()
            return elements

        if state["loading_more"]:
            return elements
        state["loading_more"] = True

        already_present = []
        for el in elements:
            if "id" in el["data"]:
                if el["data"]["id"] != node["data"]["id"]:
                    already_present.append(el["data"]["id"])

        new_elements = load_elements(
            graph, node["data"]["id"], do_not_include=already_present, depth=2
        )
        if new_elements:
            for n in new_elements:
                n["renderedPosition"] = node["renderedPosition"]
            new_elements.extend(elements)
            elements = new_elements
        state["loading_more"] = False

        return elements

    img_stylesheet = [
        {
            "selector": f"node.{t}",
            "style": {
                "border-width": 0,
                "background-image": icons.images(t),
            },
        }
        for t in icons.Images
    ]

    cs = cyto.Cytoscape(
        id="graph",
        # layout={"name": "cose" },
        layout={"name": "cose-bilkent", "idealEdgeLength": 64, "randomize": False},
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
                    "text-valign": "bottom",
                    "text-halign": "center",
                    "text-margin-y": 3,
                    "font-size": 8,
                    "text-wrap": "wrap",
                    "text-background-color": "white",
                    "text-background-opacity": 0.5,
                    "text-background-padding": 2,
                    # "text-opacity": 255,
                    "shape": "rectangle",
                    "background-color": "white",
                    "overlay-color": "blue",
                    # "border-width": 1,
                    # "border-color": "blue",
                    # "outline-width": 2,
                    "border-width": 1,
                    "background-fit": "cover",
                    "padding": "5px",
                },
            },
            {
                "selector": "node:selected",
                "style": {
                    "border-color": "blue",
                    "border-width": 3,
                },
            },
        ]
        + img_stylesheet,
        responsive=True,
        boxSelectionEnabled=True,
        wheelSensitivity=0.3,
    )

    app.layout = html.Div(
        [
            html.Div(
                [
                    html.Button("Click here!", id="resetButton"),
                    dcc.Input(
                        id="searchId", type="text", placeholder="RDFID", size="20em"
                    ),
                    html.Button("Go to ID", id="searchIdButton"),
                ]
            ),
            cs,
            html.Div(id="output"),
        ]
    )

    app.run(debug=True)  # , use_reloader=False)
