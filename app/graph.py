from __future__ import annotations


from app.models import DAGDefinition, NodeDefinition, WorkflowDefinition


class WorkflowGraph:
    def __init__(self, definition: WorkflowDefinition) -> None:
        self.definition = definition
        self.nodes: dict[str, NodeDefinition] = {
            node.id: node for node in definition.dag.nodes
        }
        self.adjacency: dict[str, list[str]] = {node_id: [] for node_id in self.nodes}
        self.parents: dict[str, list[str]] = {node_id: [] for node_id in self.nodes}
        self.in_degree: dict[str, int] = {node_id: 0 for node_id in self.nodes}
        self._build()

    def _build(self) -> None:
        for node in self.definition.dag.nodes:
            for dep in node.dependencies:
                self.adjacency.setdefault(dep, []).append(node.id)
                self.parents[node.id].append(dep)
                self.in_degree[node.id] += 1

    @property
    def roots(self) -> list[str]:
        return [node_id for node_id, degree in self.in_degree.items() if degree == 0]


def validate_workflow(definition: WorkflowDefinition) -> WorkflowGraph:
    _ensure_dependencies_exist(definition.dag)
    graph = WorkflowGraph(definition)
    _ensure_acyclic(graph)
    return graph


def _ensure_dependencies_exist(dag: DAGDefinition) -> None:
    node_ids: set[str] = {node.id for node in dag.nodes}
    for node in dag.nodes:
        for dep in node.dependencies:
            if dep not in node_ids:
                raise ValueError(f"Node {node.id} references missing dependency {dep}")


def _ensure_acyclic(graph: WorkflowGraph) -> None:
    visited: set[str] = set()
    stack: set[str] = set()

    def dfs(node_id: str) -> None:
        if node_id in stack:
            raise ValueError(f"Cycle detected involving node {node_id}")
        if node_id in visited:
            return
        visited.add(node_id)
        stack.add(node_id)
        for child in graph.adjacency.get(node_id, []):
            dfs(child)
        stack.remove(node_id)

    for node_id in graph.nodes:
        if node_id not in visited:
            dfs(node_id)
