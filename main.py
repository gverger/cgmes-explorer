from pathlib import Path
import rdflib as rdf
from datetime import datetime

def get(graph: rdf.Graph, prop_query: str, identifier: str, indent = ""):
    # query = query.replace("$ID", 'F20171002T0930Z_BE_EQ_2.xml:_17086487-56ba-4979-b8de-064025a6b4da')
    query = prop_query.replace("$ID", identifier)

    # print(query)

    references = []

    for res in graph.query(query):
        s = res.get("s")
        p = res.get("p")
        if isinstance(p, rdf.URIRef):
            p.n3(graph.namespace_manager)
        o = res.get("o")

        print(f"{indent}{s.n3(graph.namespace_manager)} {p.n3(graph.namespace_manager)} {o.n3(graph.namespace_manager)}")

        if isinstance(o, rdf.URIRef):
            get(graph, prop_query, o.n3(graph.namespace_manager), f"  {indent}")

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
        graph.bind("F"+f.name, f"file://{f.absolute()}#")

    stop = datetime.now()
    print(f"loading duration: {stop - start}")


    with open("./query.rq") as qf:
        prop_query = qf.read()

    with open("./query_up.rq") as qf:
        asc_query = qf.read()

    # get(graph, prop_query, 'F20171002T0930Z_BE_EQ_2.xml:_17086487-56ba-4979-b8de-064025a6b4da')
    get(graph, asc_query, 'F20171002T0930Z_BE_EQ_2.xml:_17086487-56ba-4979-b8de-064025a6b4da')

    # get(graph, prop_query, 'FCGMES_v2.4.15_RealGridTestConfiguration_EQ_V2.xml:_426798065_ACLS')
    # get(graph, asc_query, 'FCGMES_v2.4.15_RealGridTestConfiguration_EQ_V2.xml:_426798065_ACLS')



if __name__ == "__main__":
    main()
