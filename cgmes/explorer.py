import functools
from dataclasses import dataclass
from pathlib import Path

import pandas
from loguru import logger


@dataclass
class CGMESValue:
    value: str
    file: str

    def __repr__(self):
        return f"{self.value}"

    def html_version(self):
        return f"<a href={self.file}>{self.value}</a>"


class CGMESNode:
    def __init__(self, id: str):
        self.id = id
        self.total_links: int = 0
        self.props: dict[str, CGMESValue] = {}
        self.children: list[tuple[str, CGMESValue]] = []
        self.files: list[str] = []

    def add_file(self, file: str):
        if file in self.files:
            return
        self.files.append(file)
        self.files.sort()

    def add_value(self, key, value, instance_id):
        self.props[key] = CGMESValue(value, instance_id)

    def add_child(self, filiation, child, instance_id):
        self.children.append((filiation, CGMESValue(child, instance_id)))

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
        rep += f"  Total Neighbours: {self.total_links}"

        return rep


@dataclass
class Element:
    rdfid: str
    cim_type: str
    name: str


class Graph:
    def __init__(self, df: pandas.DataFrame):
        logger.info("Precompute graph")

        df.KEY = df.KEY.astype("category")
        self.all_files = df[df.KEY == "label"][["VALUE", "INSTANCE_ID"]]
        self.all_files = self.all_files.set_index("INSTANCE_ID").VALUE

        self.df = df.set_index("ID")

        logger.info("indexing...")
        self.idx = self.df.groupby(level=0, sort=False).indices
        logger.info("indexing done")

        logger.info("children...")
        index_unique = self.df.index.unique()
        df_children = self.df.loc[self.df.VALUE.isin(index_unique), "VALUE"]
        logger.info("children")
        self.children = {}
        for parent, child in df_children.items():
            self.children.setdefault(parent, set()).add(child)
        logger.info("children done")

        logger.info("parents...")
        self.parents = {}
        for parent, child in df_children.items():
            self.parents.setdefault(child, set()).add(parent)
        logger.info("parents done")

        logger.info("elements...")
        names = self.df[self.df.KEY == "IdentifiedObject.name"]
        types = self.df[(self.df.KEY == "Type") & self.df.index.isin(names.index)]
        types = types[~types.index.duplicated(keep="first")]
        self.elements = names[["VALUE"]].rename(columns={"VALUE": "IdentifiedObject.name"})
        self.elements["Type"] = types.VALUE
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
            node.total_links = len(self.parents.get(identifier, [])) + len(self.children.get(identifier, []))

            instances = node_df.INSTANCE_ID.unique()
            files = self.all_files.loc[instances].to_dict()
            for file in sorted(files.values()):
                node.add_file(file)

            for row in node_df.itertuples():
                r = row
                node.id = identifier
                value = row.VALUE
                file_name = files[row.INSTANCE_ID]
                if pandas.isna(row.VALUE):
                    value = "N/A"
                if value == identifier:
                    node.add_value(r.KEY, value, file_name)
                elif value in self.all_ids:
                    node.add_child(r.KEY, value, file_name)
                else:
                    node.add_value(r.KEY, value, file_name)

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
