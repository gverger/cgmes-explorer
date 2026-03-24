import functools
from dataclasses import dataclass
from pathlib import Path

import pandas
import triplets
from loguru import logger


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
    def __init__(self, df: pandas.DataFrame):
        logger.info("Precompute graph")

        self.all_files = df[df.KEY == "label"][["VALUE", "INSTANCE_ID"]]
        self.all_files = self.all_files.set_index("INSTANCE_ID").VALUE

        self.df = df.set_index("ID")

        logger.info("indexing...")
        self.idx = {}
        for iloc, id in df.ID.items():
            if id not in self.idx:
                self.idx[id] = [iloc]
            else:
                self.idx[id].append(iloc)
        logger.info("indexing done")

        logger.info("children...")
        index_unique = self.df.index.to_frame().drop_duplicates().index
        df_with_link = self.df.assign(link=self.df.VALUE.isin(index_unique))
        df_children = df_with_link[df_with_link.link].VALUE
        self.children = {}
        for a, b in df_children.items():
            if a not in self.children:
                self.children[a] = {b}
            else:
                self.children[a].add(b)

        logger.info("children done")

        logger.info("parents...")
        df_parents = pandas.Series(df_children.index.values, index=df_children)
        self.parents = {}
        for a, b in df_parents.items():
            if a not in self.parents:
                self.parents[a] = {b}
            else:
                self.parents[a].add(b)
        logger.info("parents done")

        logger.info("elements...")
        self.elements = self.df[self.df.KEY.isin(["Type", "IdentifiedObject.name"])]
        self.elements = self.elements.pivot_table(
            values="VALUE", index=["ID"], columns=["KEY"], aggfunc="first"
        ).dropna()
        self.elements = self.elements.assign(
            lower_name=self.elements["IdentifiedObject.name"].str.lower()
        )
        logger.info("elements done")

        logger.info("Graph precomputed")

    @property
    @functools.cache
    def all_ids(self) -> set[str]:
        return set(self.df.index.values)

    def properties(self, identifiers: list[str]) -> dict[str, CGMESNode]:
        rows = []
        for identifier in identifiers:
            rows.extend(self.idx[identifier])

        df = self.df.iloc[rows][["KEY", "VALUE", "INSTANCE_ID"]]

        nodes: dict[str, CGMESNode] = {}
        for identifier in identifiers:
            node_df = df.loc[identifier]
            node = CGMESNode(identifier)
            for row in node_df.itertuples():
                r = row
                node.id = identifier
                value = row.VALUE
                if pandas.isna(row.VALUE):
                    value = "N/A"
                if value == identifier:
                    node.add_value(r.KEY, value)
                elif value in self.all_ids:
                    node.add_child(r.KEY, value)
                else:
                    node.add_value(r.KEY, value)

            instances = node_df.INSTANCE_ID.unique()
            for file in self.all_files.loc[instances]:
                node.add_file(file)

            nodes[identifier] = node
        logger.info("done")
        return nodes

    def descendants(self, identifier: str) -> list[str]:
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

    def elem_with_name(self, name: str) -> Element | None:
        df = self.elements[self.elements["IdentifiedObject.name"] == name]
        if len(df) == 0:
            return None

        d = df.reset_index().iloc[0].to_dict()
        return Element(d["ID"], d["Type"], name)


def load_zip(filepath: Path | str) -> Graph:
    graph = Graph(pandas.read_RDF(filepath))
    return graph
