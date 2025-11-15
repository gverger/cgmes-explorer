import pickle
from datetime import datetime
from pathlib import Path

import dash
import dash_cytoscape as cyto
import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, dcc, html
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
        identifier = "_87f7002b-056f-4a6a-a872-1744eea757e3"
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
    already_present: list[str] | None = None,
    depth=1000,
):
    already_present = already_present or []
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

    all = list(set(all + already_present))

    logger.info("getting properties...")
    nodes = {nid: graph.properties(":" + nid) for nid in all}
    logger.info("done visu")

    elements = []
    print(f"already_present = {already_present}")
    for identifier, n in nodes.items():
        nodeid = identifier.split(":")[-1]
        if identifier not in already_present:
            details = graphs.node_details(graph, n)
            logger.info("{}:\n n={}\ndetails={}", identifier, n, details)
            node = {
                "data": dict(
                    id=nodeid,
                    label=f"{details.name}\n[{details.type}]",
                    description=f"{details}",
                    type=details.type,
                ),
                "classes": details.type,
            }
            elements.append(node)

        for c in n.children:
            childid = c[1].split(":")[1]
            if childid not in all:
                continue
            if nodeid in already_present and childid in already_present:
                continue

            elements.append(dict(data=dict(source=nodeid, target=childid)))

    return elements


