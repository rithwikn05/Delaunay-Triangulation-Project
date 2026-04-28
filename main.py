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
    loc_group.add_argument('--slow', action='store_true',
                           help='Walking point location (Guibas-Stolfi Section 10.3)')
    loc_group.add_argument('--fast', action='store_true', default=True,
                           help='History DAG point location (default)')

    order_group = parser.add_mutually_exclusive_group()
    order_group.add_argument('--ordered', action='store_true',
                             help='Insert vertices in file order')
    order_group.add_argument('--randomized', action='store_true', default=True,
                             help='Insert vertices in random order (default)')

    parser.add_argument('--seed', type=int, default=None,
                        help='Random seed for reproducibility')
    parser.add_argument('--verify', action='store_true',
                        help='Verify Delaunay condition after triangulation')

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

    mode_str = ("History DAG" if use_fast else "Walking") + " point location"
    order_str = "randomized" if use_randomized else "ordered"
    print(f"Mode: {mode_str}, {order_str} insertion")

    dt = DelaunayTriangulation()

    t0 = time.time()
    triangles = dt.triangulate(points, randomized=use_randomized, fast=use_fast)
    t1 = time.time()

    print(f"  {len(triangles)} triangles in {t1 - t0:.4f}s")

    if args.verify:
        ok, bad = dt.verify_delaunay()
        if ok:
            print("  Verification: PASSED (all edges satisfy Delaunay condition)")
        else:
            print(f"  Verification: FAILED ({len(bad)} bad edges)")
            for b in bad[:5]:
                print(f"    Edge ({b[0]},{b[1]}) violates InCircle with apex {b[2]}, opposite {b[3]}")

    coord_to_index = {p: idx for p, idx in zip(points, indices)}
    dedup_indices = [coord_to_index[p] for p in dt._points]
    point_to_index = build_point_index_map(dt._points, dedup_indices)

    base = parse_node_filename(node_file)
    ele_file = base + '.ele'
    write_ele_file(ele_file, triangles, point_to_index)
    print(f"Written: {ele_file}")


if __name__ == '__main__':
    main()