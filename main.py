from pathlib import Path
from typing import Any
import rdflib as rdf
from datetime import datetime
import networkx as nx
import matplotlib.pyplot as plt

FILE_NS = "NSFILE_"

class CGMESNode():
    def __init__(self, id: str):
        self.id = id
        self.props = {}
        self.children = {}

    def add_value(self, key, value):
        self.props[key] = value

    def add_child(self, filiation, child):
        self.children[filiation] = child

    def __repr__(self) -> str:
        rep = f"{self.id}:\n"
        if len(self.props) > 1:
            rep += "Properties:\n"
            for key in sorted(self.props.keys()):
                rep += f"  {key}: {self.props[key]}\n"
        if len(self.props) > 1:
            rep += "Children:\n"
            for key in sorted(self.children.keys()):
                rep += f"  {key}: {self.children[key]}\n"

        return rep


def properties(graph: rdf.Graph, identifier: str) -> CGMESNode:
    query = """
SELECT ?s ?p ?o
WHERE {
  VALUES ?s { $ID }
?s ?p ?o.
}
LIMIT 1000
        """

    query = query.replace("$ID", identifier)

    node = CGMESNode(identifier)

    for res in graph.query(query):
        raw_p = res.get("p")
        p = raw_p.n3(graph.namespace_manager)
        raw_o = res.get("o")
        o = raw_o.n3(graph.namespace_manager)

        if p == "rdf:type":
            node.add_value(p, o)
        elif isinstance(raw_o, rdf.Literal):
            node.add_value(p, raw_o.value)
        elif isinstance(raw_o, rdf.URIRef):
            node.add_child(p, o)

    return node

def ascendants(graph: rdf.Graph, identifier: str, seen:list[str]=[]) -> list[str]:
    if identifier in seen:
        return []

    seen.append(identifier)

    query = """
SELECT ?s ?p ?o
WHERE {
?o ?p $ID.
  VALUES ?s { $ID }
}
LIMIT 10000
        """
    query = query.replace("$ID", identifier)

    references = []

    for res in graph.query(query):
        o = res.get("o")
        n3 = o.n3(graph.namespace_manager)

        if n3.startswith(FILE_NS) and isinstance(o, rdf.URIRef):
            identifier = o.n3(graph.namespace_manager)
            if identifier.startswith("F"):
                pass
            references.append(o.n3(graph.namespace_manager))
            references.extend(ascendants(graph, o.n3(graph.namespace_manager), seen))

    return references

def descendants(graph: rdf.Graph, identifier: str, seen: list[str]=[]) -> list[str]:
    if identifier in seen:
        return []
    seen.append( identifier)

    query = """
SELECT ?s ?p ?o
WHERE {
  VALUES ?s { $ID }
?s ?p ?o.
}
LIMIT 1000
        """
    query = query.replace("$ID", identifier)

    references = []

    for res in graph.query(query):
        o = res.get("o")
        n3 = o.n3(graph.namespace_manager)


        if n3.startswith(FILE_NS) and isinstance(o, rdf.URIRef):
            identifier = o.n3(graph.namespace_manager)
            if identifier.startswith("F"):
                pass
            references.append(o.n3(graph.namespace_manager))
            references.extend(descendants(graph, o.n3(graph.namespace_manager), seen))

    return references

def main():

    graph = rdf.Graph()

    # graph.bind("cim", rdf.Namespace("http://iec.ch/TC57/2013/CIM-schema-cim16#"))
    # graph.bind("rdf", rdf.RDF)


    start = datetime.now()

    small_grid_folder = Path("./samples/smallgrid")
    # small_grid_folder = Path("./samples/realgrid")
    for f in small_grid_folder.glob("*.xml"):
        print(f)
        graph.parse(f)
        graph.bind(FILE_NS+f.name, f"file://{f.absolute()}#")

    stop = datetime.now()
    print(f"loading duration: {stop - start}")


    with open("./query.rq") as qf:
        prop_query = qf.read()

    with open("./query_up.rq") as qf:
        asc_query = qf.read()

    identifier = FILE_NS + '20171002T0930Z_BE_EQ_2.xml:_17086487-56ba-4979-b8de-064025a6b4da'
    # identifier = FILE_NS + 'CGMES_v2.4.15_RealGridTestConfiguration_EQ_V2.xml:_426798065_ACLS'
    # print(properties(graph, identifier))
    all = [identifier] + descendants(graph, identifier) + ascendants(graph, identifier)
    # print(descendants(graph, identifier))
    # print(ascendants(graph, identifier))

    g = nx.DiGraph()

    g.add_nodes_from(all)

    for identifier in all:
        n = properties(graph, identifier)
        for p in n.props:
            g.nodes[identifier][p] = n.props[p]

        for c in n.children:
            g.add_edge(identifier, n.children[c], rel=c)

    nx.nx_pydot.graphviz_layout(g)
    plt.savefig("graph.png")


if __name__ == "__main__":
    main()
