def read_node_file(filepath):
    indices = []
    points = []
    
    with open(filepath, 'r') as f:
        # Read header
        header = f.readline().split()
        while not header or header[0].startswith('#'):
            header = f.readline().split()
            
        num_points = int(header[0])
        
        for _ in range(num_points):
            line = f.readline().split()
            if not line or line[0].startswith('#'): continue
            
            indices.append(int(line[0]))  # Keep the ID
            points.append((float(line[1]), float(line[2])))

    if not points:
        return [], []
    
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    
    scale = max(max_x - min_x, max_y - min_y)
    if scale == 0: scale = 1.0
    norm_points = [
        ((p[0] - min_x) / scale, (p[1] - min_y) / scale) 
        for p in points
    ]
    
    return norm_points, indices


def write_ele_file(filename, triangles, point_to_index):
    misses = sum(
        1 for v0, v1, v2 in triangles
        if point_to_index.get(v0, -1) == -1
           or point_to_index.get(v1, -1) == -1
           or point_to_index.get(v2, -1) == -1
    )
    if misses:
        raise ValueError(f"write_ele_file: {misses}/{len(triangles)} triangles have vertices not found in point_to_index.")

    with open(filename, 'w') as f:
        f.write(f"{len(triangles)} 3 0\n")
        for i, (v0, v1, v2) in enumerate(triangles, start=1):
            i0 = point_to_index[v0]
            i1 = point_to_index[v1]
            i2 = point_to_index[v2]
            f.write(f"{i}  {i0}  {i1}  {i2}\n")

def build_point_index_map(points, indices):
    return {p: idx for p, idx in zip(points, indices)}

def parse_node_filename(node_file):
    if node_file.endswith('.node'):
        return node_file[:-5]
    return node_file