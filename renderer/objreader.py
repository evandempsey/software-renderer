# Reader for .obj file format.


def parse_vertex(line, vertices):
    """
    Parse a line defining a vertex.
    """
    vertex = [float(x) for x in line.split()[1:]]
    vertices.append(vertex)


def parse_facet(line, facets):
    """
    Parse a line defining a facet.
    """
    facet = [int(x.split("/")[0])-1 for x in line.split()[1:]]
    facets.append(facet)


def convert_facets_to_edges(facets):
    """
    Convert facet list to list of edges
    without duplication of edges.
    """
    edges = []

    for facet in facets:
        edge1 = sorted([facet[0], facet[1]])
        edge2 = sorted([facet[1], facet[2]])
        edge3 = sorted([facet[0], facet[2]])

        if edge1 not in edges:
            edges.append(edge1)
        if edge2 not in edges:
            edges.append(edge2)
        if edge3 not in edges:
            edges.append(edge3)

    return edges


def read(filename):
    """
    Read a .obj file.
    """
    vertices = []
    facets = []

    input_file = open(filename)
    for line in input_file.readlines():
        if line.startswith("v "):
            parse_vertex(line, vertices)
        elif line.startswith("f "):
            parse_facet(line, facets)

    edges = convert_facets_to_edges(facets)

    return vertices, facets, edges


def main():
    """
    Test the .obj file reader.
    """
    vertices, facets, edges = read("models/gourd.obj")
    print vertices
    print facets
    print edges


if __name__ == "__main__":
    main()