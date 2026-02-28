import functools
import zipfile
from dataclasses import dataclass
from pathlib import Path

import pandas
import triplets
import rdflib as rdf
from loguru import logger
from numpy.random import rand
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
        self.files: list[str] = []

    def add_file(self, file: str):
        if file in self.files:
            return
        self.files.append(file)
        self.files.sort()

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


@dataclass
class Element:
    rdfid: str
    cim_type: str
    name: str


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

    @property
    @functools.cache
    def elements(self) -> list[Element]:
        logger.info("loading elements...")
        _elements = []
        query = """
            SELECT ?s ?t ?n
            WHERE {
            ?s rdf:type ?t.
            ?s cim:IdentifiedObject.name ?n
            }
            LIMIT 10000000
            """

        for res in self.graph.query(query):
            assert isinstance(res, ResultRow)
            if not isinstance(res["s"], rdf.URIRef):
                continue
            rdfid = self._n3(res["s"])
            kind = res["t"]
            name = res["n"]
            if rdfid.startswith(FILE_NS):
                _elements.append(Element(rdfid.split(":")[1].strip(), kind, name))
        logger.info(f"{len(_elements)} elements loaded")
        return _elements

    def elem_with_name(self, name: str) -> Element | None:
        logger.info(f"looking for element with name [{name}]")
        for e in self.elements:
            if e.name.strip() == name:
                return e

        return None

    def random_element(self):
        return self.elements[int(rand() * len(self.elements))]

    @functools.cache
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
        return identifier
        assert identifier.startswith(FILE_NS)
        assert ":" in identifier

        text = identifier.removeprefix(FILE_NS)
        return text.split(":")[1]


class GraphWithTriples(Graph):
    def __init__(self, df: pandas.DataFrame):
        super().__init__()
        logger.info("Precompute graph")
        self.all_files = df[df.KEY == "label"][["VALUE", "INSTANCE_ID"]]
        self.all_files = self.all_files.set_index("INSTANCE_ID")

        self.df = df.set_index("ID")

        self.idx = {g[0]: g[1].index.tolist() for g in df[["ID"]].groupby("ID")}

        df_with_link = self.df.assign(link=self.df.VALUE.isin(self.df.index))
        print(df_with_link)
        self.children = {
            g[0]: set(g[1].VALUE.tolist())
            for g in df_with_link[df_with_link.link][["VALUE"]].groupby("ID")
        }
        logger.info("children: len = {}", len(self.children))
        self.parents = {
            g[0]: set(g[1].index.tolist())
            for g in df_with_link[df_with_link.link][["VALUE"]].groupby("VALUE")
        }
        logger.info("Graph precomputed")

    @property
    @functools.cache
    def elements(self) -> list[Element]:
        logger.info("loading elements from triplets...")
        df = self.df[self.df.KEY.isin(["Type", "IdentifiedObject.name"])]
        df = df.pivot_table(
            values="VALUE", index=["ID"], columns=["KEY"], aggfunc="first"
        ).dropna()

        return [
            Element(r[0], r[1], r[2])
            for r in df[["Type", "IdentifiedObject.name"]].to_records()
        ]

    @property
    @functools.cache
    def all_ids(self) -> set[str]:
        return set(self.df.index.values)

    def properties(self, identifiers: list[str]) -> dict[str, CGMESNode]:
        logger.info("df for {}", identifiers)
        rows = []
        for identifier in identifiers:
            rows.extend(self.idx[identifier])

        df = self.df.iloc[rows][["KEY", "VALUE", "INSTANCE_ID"]]

        nodes:dict[str,CGMESNode] = {}
        for identifier in identifiers:
            node_df = df.loc[identifier]
            node = CGMESNode(identifier)
            for row in node_df.itertuples():
                r = row
                node.id = identifier
                if row.VALUE == identifier:
                    node.add_value(r.KEY, r.VALUE)
                elif r.VALUE in self.all_ids:
                    node.add_child(r.KEY, r.VALUE)
                else:
                    node.add_value(r.KEY, r.VALUE)

            instances = node_df.INSTANCE_ID.unique()
            for file in self.all_files.loc[instances].values:
                node.add_file(file)

            nodes[identifier] = node
        logger.info("done")
        return nodes

    def descendants(self, identifier: str, depth=1000, max_seen=5) -> list[str]:
        logger.info("descendants of {}...", identifier)
        close = set()
        opened = {identifier}
        while opened:
            current = opened.pop()
            if current in close:
                continue
            close.add(current)
            opened = opened | self.children.get(current, set())

        close.remove(identifier)
        logger.info("descendants done")
        return list(close)

    def ascendants(self, identifier: str, depth=1000, max_seen=5) -> list[str]:
        logger.info("ascendants of {}...", identifier)
        close = set()
        opened = {identifier}
        while opened:
            current = opened.pop()
            if current in close:
                continue
            close.add(current)
            opened = opened | self.parents.get(current, set())

        close.remove(identifier)
        logger.info("descendants done")
        logger.info("ascendants done")
        return list(close)


def load_zip(filepath: Path | str) -> Graph:
    graph = GraphWithTriples(pandas.read_RDF(filepath))
    # archive = zipfile.ZipFile(filepath)
    # for file in archive.filelist:
    #     logger.info(f"loading {file.filename}")
    #     with archive.open(file) as f:
    #         graph.graph.parse(f, format="xml")
    #         graph.graph.bind(
    #             FILE_NS + graph.prefix_from_filename(f.name).prefix,
    #             f"{f.name}#",
    #         )
    return graph


def load_folder(cgmes_folder: Path | str) -> Graph:
    cgmes_folder = Path(cgmes_folder)

    graph = Graph()

    for f in cgmes_folder.glob("*.xml"):
        logger.info(f"loading {f}")
        graph.graph.parse(f)
        graph.graph.bind(
            FILE_NS + graph.prefix_from_filename(f.name).prefix,
            f"{f.absolute().as_uri()}#",
        )

    return graph
