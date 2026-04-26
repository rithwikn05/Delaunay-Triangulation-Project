import random
import math
from quad_edge import (make_edge, splice, connect, delete_edge, swap, edges_around_face, EdgeRef)
from predicates import orient2d, incircle, right_of, on_edge

class DelaunayTriangulation:
    def __init__(self):
        self.start_edge = None
        self.dag = None
        self._bv_set = set()
        self._fast = False

    def triangulate(self, points, randomized=True, fast=True):
        if len(points) < 2: return []
        self._fast = fast
        
        seen = set()
        unique = [p for p in points if not (p in seen or seen.add(p))]
        points = unique

        self._init_bounding_triangle(points)
        order = list(points)
        if randomized: random.shuffle(order)

        for p in order:
            self._insert_site(p)
        return self._collect_triangles()

    def _init_bounding_triangle(self, points):
        xs, ys = [p[0] for p in points], [p[1] for p in points]
        cx, cy = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
        span = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
        R = span * 50.0
        v0, v1, v2 = (cx, cy + 2*R), (cx - R*math.sqrt(3), cy - R), (cx + R*math.sqrt(3), cy - R)
        self._bv_set = {v0, v1, v2}

        ea, eb, ec = make_edge(), make_edge(), make_edge()
        splice(ea.sym, eb); splice(eb.sym, ec); splice(ec.sym, ea)
        ea.org, ea.dest, eb.org, eb.dest, ec.org, ec.dest = v0, v1, v1, v2, v2, v0
        self.start_edge = ea.sym

        if self._fast:
            from history_dag import HistoryDAG
            self.dag = HistoryDAG(v1, v0, v2, self.start_edge)
            for e in edges_around_face(self.start_edge): 
                e.left_face_data = self.dag.root

    def _locate(self, x):
        e = self.start_edge
        
        # Fast mode
        if self._fast and self.dag:
            leaf = self.dag.locate(x)
            if leaf and leaf.edge_ref:
                e = leaf.edge_ref
        
        # Walking mode
        for _ in range(100_000):
            if x == e.org or x == e.dest: return e
            if right_of(x, e): e = e.sym
            elif not right_of(x, e.onext): e = e.onext
            elif not right_of(x, e.dprev): e = e.dprev
            else: return e
        return e

    def _insert_site(self, x):
        e = self._locate(x)
        if x == e.org or x == e.dest: return
        
        old_nodes = []
        if self._fast and e.left_face_data:
            old_nodes.append(e.left_face_data)

        if on_edge(x, e):
            if self._fast and e.sym.left_face_data:
                old_nodes.append(e.sym.left_face_data)
            e = e.oprev
            delete_edge(e.onext)

        base = make_edge()
        first = e.org
        base.org, base.dest = first, x
        splice(base, e)
        self.start_edge = base.sym
        
        base = connect(e, base.sym)
        e = base.oprev
        while e.dest != first:
            base = connect(e, base.sym)
            e = base.oprev

        if self._fast and old_nodes: 
            self._dag_record_fan(old_nodes, x, first)

        suspect = self._star_boundary(self.start_edge, x)
        while suspect:
            be = suspect.pop()
            
            if not hasattr(be, 'lnext'): continue 
            if be.lnext.dest != x:
                be = be.sym
                if be.lnext.dest != x: continue
            
            t = be.oprev
            if not right_of(t.dest, be) or incircle(be.org, t.dest, be.dest, x) <= 0:
                continue

            e1 = be.oprev
            e2 = be.sym.onext.sym

            if self._fast: self._dag_record_flip_before(be, x, t)
            swap(be)
            if self._fast: self._dag_record_flip_after(be)
            
            suspect.append(e1)
            suspect.append(e2)

    def _star_boundary(self, x_spoke, x):
        res, cur = [], x_spoke
        while True:
            res.append(cur.sym.onext)
            cur = cur.onext
            if cur.equals(x_spoke): break
        return res

    def _ccw3(self, a, b, c): 
        return (a, b, c) if orient2d(a, b, c) >= 0 else (a, c, b)

    def _dag_record_fan(self, old_nodes, x, first):
        spokes, cur = [], self.start_edge
        while True:
            spokes.append(cur)
            cur = cur.onext
            if cur.equals(self.start_edge): break
        
        new_tris = []
        for sp in spokes:
            f = list(edges_around_face(sp))
            if len(f) == 3:
                tri = self._ccw3(f[0].org, f[1].org, f[2].org)
                new_tris.append((*tri, sp))
        
        children = self.dag.split_triangle(old_nodes, new_tris)
        for i, tri_data in enumerate(new_tris):
            for fe in edges_around_face(tri_data[3]): 
                fe.left_face_data = children[i]

    def _dag_record_flip_before(self, e, x, t):
        self._flip_node_l = e.left_face_data
        self._flip_node_r = e.sym.left_face_data
        org, dest, apex_l, apex_r = e.org, e.dest, e.lnext.dest, t.dest
        self._flip_new_a = self._ccw3(org, apex_r, apex_l)
        self._flip_new_b = self._ccw3(dest, apex_l, apex_r)

    def _dag_record_flip_after(self, e):
        if not getattr(self, '_flip_node_l', None) or not getattr(self, '_flip_node_r', None): 
            return
        t1, t2 = self._flip_new_a, self._flip_new_b
        
        # CORRECTED MAP: t2 belongs to e, t1 belongs to e.sym
        children = self.dag.flip_triangles(self._flip_node_l, self._flip_node_r, [(*t2, e), (*t1, e.sym)])
        for i, eref in enumerate([e, e.sym]):
            for fe in edges_around_face(eref): 
                fe.left_face_data = children[i]

    def _collect_triangles(self):
        visited, result = set(), []
        for e in self._all_reachable_edges():
            f = list(edges_around_face(e))
            if len(f) == 3:
                v = [fi.org for fi in f]
                if not any(vi in self._bv_set for vi in v):
                    key = tuple(sorted(v))
                    if key not in visited:
                        visited.add(key)
                        result.append(tuple(v) if orient2d(*v) > 0 else (v[0], v[2], v[1]))
        return result

    def _all_reachable_edges(self):
        visited, queue, result = set(), [self.start_edge], []
        while queue:
            e = queue.pop()
            if id(e._rec) in visited: continue
            visited.add(id(e._rec))
            e0 = EdgeRef(e._rec, 0)
            result.extend([e0, e0.sym])
            for base in (e0, e0.sym):
                cur = base.onext
                while not cur.equals(base):
                    if id(cur._rec) not in visited: queue.append(cur)
                    cur = cur.onext
        return result

    def verify_delaunay(self):
        bv = self._bv_set
        bad = []
        visited = set()

        for e in self._all_reachable_edges():
            rid = id(e._rec)
            if rid in visited:
                continue
            visited.add(rid)

            if e.org in bv or e.dest in bv:
                continue

            apex_l = e.lnext.dest
            apex_r = e.sym.lnext.dest

            if apex_l is None or apex_r is None:
                continue
            if apex_l in bv or apex_r in bv:
                continue

            if incircle(apex_l, e.org, e.dest, apex_r) > 0:
                bad.append((e.org, e.dest, apex_l, apex_r))

        return len(bad) == 0, bad