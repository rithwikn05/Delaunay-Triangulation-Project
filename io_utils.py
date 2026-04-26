
def read_node_file(filename):
    points = []
    indices = []

    with open(filename, 'r') as f:
        lines = [line.strip() for line in f
                 if line.strip() and not line.strip().startswith('#')]

    # First non-comment line is the header
    header = lines[0].split()
    n_verts = int(header[0])
    # dimension = int(header[1])  # always 2
    # n_attrs = int(header[2])
    # n_markers = int(header[3])

    for line in lines[1:n_verts + 1]:
        parts = line.split()
        idx = int(parts[0])
        x = float(parts[1])
        y = float(parts[2])
        indices.append(idx)
        points.append((x, y))

    return points, indices


def write_ele_file(filename, triangles, point_to_index):
    with open(filename, 'w') as f:
        # Header: num_triangles, nodes_per_triangle, num_attributes
        f.write(f"{len(triangles)} 3 0\n")
        for i, (v0, v1, v2) in enumerate(triangles, start=1):
            i0 = point_to_index.get(v0, -1)
            i1 = point_to_index.get(v1, -1)
            i2 = point_to_index.get(v2, -1)
            f.write(f"{i}  {i0}  {i1}  {i2}\n")


def build_point_index_map(points, indices):
    return {p: idx for p, idx in zip(points, indices)}

def parse_node_filename(node_file):
    if node_file.endswith('.node'):
        return node_file[:-5]
    return node_file