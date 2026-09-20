"""The registration records: what they accept and what they refuse."""

from collections.abc import AsyncIterator
from typing import Annotated

import pytest

from di_fx import Annotate, As, Component, Invoke, Provide, Supply
from di_fx.registrations import dependencies_of


class Database:
    pass


class TestProvide:
    def test_a_constructor_is_keyed_by_its_return_type(self):
        def new_database() -> Database:
            return Database()

        provide = Provide(new_database)

        assert Database in provide
        assert len(provide) == 1
        assert provide[Database].constructor is new_database

    def test_parameters_become_dependencies_in_order(self):
        def new_database(host: str, port: int) -> Database:
            return Database()

        assert Provide(new_database)[Database].dependencies == (str, int)

    def test_a_missing_return_annotation_is_refused(self):
        def new_database():
            return Database()

        with pytest.raises(ValueError, match="return type annotation"):
            Provide(new_database)

    def test_a_missing_parameter_annotation_is_refused(self):
        def new_database(host) -> Database:
            return Database()

        with pytest.raises(ValueError, match="type annotation"):
            Provide(new_database)

    def test_a_resource_is_also_registered_under_what_it_yields(self):
        async def new_database() -> AsyncIterator[Database]:
            yield Database()

        provide = Provide(new_database)

        assert Database in provide
        assert AsyncIterator[Database] in provide

    def test_an_annotated_alias_does_not_claim_its_underlying_type(self):
        Dsn = Annotated[str, "dsn"]

        def new_dsn() -> Dsn:
            return "postgresql://localhost"

        provide = Provide(new_dsn)

        assert Dsn in provide
        assert str not in provide

    def test_as_registers_the_interface_too(self):
        class Storage:
            pass

        def new_database() -> Database:
            return Database()

        provide = Provide(Annotate(new_database, As(Storage)))

        assert Database in provide
        assert Storage in provide

    def test_an_unregistered_type_raises(self):
        with pytest.raises(KeyError):
            Provide()[Database]


class TestSupply:
    def test_a_value_is_keyed_by_its_own_type(self):
        supply = Supply("dsn", 8000)

        assert supply[str] == "dsn"
        assert supply[int] == 8000
        assert len(supply) == 2

    def test_an_unsupplied_type_raises(self):
        with pytest.raises(KeyError):
            Supply()[str]


class TestInvoke:
    def test_functions_keep_their_names_and_dependencies(self):
        def setup(database: Database) -> None:
            pass

        invoke = Invoke(setup)

        assert len(invoke) == 1
        assert invoke.invokables[0].name == "setup"
        assert invoke.invokables[0].dependencies == (Database,)


class TestComponent:
    def test_children_are_kept_in_order(self):
        provide, supply = Provide(), Supply()
        component = Component(provide, supply)

        assert list(component) == [provide, supply]
        assert len(component) == 2

    def test_a_leading_string_is_the_name(self):
        component = Component("database", Provide())

        assert component.name == "database"
        assert len(component) == 1

    def test_the_name_can_also_be_a_keyword(self):
        assert Component(Provide(), name="database").name == "database"


class TestDependenciesOf:
    def test_self_is_not_a_dependency(self):
        class Service:
            def __init__(self, database: Database) -> None:
                pass

        assert dependencies_of(Service.__init__) == (Database,)
