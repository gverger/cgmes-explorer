from dataclasses import dataclass
from typing import Any

from cgmes.explorer import CGMESNode, Graph


@dataclass
class NodeDetails:
    id: str
    type: str
    name: str
    file: list[str]
    properties: dict[str, Any]
    children: list[tuple[str, str]]

    def title(self) -> str:
        return f"{self.type} - {self.name}"

    def __repr__(self) -> str:
        rep = f"{self.id}:\n"
        if len(self.file) == 1:
            rep += f"- in file {self.file[0]}\n"
        else:
            rep += "- in files:\n"
            for f in self.file:
                rep += f"  - {f}\n"
        rep += f"- type = {self.type}\n"
        rep += f"- name = {self.name}\n"
        if len(self.properties) > 0:
            rep += "  Properties:\n"
            for key in sorted(self.properties.keys()):
                rep += f"    {key}: {self.properties[key]}\n"
        if len(self.children) > 0:
            rep += "  Children:\n"
            for child in sorted(self.children):
                rep += f"    {child[0]}: {child[1].split(':')[-1]}\n"

        return rep


def node_details(graph: Graph, node: CGMESNode) -> NodeDetails:
    node_type = node.props.get("Type", "").removeprefix("cim:")
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
    )
