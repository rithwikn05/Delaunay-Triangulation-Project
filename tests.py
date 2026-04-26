"""
Usage:
    python test_delaunay.py [options]

Options:
    --node-dir DIR   Directory containing .node files (default: same dir as script)
    --src-dir DIR    Directory containing .py source files (default: same dir as script)
    --skip-large     Skip ttimeu100000 and ttimeu1000000
    --skip-slow      Skip slow-mode runs
    --seed N         Fix random seed (default: 42)
"""

import sys
import os
import time
import argparse
import subprocess

MODES = [
    ("fast  + randomized", ["--fast",  "--randomized"]),
    ("fast  + ordered",    ["--fast",  "--ordered"]),
    ("slow  + randomized", ["--slow",  "--randomized"]),
    ("slow  + ordered",    ["--slow",  "--ordered"]),
]


def _count_points(node_file):
    with open(node_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                return int(line.split()[0])
    return 0


def _run_main(src_dir, node_file, flags, timeout=1800):
    cmd = [sys.executable, os.path.join(src_dir, "main.py")] + flags + [node_file]
    t0 = time.time()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, time.time() - t0, False, r.stderr
    except subprocess.TimeoutExpired:
        return -1, timeout, True, ""


def run_timing_test(src_dir, node_file, seed=42, skip_slow=False):
    n_pts = _count_points(node_file)
    fname = os.path.basename(node_file)
    print(f"\n{fname}  ({n_pts} points)")
    print(f"  {'Mode':<25} {'Time':>10}  Status")

    for label, flags in MODES:
        if skip_slow and "--slow" in flags:
            print(f"  {label:<25} {'—':>10}  skipped")
            continue

        rc, elapsed, timed_out, stderr = _run_main(src_dir, node_file, flags + [f"--seed={seed}"])

        if timed_out:
            status = "timed out"
        elif rc != 0:
            status = f"crashed (rc={rc})"
        else:
            status = "ok"

        print(f"  {label:<25} {elapsed:>9.3f}s  {status}")
        if rc != 0 and stderr:
            print(stderr)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--node-dir",   default=None)
    parser.add_argument("--src-dir",    default=None)
    parser.add_argument("--skip-large", action="store_true")
    parser.add_argument("--skip-slow",  action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir  = args.src_dir  or script_dir
    node_dir = args.node_dir or script_dir

    timing_files = [
        ("ttimeu10000.node",   False),
        ("ttimeu100000.node",  args.skip_large),
        ("ttimeu1000000.node", args.skip_large),
    ]

    for fname, skip in timing_files:
        path = os.path.join(node_dir, fname)
        if not os.path.exists(path):
            print(f"Not found, skipping: {fname}")
            continue
        if skip:
            print(f"Skipping (--skip-large): {fname}")
            continue
        run_timing_test(src_dir, path, seed=args.seed, skip_slow=args.skip_slow)


if __name__ == "__main__":
    main()