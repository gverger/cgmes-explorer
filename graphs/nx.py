from dataclasses import dataclass
from typing import Any

from cgmes.explorer import CGMESNode, file_for, rdfid_for


@dataclass
class NodeDetails:
    id: str
    type: str
    name: str
    file: str
    properties: dict[str, Any]
    children: dict[str, str]

    def title(self) -> str:
        return f"{self.type} - {self.name}"

    def __repr__(self) -> str:
        rep = f"{self.id} (in {self.file}):\n"
        rep += f"- type = {self.type}\n"
        rep += f"- name = {self.name}\n"
        if len(self.properties) > 1:
            rep += "  Properties:\n"
            for key in sorted(self.properties.keys()):
                rep += f"    {key}: {self.properties[key]}\n"
        if len(self.children) > 1:
            rep += "  Children:\n"
            for key in sorted(self.children.keys()):
                rep += f"    {key}: {self.children[key]}\n"

        return rep


def node_details(node_id: str, node: CGMESNode) -> NodeDetails:
    node_type = node.props.get("rdf:type", "").removeprefix("cim:")
    node_name = node.props.get("cim:IdentifiedObject.name", node_id)
    node_properties = {
        k: v
        for k, v in node.props.items()
        if k != "cim:IdentifiedObject.name" and k != "rdf:type"
    }

    return NodeDetails(
        id=rdfid_for(node_id),
        type=node_type,
        name=node_name,
        file=file_for(node_id),
        properties=node_properties,
        children=node.children,
    )
