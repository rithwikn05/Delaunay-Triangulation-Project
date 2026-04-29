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
        self._points = []

    def triangulate(self, points, randomized=True, fast=True):
        if len(points) < 2:
            self._points = []
            return []

        self._fast = fast

        seen = set()
        unique = [p for p in points if not (p in seen or seen.add(p))]
        self._points = unique

        self._init_bounding_triangle(unique)

        order = list(unique)
        if randomized:
            random.shuffle(order)

        for p in order:
            self._insert_site(p)

        return self._collect_triangles()

    def _set_face_data(self, edge_ref, node):
        curr = edge_ref
        for _ in range(3):
            curr._rec.q[(curr._r + 1) & 3].data = node
            curr = curr.lnext
        node.edge_ref = edge_ref

    def _init_bounding_triangle(self, points):
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        cx = (min(xs) + max(xs)) / 2.0
        cy = (min(ys) + max(ys)) / 2.0
        span = max(max(xs) - min(xs), max(ys) - min(ys)) or 1.0
        R = span * 50.0

        v0 = (cx, cy + 2 * R)
        v1 = (cx - R * math.sqrt(3), cy - R)
        v2 = (cx + R * math.sqrt(3), cy - R)
        self._bv_set = {v0, v1, v2}

        ea, eb, ec = make_edge(), make_edge(), make_edge()
        splice(ea.sym, eb)
        splice(eb.sym, ec)
        splice(ec.sym, ea)
        ea.org, ea.dest = v0, v1
        eb.org, eb.dest = v1, v2
        ec.org, ec.dest = v2, v0
        self.start_edge = ea.sym

        if self._fast:
            from history_dag import HistoryDAG
            self.dag = HistoryDAG(v1, v0, v2, self.start_edge)
            for e in [ea, eb, ec]:
                self._set_face_data(e, self.dag.root)

    def _locate(self, x):
        e = self.start_edge
        dag_depth = 0
        dag_status = 0

        # The fast logic
        if self._fast and self.dag:
            leaf, dag_status = self.dag.locate(x)
            if leaf and leaf.edge_ref:
                e = leaf.edge_ref
                if e._r & 1: e = EdgeRef(e._rec, 0)

        walk_steps = 0
        # The Walking Loop
        while True:
            walk_steps += 1
            if x == e.org or x == e.dest:
                break
            if right_of(x, e):
                e = e.sym
            elif not right_of(x, e.onext):
                e = e.onext
            elif not right_of(x, e.dprev):
                e = e.dprev
            else:
                break
            
        return e

    def _insert_site(self, x):
        e = self._locate(x)
        if x == e.org or x == e.dest:
            return

        old_nodes = []
        if self._fast and e.left_face_data:
            old_nodes.append(e.left_face_data)
        
        is_on_edge = on_edge(x, e)
        if is_on_edge and self._fast and e.sym.left_face_data:
            old_nodes.append(e.sym.left_face_data)

        if is_on_edge:
            e_temp = e.oprev
            delete_edge(e.onext)
            e = e_temp

        base = make_edge()
        first_org = e.org
        base.org, base.dest = first_org, x
        splice(base, e)
        self.start_edge = base.sym

        base = connect(e, base.sym)
        e = base.oprev
        while e.dest != first_org:
            base = connect(e, base.sym)
            e = base.oprev

        if self._fast and old_nodes:
            new_tris_data = []
            curr = self.start_edge
            start_curr = curr
            while True:
                face_edges = list(edges_around_face(curr.sym))
                if len(face_edges) == 3:
                    t_v = (face_edges[0].org, face_edges[1].org, face_edges[2].org)
                    new_tris_data.append((*t_v, curr.sym))
                curr = curr.onext
                if curr.equals(start_curr):
                    break
            
            children = self.dag.split_triangle(old_nodes, new_tris_data)
            for i, (v0, v1, v2, eref) in enumerate(new_tris_data):
                for fe in edges_around_face(eref):
                    self._set_face_data(fe, children[i])

        suspect = self._star_boundary(self.start_edge, x)
        while suspect:
            be = suspect.pop()

            if not hasattr(be, 'lnext'):
                continue
            if be.lnext.dest != x:
                be = be.sym
                if be.lnext.dest != x:
                    continue

            t = be.oprev
            if not right_of(t.dest, be) or incircle(be.org, t.dest, be.dest, x) <= 0:
                continue

            e1 = be.oprev
            e2 = be.sym.onext.sym

            if self._fast:
                self._dag_record_flip_before(be, x, t)
            swap(be)
            if self._fast:
                self._dag_record_flip_after(be)

            suspect.append(e1)
            suspect.append(e2)

    def _star_boundary(self, x_spoke, x):
        res = []
        cur = x_spoke
        while True:
            res.append(cur.sym.onext)
            cur = cur.onext
            if cur.equals(x_spoke):
                break
        return res

    def _ccw3(self, a, b, c):
        return (a, b, c) if orient2d(a, b, c) >= 0 else (a, c, b)

    def _dag_record_fan(self, old_nodes, x, first):
        new_tris_data = []
        curr = self.start_edge
        start_e = curr
        
        while True:
            e_left = curr.sym 
            v0, v1, v2 = e_left.org, e_left.dest, e_left.lnext.dest
            
            new_tris_data.append((v0, v1, v2, e_left))
            
            curr = curr.onext
            if curr.equals(start_e):
                break

        children = self.dag.split_triangle(old_nodes, new_tris_data)
        
        for i, (v0, v1, v2, eref) in enumerate(new_tris_data):
            self._set_face_data(eref, children[i])

    def _dag_record_flip_before(self, e, x, t):
        self._flip_node_l = e.left_face_data
        self._flip_node_r = e.sym.left_face_data
        self.f_org = e.org
        self.f_dest = e.dest
        self.f_apex_l = e.lnext.dest
        self.f_apex_r = e.sym.lnext.dest

    def _dag_record_flip_after(self, e):
        if not self._flip_node_l or not self._flip_node_r: return
    
        t1 = (self.f_org, self.f_apex_r, self.f_apex_l)
        t2 = (self.f_dest, self.f_apex_l, self.f_apex_r)
        t1 = t1 if orient2d(*t1) > 0 else (t1[0], t1[2], t1[1])
        t2 = t2 if orient2d(*t2) > 0 else (t2[0], t2[2], t2[1])
        new_tris = [(*t1, e), (*t2, e.sym)]
        
        children = self.dag.flip_triangles(self._flip_node_l, self._flip_node_r, new_tris)
        
        for i, (_, _, _, eref) in enumerate(new_tris):
            self._set_face_data(eref, children[i])

    def _collect_triangles(self):
        visited = set()
        result = []
        for e in self._all_reachable_edges():
            f = list(edges_around_face(e))
            if len(f) == 3:
                v = [fi.org for fi in f]
                if not any(vi in self._bv_set for vi in v):
                    key = tuple(sorted(v))
                    if key not in visited:
                        visited.add(key)
                        result.append(
                            tuple(v) if orient2d(*v) > 0 else (v[0], v[2], v[1])
                        )
        return result

    def _all_reachable_edges(self):
        visited = set()
        queue = [self.start_edge]
        result = []
        while queue:
            e = queue.pop()
            if id(e._rec) in visited:
                continue
            visited.add(id(e._rec))
            e0 = EdgeRef(e._rec, 0)
            result.extend([e0, e0.sym])
            for base in (e0, e0.sym):
                cur = base.onext
                while not cur.equals(base):
                    if id(cur._rec) not in visited:
                        queue.append(cur)
                    cur = cur.onext
        return result