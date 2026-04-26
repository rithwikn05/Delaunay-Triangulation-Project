
class QuarterEdge:
    __slots__ = ('next', 'data')

    def __init__(self):
        self.next = None
        self.data = None

class EdgeRecord:
    __slots__ = ('q',)

    def __init__(self):
        self.q = [QuarterEdge() for _ in range(4)]


class EdgeRef:
    __slots__ = ('_rec', '_r')

    def __init__(self, record, r=0):
        self._rec = record
        self._r = r % 4

    # Basic rotations

    @property
    def rot(self):
        return EdgeRef(self._rec, (self._r + 1) % 4)

    @property
    def sym(self):
        return EdgeRef(self._rec, (self._r + 2) % 4)

    @property
    def rot_inv(self):
        return EdgeRef(self._rec, (self._r + 3) % 4)

    # Onext and derived traversals
    @property
    def onext(self):
        return self._rec.q[self._r].next

    @onext.setter
    def onext(self, val):
        self._rec.q[self._r].next = val

    @property
    def oprev(self):
        return self.rot.onext.rot

    @property
    def lnext(self):
        return self.rot_inv.onext.rot

    @property
    def lprev(self):
        return self.onext.sym

    @property
    def rnext(self):
        return self.rot.onext.rot_inv

    @property
    def rprev(self):
        return self.sym.onext

    @property
    def dnext(self):
        return self.sym.onext.sym

    @property
    def dprev(self):
        return self.rot_inv.onext.rot_inv

    # Vertex Data
    @property
    def org(self):
        return self._rec.q[self._r].data

    @org.setter
    def org(self, val):
        self._rec.q[self._r].data = val

    @property
    def dest(self):
        return self._rec.q[(self._r + 2) % 4].data

    @dest.setter
    def dest(self, val):
        self._rec.q[(self._r + 2) % 4].data = val

    # Face DAG Data
    @property
    def left_face_data(self):
        return self._rec.q[(self._r + 1) % 4].data

    @left_face_data.setter
    def left_face_data(self, val):
        self._rec.q[(self._r + 1) % 4].data = val

    @property
    def right_face_data(self):
        return self._rec.q[(self._r + 3) % 4].data

    @right_face_data.setter
    def right_face_data(self, val):
        self._rec.q[(self._r + 3) % 4].data = val

    def equals(self, other):
        return self._rec is other._rec and self._r == other._r

    def __repr__(self):
        org = self.org
        dest = self.dest
        return f"EdgeRef(r={self._r}, org={org}, dest={dest})"


# Topological primitives: MakeEdge and Splice
def make_edge():
    rec = EdgeRecord()
    e0 = EdgeRef(rec, 0)
    e1 = EdgeRef(rec, 1)
    e2 = EdgeRef(rec, 2)
    e3 = EdgeRef(rec, 3)
    e0.onext = e0
    e2.onext = e2
    e1.onext = e3
    e3.onext = e1

    return e0

# Connects or disconnects two edges
def splice(a, b):
    alpha = a.onext.rot
    beta = b.onext.rot
    t1 = b.onext
    t2 = a.onext
    t3 = beta.onext
    t4 = alpha.onext
    a.onext = t1
    b.onext = t2
    alpha.onext = t3
    beta.onext = t4

# Creates a new edge between two vertices
def connect(a, b):
    e = make_edge()
    e.org = a.dest
    e.dest = b.org
    splice(e, a.lnext)
    splice(e.sym, b)
    return e

# Detaches an edge from its neighbors
def delete_edge(e):
    splice(e, e.oprev)
    splice(e.sym, e.sym.oprev)

# Rotates the edge and connects it to another two vertices
def swap(e):
    a = e.oprev
    b = e.sym.oprev
    splice(e, a)
    splice(e.sym, b)
    splice(e, a.lnext)
    splice(e.sym, b.lnext)
    e.org = a.dest
    e.dest = b.dest

# BFS that finds every edge in the triangulation
def all_edges(start_edge):
    visited = set()
    queue = [start_edge if start_edge._r == 0 else EdgeRef(start_edge._rec, 0)]
    result = []

    while queue:
        e = queue.pop()
        rec_id = id(e._rec)
        if rec_id in visited:
            continue
        visited.add(rec_id)
        result.append(EdgeRef(e._rec, 0))

        # Follow Onext rings for both primal directions
        for start in [EdgeRef(e._rec, 0), EdgeRef(e._rec, 2)]:
            cur = start.onext
            while not cur.equals(start):
                cid = id(cur._rec)
                if cid not in visited:
                    queue.append(EdgeRef(cur._rec, 0))
                cur = cur.onext

    return result

# Loops through all edges connected to a vertex
def edges_around_vertex(e):
    start = e
    yield e
    cur = e.onext
    while not cur.equals(start):
        yield cur
        cur = cur.onext

# Loops through three edges of a triangle
def edges_around_face(e):
    start = e
    yield e
    cur = e.lnext
    while not cur.equals(start):
        yield cur
        cur = cur.lnext