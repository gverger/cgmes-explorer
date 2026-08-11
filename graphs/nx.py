from dataclasses import dataclass
from typing import Any

from cgmes.explorer import CGMESNode, Graph, CGMESValue


@dataclass
class NodeDetails:
    id: str
    type: str
    name: str
    file: list[str]
    properties: dict[str, CGMESValue]
    children: list[tuple[str, CGMESValue]]
    neighbors: int

    def title(self) -> str:
        return f"{self.type} - {self.name}"



    def __repr__(self) -> str:
        if len(self.file) == 1:
            return self.__repr_one_file__()
        else:
            return self.__repr_several_files__()

    def __repr_one_file__(self):
        rep = f"{self.id}:\n"
        rep += f"- in file {self.file[0]}\n"
        rep += f"- type = {self.type}\n"
        rep += f"- name = {self.name}\n"
        if len(self.properties) > 0:
            rep += "  Properties:\n"
            for key in sorted(self.properties.keys()):
                rep += f"      {key}: {self.properties[key]}\n"
        if len(self.children) > 0:
            rep += "  Children:\n"
            for child in sorted(self.children, key= lambda c: c[0]):
                rep += f"    {child[0]}: {child[1].value.split(':')[-1]}\n"

        return rep

    def __repr_several_files__(self):
        rep = f"{self.id}:\n"
        rep += "- in files:\n"
        for f in self.file:
            rep += f"  - {f}\n"
        rep += f"- type = {self.type}\n"
        rep += f"- name = {self.name}\n"
        for f in self.file:
            properties = {k: v for k,v in self.properties.items() if v.file == f}
            children = [v for v in self.children if v[1].file == f]
            rep+= f"  In file {f}:\n"
            if len(properties) > 0:
                rep += "    Properties:\n"
                for key in sorted(properties.keys()):
                    rep += f"      {key}: {properties[key]}\n"
            if len(children) > 0:
                rep += "    Children:\n"
                for child in sorted(children):
                    rep += f"      {child[0]}: {child[1].value.split(':')[-1]}\n"

        return rep


def node_details(graph: Graph, node: CGMESNode) -> NodeDetails:
    node_type = node.props.get("Type", "").value.removeprefix("cim:")
    node_name = node.props.get("IdentifiedObject.name", node.id)
    node_properties = {
        k: v
        for k, v in node.props.items()
        if k != "IdentifiedObject.name" and k != "Type"
    }

    return NodeDetails(
        id=node.id,
        type=node_type,
        name=node_name,
        file=node.files,
        properties=node_properties,
        children=node.children,
        neighbors= node.total_links,
    )
