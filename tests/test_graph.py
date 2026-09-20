"""Flattening registrations into a graph, and reading it back."""

from dataclasses import dataclass

import pytest

from di_fx import (
    Component,
    DotGraph,
    Invoke,
    Lifecycle,
    Named,
    Provide,
    Shutdowner,
    Supply,
)
from di_fx.graph import flatten, type_name


@dataclass
class Config:
    port: int = 8000


class Database:
    pass


def new_database(config: Config) -> Database:
    return Database()


class TestFlatten:
    def test_registrations_are_indexed_by_type(self):
        graph = flatten(Supply(Config()), Provide(new_database), Invoke(lambda: None))

        assert Database in graph.providers
        assert Config in graph.values
        assert len(graph.invokables) == 1

    def test_components_are_walked_to_any_depth(self):
        graph = flatten(Component(Component(Component(Provide(new_database)))))

        assert Database in graph.providers

    def test_a_component_keeps_the_order_of_its_children(self):
        def first() -> int:
            return 1

        def second(value: int) -> str:
            return str(value)

        graph = flatten(Component(Provide(first), Provide(second)))

        assert graph.providers[str].dependencies == (int,)

    def test_an_unknown_registration_is_refused(self):
        with pytest.raises(ValueError, match="Unknown registration type"):
            flatten("not a registration")


class TestCanResolve:
    def test_providers_and_values_count(self):
        graph = flatten(Supply(Config()), Provide(new_database))

        assert graph.can_resolve(Database)
        assert graph.can_resolve(Config)

    def test_built_ins_count(self):
        graph = flatten()

        assert graph.can_resolve(Lifecycle)
        assert graph.can_resolve(Shutdowner)
        assert graph.can_resolve(DotGraph)

    def test_a_named_type_falls_back_to_its_base_type(self):
        graph = flatten(Provide(new_database))
        primary = Named("primary", Database)

        assert graph.can_resolve(primary)
        assert graph.provider_for(primary) is graph.providers[Database]

    def test_anything_else_does_not(self):
        assert not flatten().can_resolve(Database)
        assert flatten().provider_for(Database) is None


class TestTypeName:
    def test_a_plain_type_is_its_name(self):
        assert type_name(Database) == "Database"

    def test_a_named_type_carries_its_name(self):
        assert type_name(Named("primary", Database)) == "primary:Database"
