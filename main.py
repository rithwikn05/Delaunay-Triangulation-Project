import sys
import os
import time
import argparse

from io_utils import read_node_file, write_ele_file, build_point_index_map, parse_node_filename
from triangulation import DelaunayTriangulation


def main():
    parser = argparse.ArgumentParser(
        description='Incremental Delaunay Triangulation (Guibas-Stolfi)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument('input', help='Input .node file')

    loc_group = parser.add_mutually_exclusive_group()
    loc_group.add_argument('--slow', action='store_true')
    loc_group.add_argument('--fast', action='store_true', default=True)
    order_group = parser.add_mutually_exclusive_group()
    order_group.add_argument('--ordered', action='store_true')
    order_group.add_argument('--randomized', action='store_true', default=True)
    parser.add_argument('--seed', type=int, default=None)

    args = parser.parse_args()

    use_fast = not args.slow
    use_randomized = not args.ordered

    if args.seed is not None:
        import random
        random.seed(args.seed)
        print(f"Random seed: {args.seed}")

    node_file = args.input
    if not os.path.exists(node_file):
        if os.path.exists(node_file + '.node'):
            node_file = node_file + '.node'
        else:
            print(f"Error: file not found: {args.input}", file=sys.stderr)
            sys.exit(1)

    print(f"Reading: {node_file}")
    points, indices = read_node_file(node_file)
    print(f"  {len(points)} vertices")

    dt = DelaunayTriangulation()

    t0 = time.time()
    triangles = dt.triangulate(points, randomized=use_randomized, fast=use_fast)
    t1 = time.time()

    print(f"  {len(triangles)} triangles in {t1 - t0:.4f}s")

    coord_to_index = {p: idx for p, idx in zip(points, indices)}
    dedup_indices = [coord_to_index[p] for p in dt._points]
    point_to_index = build_point_index_map(dt._points, dedup_indices)

    base = parse_node_filename(node_file)
    ele_file = base + '.ele'
    write_ele_file(ele_file, triangles, point_to_index)
    print(f"Written: {ele_file}")

if __name__ == '__main__':
    main()