"""Rendering the graph for Graphviz."""

from dataclasses import dataclass
from typing import Annotated

from di_fx import App, DotGraph, Invoke, Named, Provide, Supply


@dataclass
class Config:
    port: int = 8000


class Database:
    pass


class Worker:
    pass


def new_database(config: Config) -> Database:
    return Database()


def new_worker(database: Database) -> Worker:
    return Worker()


def graph_of(*registrations):
    app = App(*registrations, validate=False)
    return DotGraph(app.graph.providers, app.graph.values)


class TestDotGraph:
    def test_every_type_becomes_a_node(self):
        dot = graph_of(Supply(Config()), Provide(new_database, new_worker)).to_dot()

        assert '"Config";' in dot
        assert '"Database";' in dot
        assert '"Worker";' in dot

    def test_a_dependency_becomes_an_edge_pointing_at_the_dependent(self):
        dot = graph_of(Supply(Config()), Provide(new_database)).to_dot()

        assert '"Config" -> "Database";' in dot

    def test_the_output_is_a_digraph(self):
        dot = graph_of(Provide(new_database)).to_dot()

        assert dot.startswith("digraph DependencyGraph {")
        assert dot.rstrip().endswith("}")

    def test_an_annotated_alias_keeps_its_tag(self):
        Dsn = Annotated[str, "dsn"]

        def new_dsn() -> Dsn:
            return "postgresql://localhost"

        assert '"str_dsn";' in graph_of(Provide(new_dsn)).to_dot()

    def test_a_named_type_is_rendered(self):
        Primary = Named("primary", Database)

        def new_primary() -> Primary:
            return Database()

        dot = graph_of(Provide(new_primary)).to_dot()

        assert "primary" in dot

    def test_str_is_the_dot_output(self):
        graph = graph_of(Provide(new_database))

        assert str(graph) == graph.to_dot()

    def test_repr_counts_nodes_and_edges(self):
        graph = graph_of(Supply(Config()), Provide(new_database))

        assert repr(graph) == "DotGraph(nodes=2, edges=1)"


class TestInjection:
    async def test_dotgraph_can_be_injected(self):
        seen = []

        def inspect(graph: DotGraph) -> None:
            seen.append(graph.to_dot())

        await App(Supply(Config()), Provide(new_database), Invoke(inspect)).start()

        assert '"Config" -> "Database";' in seen[0]
