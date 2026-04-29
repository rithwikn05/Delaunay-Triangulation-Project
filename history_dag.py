from predicates import orient2d

class DAGNode:
    __slots__ = ('vertices', 'children', 'edge_ref')

    def __init__(self, v0, v1, v2, edge_ref=None):
        self.vertices = (v0, v1, v2)
        self.children = []
        self.edge_ref = edge_ref

    def is_leaf(self):
        return not self.children

    def contains_point(self, p):
        v0, v1, v2 = self.vertices
        return (orient2d(v0, v1, p) >= 0 and 
                orient2d(v1, v2, p) >= 0 and 
                orient2d(v2, v0, p) >= 0)


class HistoryDAG:
    def __init__(self, v0, v1, v2, edge_ref):
        self.root = DAGNode(v0, v1, v2, edge_ref)
        self._leaf_map = {}
        self._leaf_map[self._key(v0, v1, v2)] = self.root

    @staticmethod
    def _key(v0, v1, v2):
        return tuple(sorted([v0, v1, v2]))

    def get_node_for_triangle(self, v0, v1, v2):
        return self._leaf_map.get(self._key(v0, v1, v2))

    def _make_child(self, v0, v1, v2, edge_ref):
        node = DAGNode(v0, v1, v2, edge_ref)
        self._leaf_map[self._key(v0, v1, v2)] = node
        return node

    def _remove_leaf(self, v0, v1, v2):
        self._leaf_map.pop(self._key(v0, v1, v2), None)

    def split_triangle(self, parent_nodes, new_triangles):
        if not isinstance(parent_nodes, list):
            parent_nodes = [parent_nodes]

        children = []
        for (nv0, nv1, nv2, eref) in new_triangles:
            child = self._make_child(nv0, nv1, nv2, eref)
            children.append(child)

        for p in parent_nodes:
            if p:
                self._remove_leaf(*p.vertices)
                p.children.extend(children)
        return children

    def flip_triangles(self, node_a, node_b, new_triangles):
        children = []
        for (nv0, nv1, nv2, eref) in new_triangles:
            child = self._make_child(nv0, nv1, nv2, eref)
            children.append(child)

        if node_a:
            self._remove_leaf(*node_a.vertices)
            node_a.children.extend(children)
        if node_b:
            self._remove_leaf(*node_b.vertices)
            node_b.children.extend(children)
        return children

    def locate(self, p):
        node = self.root
        while node.children:
            found = False
            for child in node.children:
                if child.contains_point(p):
                    node = child
                    found = True
                    break
            if not found:
                for i, c in enumerate(node.children):
                    print(f"  Child {i} {c.vertices} -> CCW: {orient2d(*c.vertices) > 0}")
                return node, -1
        return node, 0

    def all_leaves(self):
        return list(self._leaf_map.values())