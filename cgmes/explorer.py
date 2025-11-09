from datetime import datetime
from pathlib import Path
import rdflib as rdf
from rdflib import term
from rdflib.query import ResultRow

FILE_NS = "NSFILE_"


def identifier_for(filename: str, rdfid: str) -> str:
    return FILE_NS + f"{filename}:{rdfid}"


class CGMESNode:
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


class Graph:
    def __init__(self):
        self.graph = rdf.Graph()

    def properties(self, identifier: str) -> CGMESNode:
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

        for res in self.graph.query(query):
            assert isinstance(res, ResultRow)
            raw_p = res.get("p")
            p = self._n3(raw_p)
            raw_o = res.get("o")
            o = self._n3(raw_o)

            if p == "rdf:type":
                node.add_value(p, o)
            elif isinstance(raw_o, rdf.Literal):
                node.add_value(p, raw_o.value)
            elif isinstance(raw_o, rdf.URIRef):
                node.add_child(p, o)

        return node

    def ascendants(
        self, identifier: str, seen: list[str] = [], depth=1000
    ) -> list[str]:
        if depth == 0:
            return []
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

        for res in self.graph.query(query):
            assert isinstance(res, ResultRow)
            o = res.get("o")
            identifier = self._n3(o)

            if identifier.startswith(FILE_NS) and isinstance(o, rdf.URIRef):
                references.append(identifier)
                references.extend(self.ascendants(identifier, seen, depth - 1))

        return references

    def descendants(
        self, identifier: str, seen: list[str] = [], depth=1000
    ) -> list[str]:
        if depth == 0:
            return []
        if identifier in seen:
            return []
        seen.append(identifier)

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

        for res in self.graph.query(query):
            assert isinstance(res, rdf.query.ResultRow)
            o = res.get("o")
            identifier = self._n3(o)

            if identifier.startswith(FILE_NS) and isinstance(o, rdf.URIRef):
                references.append(identifier)
                references.extend(self.descendants(identifier, seen, depth - 1))

        return references

    def _n3(self, rdf_result: term.Identifier | None) -> str:
        if not rdf_result:
            return "NONE"
        return rdf_result.n3(self.graph.namespace_manager)


def load_folder(cgmes_folder: Path | str) -> Graph:
    cgmes_folder = Path(cgmes_folder)

    start = datetime.now()
    graph = Graph()

    for f in cgmes_folder.glob("*.xml"):
        print(f"loading {f}")
        graph.graph.parse(f)
        graph.graph.bind(FILE_NS + f.name, f"file://{f.absolute()}#")

    stop = datetime.now()
    print(f"loading duration: {stop - start}")

    return graph
