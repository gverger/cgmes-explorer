import networkx as nx
import cgmes
import matplotlib.pyplot as plt
import graphs

grid = "small"
# grid = "large"


def main():
    if grid == "small":
        graph = cgmes.load_folder("./samples/smallgrid")

        identifier = cgmes.identifier_for(
            "20171002T0930Z_BE_EQ_2.xml", "_17086487-56ba-4979-b8de-064025a6b4da"
        )
    else:
        graph = cgmes.load_folder("./samples/realgrid")
        identifier = cgmes.identifier_for(
            "CGMES_v2.4.15_RealGridTestConfiguration_EQ_V2.xml", "_426798065_ACLS"
        )

    all = list(
        set(
            [identifier]
            + graph.descendants(identifier, depth=1000)
            + graph.ascendants(identifier, depth=1000)
        )
    )
    # print(descendants(graph, identifier))
    # print(ascendants(graph, identifier))

    g = nx.DiGraph()

    g.add_nodes_from(all)

    props = {}
    for identifier in all:
        n = graph.properties(identifier)
        props[identifier] = n
        for p in n.props:
            g.nodes[identifier][p] = n.props[p]

        for c in n.children:
            if n.children[c] not in all:
                continue
            g.add_edge(identifier, n.children[c], rel=c)

    for nid, n in props.items():
        print(graphs.node_details(nid, n))

    labels = {nid: f"{graphs.node_details(nid, n)}" for nid, n in props.items()}

    # pos = nx.planar_layout(g)
    h = nx.Graph(g)
    pos = nx.planar_layout(h)
    pos = nx.spring_layout(h, pos=pos)
    pos = nx.spring_layout(h)
    # nx.draw_networkx(g, pos, with_labels=False)
    # nx.draw_networkx_labels(g, pos, labels)

    # nx.nx_pydot.graphviz_layout(g)
    # p = nx.nx_pydot.to_pydot(g)
    # a = nx.nx_agraph.to_agraph(g)
    # a.draw("graph.svg", args="-Gnodesep=0.01 -Gfontsize=1", prog="dot")
    # a.draw("graph.svg", prog="sfdp")
    # a.draw("graph.svg", prog="neato", labels=labels)
    # p.write_dot("graph.dot")
    nx.draw(
        g,
        pos=pos,
        node_shape="s",
        node_color="#aaaaaa",
        labels=labels,
        arrows=True,
        arrowstyle="-|>",
        font_size=3,
        horizontalalignment="left",
    )
    plt.savefig("graph.svg")


if __name__ == "__main__":
    main()
