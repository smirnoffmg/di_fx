"""Graph validation: what counts as satisfiable, duplicates, cycles."""

from dataclasses import dataclass

import pytest

from di_fx import (
    App,
    Component,
    DotGraph,
    DuplicateProviderError,
    Invoke,
    Lifecycle,
    Provide,
    Shutdowner,
    Supply,
    ValidationError,
)


@dataclass
class Config:
    port: int = 8000


class Database:
    def __init__(self, config: Config) -> None:
        self.config = config


def new_database(config: Config) -> Database:
    return Database(config)


class TestSatisfiability:
    """Everything the resolver can supply has to count as satisfied."""

    def test_supplied_value_satisfies_a_dependency(self):
        app = App(Supply(Config()), Provide(new_database))

        app.validate()

    def test_lifecycle_satisfies_a_dependency(self):
        def new_service(lifecycle: Lifecycle) -> Database:
            return Database(Config())

        App(Provide(new_service)).validate()

    def test_shutdowner_and_dotgraph_satisfy_a_dependency(self):
        def new_service(shutdowner: Shutdowner, graph: DotGraph) -> Database:
            return Database(Config())

        App(Provide(new_service)).validate()

    def test_missing_dependency_is_reported(self):
        app = App(Provide(new_database))

        with pytest.raises(ValidationError) as exc_info:
            app.validate()

        assert len(exc_info.value.errors) == 1
        assert "Config" in exc_info.value.errors[0]

    def test_invokable_dependencies_are_validated(self):
        def use(database: Database) -> None:
            pass

        app = App(Invoke(use))

        with pytest.raises(ValidationError) as exc_info:
            app.validate()

        assert "Database" in exc_info.value.errors[0]


class TestDuplicates:
    def test_two_providers_for_the_same_type_are_rejected(self):
        def one() -> int:
            return 1

        def two() -> int:
            return 2

        with pytest.raises(DuplicateProviderError, match="int"):
            Provide(one, two)

    def test_duplicate_across_components_is_rejected(self):
        def one() -> int:
            return 1

        def two() -> int:
            return 2

        with pytest.raises(DuplicateProviderError, match="int"):
            App(Provide(one), Provide(two))


class TestCycles:
    def test_direct_cycle_is_reported_once_with_the_path(self):
        class A:
            pass

        class B:
            pass

        def new_a(b: B) -> A:
            return A()

        def new_b(a: A) -> B:
            return B()

        app = App(Provide(new_a, new_b))

        with pytest.raises(ValidationError) as exc_info:
            app.validate()

        errors = exc_info.value.errors
        assert len(errors) == 1, errors
        assert "A" in errors[0] and "B" in errors[0]

    def test_self_dependency_is_a_cycle(self):
        def new_thing(other: int) -> int:
            return other

        with pytest.raises(ValidationError):
            App(Provide(new_thing)).validate()

    def test_diamond_is_not_a_cycle(self):
        class Leaf:
            pass

        class Left:
            pass

        class Right:
            pass

        class Root:
            pass

        def new_leaf() -> Leaf:
            return Leaf()

        def new_left(leaf: Leaf) -> Left:
            return Left()

        def new_right(leaf: Leaf) -> Right:
            return Right()

        def new_root(left: Left, right: Right) -> Root:
            return Root()

        App(Provide(new_leaf, new_left, new_right, new_root)).validate()

    def test_only_the_nodes_on_the_cycle_are_named(self):
        class Upstream:
            pass

        class A:
            pass

        class B:
            pass

        def new_a(b: B) -> A:
            return A()

        def new_b(a: A) -> B:
            return B()

        def new_upstream(a: A) -> Upstream:
            return Upstream()

        app = App(Provide(new_a, new_b, new_upstream))

        with pytest.raises(ValidationError) as exc_info:
            app.validate()

        assert "Upstream" not in exc_info.value.errors[0]

    async def test_resolver_reports_a_cycle_instead_of_recursing(self):
        class A:
            pass

        class B:
            pass

        def new_a(b: B) -> A:
            return A()

        def new_b(a: A) -> B:
            return B()

        app = App(Provide(new_a, new_b), validate=False)

        with pytest.raises(ValidationError, match="Circular"):
            await app.resolve(A)


class TestAutomaticValidation:
    async def test_start_validates_the_graph(self):
        def use(database: Database) -> None:
            pass

        app = App(Invoke(use))

        with pytest.raises(ValidationError):
            await app.start()

    async def test_validation_can_be_switched_off(self):
        def use(database: Database) -> None:
            pass

        app = App(Invoke(use), validate=False)

        # Without validation the failure surfaces later, from the resolver.
        with pytest.raises(ValidationError, match="No provider"):
            await app.start()


class TestValidateAndResolveAgree:
    """A graph validate() accepts must resolve, and vice versa."""

    @pytest.mark.parametrize(
        "build",
        [
            lambda: App(Supply(Config()), Provide(new_database)),
            lambda: App(Provide(new_database)),
            lambda: App(Component(Supply(Config())), Component(Provide(new_database))),
        ],
    )
    async def test_agreement(self, build):
        validated = True
        try:
            build().validate()
        except ValidationError:
            validated = False

        resolved = True
        try:
            await build().resolve(Database)
        except ValidationError:
            resolved = False

        assert validated == resolved
