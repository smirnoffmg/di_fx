"""Components inside components, and the name a module carries."""

from dataclasses import dataclass

from di_fx import App, Component, Invoke, Provide, Supply


@dataclass
class Config:
    port: int = 8000


class Database:
    def __init__(self, config: Config) -> None:
        self.config = config


def new_database(config: Config) -> Database:
    return Database(config)


class TestNesting:
    async def test_two_levels(self):
        app = App(Component(Supply(Config()), Provide(new_database)))

        assert isinstance(await app.resolve(Database), Database)

    async def test_three_levels(self):
        app = App(Component(Component(Supply(Config()), Provide(new_database))))

        assert isinstance(await app.resolve(Database), Database)

    async def test_five_levels(self):
        nested: Component = Component(Supply(Config()), Provide(new_database))
        for _ in range(4):
            nested = Component(nested)

        assert isinstance(await App(nested).resolve(Database), Database)

    async def test_modules_side_by_side_inside_a_component(self):
        config_module = Component("config", Supply(Config()))
        database_module = Component("database", Provide(new_database))

        app = App(Component(config_module, database_module))

        assert isinstance(await app.resolve(Database), Database)

    async def test_invokables_survive_nesting(self):
        seen: list[Database] = []

        def use(database: Database) -> None:
            seen.append(database)

        module = Component("database", Supply(Config()), Provide(new_database))
        app = App(Component(module, Invoke(use)))

        await app.start()
        await app.stop()

        assert len(seen) == 1


class TestComponentName:
    def test_a_component_can_be_named(self):
        module = Component("database", Provide(new_database))

        assert module.name == "database"

    def test_the_name_is_not_a_child_component(self):
        module = Component("database", Provide(new_database))

        assert len(module) == 1

    def test_the_name_is_optional(self):
        assert Component(Provide(new_database)).name is None
