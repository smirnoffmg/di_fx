"""What an error tells you about where it happened.

A dependency container is only as good as the message it gives when the graph is
wrong, because that is the moment the indirection it introduced has to pay for
itself.
"""

import pytest

from di_fx import App, Component, Invoke, MissingProviderError, Provide, ValidationError


class Config:
    pass


class Database:
    def __init__(self, config: Config) -> None:
        self.config = config


class Worker:
    def __init__(self, database: Database) -> None:
        self.database = database


def new_database(config: Config) -> Database:
    return Database(config)


def new_worker(database: Database) -> Worker:
    return Worker(database)


def run(worker: Worker) -> None:
    pass


class TestResolutionChain:
    async def test_the_message_names_the_missing_type(self):
        app = App(Provide(new_database, new_worker), validate=False)

        with pytest.raises(MissingProviderError) as exc_info:
            await app.resolve(Worker)

        assert "Config" in str(exc_info.value)

    async def test_the_message_shows_who_needed_it(self):
        app = App(Provide(new_database, new_worker), validate=False)

        with pytest.raises(MissingProviderError) as exc_info:
            await app.resolve(Worker)

        message = str(exc_info.value)
        assert "required by Database" in message
        assert "required by Worker" in message

    async def test_the_chain_names_the_constructor(self):
        app = App(Provide(new_database, new_worker), validate=False)

        with pytest.raises(MissingProviderError) as exc_info:
            await app.resolve(Worker)

        assert "new_database" in str(exc_info.value)

    async def test_the_chain_names_the_module(self):
        app = App(
            Component("storage", Provide(new_database)),
            Provide(new_worker),
            validate=False,
        )

        with pytest.raises(MissingProviderError) as exc_info:
            await app.resolve(Worker)

        assert 'module "storage"' in str(exc_info.value)

    async def test_the_chain_reaches_back_to_the_invokable(self):
        app = App(Provide(new_database, new_worker), Invoke(run), validate=False)

        with pytest.raises(MissingProviderError) as exc_info:
            await app.start()

        assert "invokable run" in str(exc_info.value)


class TestValidationMessages:
    def test_a_missing_dependency_names_the_constructor_and_module(self):
        app = App(Component("storage", Provide(new_database)))

        with pytest.raises(ValidationError) as exc_info:
            app.validate()

        error = exc_info.value.errors[0]
        assert "new_database" in error
        assert 'module "storage"' in error
        assert "Config" in error
