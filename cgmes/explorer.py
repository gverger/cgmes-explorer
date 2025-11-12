from dataclasses import dataclass
from pathlib import Path

from loguru import logger
import rdflib as rdf
from rdflib import term
from rdflib.query import ResultRow

FILE_NS = "NSFILE_"


@dataclass
class FilePrefix:
    filename: str
    prefix: str


class CGMESNode:
    def __init__(self, id: str):
        self.id = id
        self.props: dict[str, str] = {}
        self.children: list[tuple[str, str]] = []

    def add_value(self, key, value):
        self.props[key] = value

    def add_child(self, filiation, child):
        self.children.append((filiation, child))

    def __repr__(self) -> str:
        rep = f"{self.id}:\n"
        if len(self.props) > 0:
            rep += "  Properties:\n"
            for key in sorted(self.props.keys()):
                rep += f"    {key}: {self.props[key]}\n"
        if len(self.children) > 0:
            rep += "  Children:\n"
            for child in sorted(self.children):
                rep += f"    {child[0]}: {child[1]}\n"

        return rep


class Graph:
    def __init__(self):
        self.graph = rdf.Graph()
        self.filenames: list[FilePrefix] = []
        self.ids: dict[str, str] = {}

    def _ids(self, identifier: str):
        id = identifier.split(":")[1]
        return [f"{FILE_NS}{el.prefix}:{id}" for el in self.filenames]

        # if not self.ids:
        #     self.load_ids()

        # return [self.ids[identifier[identifier.index(":")+1:]]]

    def load_ids(self):
        logger.info("loading ids...")
        self.ids = {}
        query = """
            SELECT ?s
            WHERE {
            ?s rdf:type ?o.
            }
            LIMIT 10000000
            """

        for res in self.graph.query(query):
            assert isinstance(res, ResultRow)
            if not isinstance(res["s"], rdf.URIRef):
                continue
            rdfid = self._n3(res["s"])
            if rdfid.startswith(FILE_NS):
                self.ids[rdfid.split(":")[1]] = rdfid
        logger.info("{len(self.ids)} ids loaded")

    def properties(self, identifier: str) -> CGMESNode:
        query = """
    SELECT ?s ?p ?o
    WHERE {
      VALUES ?s { $ID }
    ?s ?p ?o.
    }
    LIMIT 1000
            """

        query = query.replace("$ID", " ".join(self._ids(identifier)))

        node = CGMESNode(identifier)

        for res in self.graph.query(query):
            assert isinstance(res, ResultRow)
            raw_p = res.get("p")
            p = self._n3(raw_p)
            raw_o = res.get("o")
            o = self._n3(raw_o)

            if p == "rdf:type":
                node.id = self._n3(res.get("s"))
                node.add_value(p, o)
            elif isinstance(raw_o, rdf.Literal):
                node.add_value(p, raw_o.value)
            elif isinstance(raw_o, rdf.URIRef):
                node.add_child(p, o)

        return node

    def ascendants(self, identifier: str, depth=1000, max_seen=5) -> list[str]:
        query = """
    SELECT ?p ?o
    WHERE {
      VALUES ?s { $ID }
    ?o ?p ?s.
    }
    LIMIT 10000
            """
        return self.rec_search(query, identifier, [], depth, max_seen)

    def descendants(self, identifier: str, depth=1000, max_seen=5) -> list[str]:
        query = """
    SELECT ?s ?p ?o
    WHERE {
      VALUES ?s { $ID }.
    ?s ?p ?o.
    }
    LIMIT 1000
            """
        return self.rec_search(query, identifier, [], depth, max_seen)

    def rec_search(
        self,
        query: str,
        identifier: str,
        seen: list[str],
        depth: int,
        max_seen: int,
    ):
        logger.info("rec {}, {}", identifier, seen)
        if depth == 0:
            return []
        if identifier in seen:
            return []
        if len(seen) >= max_seen:
            return []

        seen.append(identifier)

        q = query.replace("$ID", " ".join(self._ids(identifier)))

        for res in self.graph.query(q):
            assert isinstance(res, rdf.query.ResultRow)
            o = res.get("o")
            childid = self._n3(o)

            if childid.startswith(FILE_NS) and isinstance(o, rdf.URIRef):
                self.rec_search(query, childid, seen, depth - 1, max_seen)
                if len(seen) >= max_seen:
                    logger.warning("max nodes reached. results will be troncated")
                    return seen

        return seen

    def _n3(self, rdf_result: term.Identifier | None) -> str:
        if not rdf_result:
            return "NONE"
        return rdf_result.n3(self.graph.namespace_manager)

    def prefix_from_filename(self, filename: str) -> FilePrefix:
        for f in self.filenames:
            if f.filename == filename:
                return f
        prefix = FilePrefix(filename, f"{len(self.filenames)}")
        self.filenames.append(prefix)
        return prefix

    def filename_from_prefix(self, prefix: str) -> FilePrefix | None:
        for f in self.filenames:
            if f.prefix == prefix:
                return f
        return None

    def identifier_for(self, filename: str, rdfid: str) -> str:
        prefix = self.prefix_from_filename(filename).prefix
        return FILE_NS + f"{prefix}:{rdfid}"

    def file_for(self, identifier: str) -> str:
        assert identifier.startswith(FILE_NS)
        assert ":" in identifier

        text = identifier.removeprefix(FILE_NS)
        fileprefix = self.filename_from_prefix(text.split(":")[0])

        if not fileprefix:
            logger.error("No file for prefix {}", text)
            return ""

        return fileprefix.filename

    def rdfid_for(self, identifier: str) -> str:
        assert identifier.startswith(FILE_NS)
        assert ":" in identifier

        text = identifier.removeprefix(FILE_NS)
        return text.split(":")[1]


NAMESPACE_ESCAPES = {
    "(": "%28",
    ")": "%29",
}


def load_folder(cgmes_folder: Path | str) -> Graph:
    cgmes_folder = Path(cgmes_folder)

    graph = Graph()

    for f in cgmes_folder.glob("*.xml"):
        print(f"loading {f}")
        graph.graph.parse(f)
        namespace = f.absolute().as_posix()
        for k, v in NAMESPACE_ESCAPES.items():
            namespace = namespace.replace(k, v)
        graph.graph.bind(
            FILE_NS + graph.prefix_from_filename(f.name).prefix,
            f"file://{namespace}#",
        )

    return graph
