"""
Dependency graph visualization for di_fx.

This module provides the DotGraph class that can generate
DOT format output for visualizing dependency relationships.
"""

from typing import Any


class DotGraph:
    """Represents a dependency graph that can be visualized in DOT format.

    This is automatically provided by di_fx to any function that requests it.
    Similar to Uber-Fx's fx.DotGraph.
    """

    def __init__(self, providers: dict[type[Any], Any], values: dict[type[Any], Any]):
        """Initialize the dependency graph.

        Args:
            providers: Dictionary of type -> provider mappings
            values: Dictionary of type -> value mappings
        """
        self._providers = providers
        self._values = values
        self._nodes: set[str] = set()
        self._edges: list[tuple[str, str]] = []
        self._build_graph()

    def _build_graph(self) -> None:
        """Build the internal graph representation."""
        # Add all nodes (types)
        for provider_type in self._providers:
            self._nodes.add(self._type_to_node_id(provider_type))

        for value_type in self._values:
            self._nodes.add(self._type_to_node_id(value_type))

        # Add edges (dependencies)
        for provider_type, provider in self._providers.items():
            # Check if provider has dependencies attribute
            if hasattr(provider, "dependencies") and provider.dependencies:
                for dep_type in provider.dependencies:
                    self._edges.append(
                        (
                            self._type_to_node_id(dep_type),
                            self._type_to_node_id(provider_type),
                        )
                    )

    def _type_to_node_id(self, type_: type[Any]) -> str:
        """Convert a Python type to a valid DOT node ID."""
        # Handle Annotated types specially
        if hasattr(type_, "__name__") and type_.__name__ == "Annotated":
            # For Annotated[T, metadata], use a combination of base type and metadata
            args = getattr(type_, "__args__", [])
            metadata = getattr(type_, "__metadata__", ())

            if args and metadata:
                base_type = args[0]
                base_name = getattr(base_type, "__name__", str(base_type))
                # Create a meaningful name from the metadata
                if isinstance(metadata, tuple) and len(metadata) > 0:
                    meta = metadata[0]
                    if isinstance(meta, str):
                        # Remove quotes and special characters for DOT compatibility
                        clean_metadata = meta.replace('"', "").replace("'", "")
                        result = f"{base_name}_{clean_metadata}"
                    else:
                        result = f"{base_name}_{str(meta)}"
                    return result
                else:
                    return f"{base_name}_unknown"
            else:
                return "Annotated_unknown"

        # Regular types
        name = type_.__name__ if hasattr(type_, "__name__") else str(type_)
        return name.replace(".", "_").replace("<", "_").replace(">", "_")

    def to_dot(self) -> str:
        """Generate DOT format representation of the dependency graph.

        Returns:
            String in DOT format that can be used with Graphviz
        """
        lines = ["digraph DependencyGraph {"]
        lines.append("  rankdir=TB;")
        lines.append("  node [shape=box, style=filled, fillcolor=lightblue];")
        lines.append("  edge [color=gray];")
        lines.append("")

        # Add nodes
        for node in sorted(self._nodes):
            lines.append(f'  "{node}";')

        lines.append("")

        # Add edges
        for from_node, to_node in self._edges:
            lines.append(f'  "{from_node}" -> "{to_node}";')

        lines.append("}")
        return "\n".join(lines)

    def __str__(self) -> str:
        """String representation returns DOT format."""
        return self.to_dot()

    def __repr__(self) -> str:
        """Detailed representation for debugging."""
        return f"DotGraph(nodes={len(self._nodes)}, edges={len(self._edges)})"