def run():
    graph = load_graph()
    elements = load_elements(graph, first_identifier(grid))
    print("initial elements", elements)

    cyto.load_extra_layouts()

    app = dash.Dash(external_stylesheets=[dbc.themes.BOOTSTRAP])

    state = {
        "loading_more": False,
        "clicked": "",
        "clicked_at": datetime.now(),
        "resetId": "",
    }

    @app.callback(
        Output("hiddenTypes", "data"),
        Input({"type": "typeFilter", "index": ALL}, "value"),
        State({"type": "typeFilter", "index": ALL}, "id"),
    )
    def show_hide_type(filtered_type, ids):
        res = [t["index"] for i, t in enumerate(ids) if not filtered_type[i]]
        return res

    @app.callback(
        Output("typeFilterList", "children"),
        Input("allElements", "data"),
        Input("hiddenTypes", "data"),
    )
    def update_filters(elements, hidden_types):
        hidden_types = hidden_types or []
        types = sorted(
            list(set([e["data"]["type"] for e in elements if "type" in e["data"]]))
        )
        return [
            html.Li(
                className="list-group-item",
                children=[
                    html.Label(
                        htmlFor=f'{{"index":"{t}","type":"typeFilter"}}',
                        className="d-flex justify-content-between align-items-center",
                        children=[
                            t,
                            dbc.Switch(
                                id={"index": t, "type": "typeFilter" },
                                value=t not in hidden_types,
                            ),
                        ],
                    ),
                ],
            )
            for t in types
        ]

    @app.callback(Output("graph", "layout"), Input("autoLayoutButton", "n_clicks"))
    def auto_layout(button):
        return {
            "name": "cose-bilkent",
            "idealEdgeLength": 96,
            "randomize": False,
            # "quality": "proof",
            "updateID": datetime.now(),
        }

    @app.callback(Output("output", "children"), Input("graph", "selectedNodeData"))
    def on_hover(data):
        if data:
            return dash.html.Pre(
                data[0]["description"],
                style={
                    "backgroundColor": "white",
                    "border": 1,
                    "paddingLeft": "1em",
                },
                className="overflow-auto",
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
        Output("allElements", "data"),
        Input("graph", "tapNode"),
        Input("resetButton", "n_clicks"),
        Input("searchIdButton", "n_clicks"),
        State("searchId", "value"),
        State("allElements", "data"),
    )
    def on_click(
        node,
        resetButton,
        searchIdButton,
        searchId,
        elements,
    ):
        if dash.callback_context.triggered[0]["prop_id"] == "resetButton.n_clicks":
            if state["clicked"]:
                if state["resetId"]:
                    return load_elements(graph, state["resetId"])

            return load_elements(graph, first_identifier(grid))
        if dash.callback_context.triggered[0]["prop_id"] == "searchIdButton.n_clicks":
            return load_elements(graph, searchId.strip())

        if not node:
            state["clicked"] = ""
            return dash.no_update

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
                already_present.append(el["data"]["id"])

        new_elements = load_elements(
            graph, node["data"]["id"], already_present=already_present, depth=2
        )
        if new_elements:
            for n in new_elements:
                n["renderedPosition"] = node["renderedPosition"]
            new_elements.extend(elements)
            elements = new_elements
        state["loading_more"] = False
        
        return elements

    @app.callback(
        Output("graph", "elements"),
        Input("hiddenTypes", "data"),
        Input("allElements", "data"),
        State("graph", "elements"),
    )
    def hide_elements(hidden_types, all_elements, displayed_elements):
        if not all_elements:
            return dash.no_update
        print("all: ", len(all_elements))
        print("displayed: ", len(displayed_elements))
        if hidden_types:
            els = []
            hidden_ids = [
                e["data"]["id"]
                for e in all_elements
                if "type" in e["data"] and e["data"]["type"] in hidden_types
            ]
            for e in all_elements:
                d = e["data"]
                if "id" in d and d["id"] not in hidden_ids:
                    els.append(e)
                if "source" in d:
                    if (
                        d["source"] not in hidden_ids
                        and d["target"] not in hidden_ids
                    ):
                        els.append(e)

            all_elements = els

        new_els = []
        all_edge_ids = set(
            (e["data"]["source"], e["data"]["target"])
            for e in all_elements
            if "source" in e["data"]
        )
        all_node_ids = set(e["data"]["id"] for e in all_elements if "id" in e["data"])
        displayed_edge_ids = set(
            (e["data"]["source"], e["data"]["target"])
            for e in displayed_elements
            if "source" in e["data"]
        )
        displayed_node_ids = set(
            e["data"]["id"] for e in displayed_elements if "id" in e["data"]
        )
        for e in displayed_elements:
            d = e["data"]
            if "id" in d and d["id"] in all_node_ids:
                new_els.append(e)
            if "source" in d and (d["source"], d["target"]) in all_edge_ids:
                new_els.append(e)
        for e in all_elements:
            d = e["data"]
            if "id" in d and d["id"] not in displayed_node_ids:
                new_els.append(e)
            if (
                "source" in d
                and (d["source"], d["target"]) not in displayed_edge_ids
            ):
                new_els.append(e)

        return new_els

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
        # layout={"name": "cose-bilkent", "idealEdgeLength": 96, "randomize": True},
        layout={"name": "fcose", "idealEdgeLength": 96, "randomize": True},
        # style={"width": "100%", "height": "1000px"},
        style={
            # "position": "absolute",
            "width": "100%",
            "height": "100%",
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
                    "width": 10,
                    "height": 10,
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
                    "outline-color": "blue",
                    "outline-width": 3,
                },
            },
        ]
        + img_stylesheet,
        responsive=True,
        boxSelectionEnabled=True,
        wheelSensitivity=0.3,
    )

    sidebar = html.Div(
        className="overflow-auto",
        children=[
            html.H2("CGMES Explorer", className="display-8"),
            html.Hr(),
            dbc.Button(
                "Click here!", id="resetButton", className="mb-3", color="primary"
            ),
            dbc.InputGroup(
                [
                    dbc.Input(
                        id="searchId", type="text", placeholder="RDFID", size="20em"
                    ),
                    dbc.Button("Go to ID", id="searchIdButton", color="primary"),
                ],
                className="mb-3",
            ),
            html.Hr(),
            html.Div(id="output", className="small overflow-auto"),
            html.Hr(),
            html.H3("Visibility"),
            html.Ul(
                id="typeFilterList",
                className="list-group",
                children=[],
            ),
        ],
        style={
            "position": "fixed",
            "top": 0,
            "left": 0,
            "bottom": 0,
            "width": "40rem",
            "padding": "2rem 1rem",
            "backgroundColor": "#f8f9fa",
        },
    )

    content = html.Div(
        [
            cs,
            dbc.Button(
                "Auto-Layout",
                id="autoLayoutButton",
                color="outline-primary",
                className="m-3 position-absolute top-0 end-0",
            ),
        ],
        style={
            "marginLeft": "40rem",
            "marginRight": "0rem",
            "padding": "0rem",
            "height": "100vh",
        },
    )

    app.layout = html.Div(
        [
            sidebar,
            content,
            dcc.Store(id="hiddenTypes", data=[]),
            dcc.Store("allElements", data=elements),
        ]
    )

    app.run(debug=True, use_reloader=False)
