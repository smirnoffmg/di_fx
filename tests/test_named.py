"""Tests for Named functionality."""

import pytest

from di_fx import App, Named, Provide


class TestNamed:
    """Test the Named functionality."""

    def test_named_creation(self):
        """Test creating Named types."""

        class Database:
            pass

        PrimaryDB = Named("primary", Database)
        ReplicaDB = Named("replica", Database)

        assert isinstance(PrimaryDB, Named)
        assert PrimaryDB.name == "primary"
        assert PrimaryDB.type == Database

        assert isinstance(ReplicaDB, Named)
        assert ReplicaDB.name == "replica"
        assert ReplicaDB.type == Database

    def test_named_equality(self):
        """Test Named type equality."""

        class Database:
            pass

        PrimaryDB1 = Named("primary", Database)
        PrimaryDB2 = Named("primary", Database)
        ReplicaDB = Named("replica", Database)

        assert PrimaryDB1 == PrimaryDB2
        assert PrimaryDB1 != ReplicaDB
        assert PrimaryDB1 != Database

    def test_named_hash(self):
        """Test that Named types can be used in sets and as dict keys."""

        class Database:
            pass

        PrimaryDB = Named("primary", Database)
        ReplicaDB = Named("replica", Database)

        # Test set usage
        named_types = {PrimaryDB, ReplicaDB}
        assert len(named_types) == 2
        assert PrimaryDB in named_types
        assert ReplicaDB in named_types

        # Test dict usage
        providers = {PrimaryDB: "primary_provider", ReplicaDB: "replica_provider"}
        assert providers[PrimaryDB] == "primary_provider"
        assert providers[ReplicaDB] == "replica_provider"

    def test_named_repr(self):
        """Test Named type string representation."""

        class Database:
            pass

        PrimaryDB = Named("primary", Database)
        assert repr(PrimaryDB) == "Named('primary', Database)"

    @pytest.mark.asyncio
    async def test_named_dependency_injection(self):
        """Test that Named types can be injected correctly."""

        class Database:
            def __init__(self, name: str):
                self.name = name

        PrimaryDB = Named("primary", Database)
        ReplicaDB = Named("replica", Database)

        def create_primary_db() -> PrimaryDB:
            return Database("primary")

        def create_replica_db() -> ReplicaDB:
            return Database("replica")

        def setup_services(primary_db: PrimaryDB, replica_db: ReplicaDB) -> str:
            """Function that receives different named Database instances."""
            assert primary_db.name == "primary"
            assert replica_db.name == "replica"
            return f"Services setup with {primary_db.name} and {replica_db.name}"

        app = App(
            Provide(create_primary_db, create_replica_db), Provide(setup_services)
        )

        # Should not raise any errors
        app.validate()

        # The function should be properly injected with Named types
        # We can test this by running the app lifecycle
        async with app.lifecycle():
            # The Named types should be properly resolved during startup
            pass

    @pytest.mark.asyncio
    async def test_named_with_annotated_types(self):
        """Test that Named types work with Annotated types."""

        from typing import Annotated

        # Create distinct types using Annotated
        DatabaseType = Annotated[str, "database"]
        ServerType = Annotated[str, "server"]

        # Create named versions
        PrimaryDB = Named("primary", DatabaseType)
        ReplicaDB = Named("replica", DatabaseType)

        def create_primary_db() -> PrimaryDB:
            return "postgresql://primary/db"

        def create_replica_db() -> ReplicaDB:
            return "postgresql://replica/db"

        def create_server() -> ServerType:
            return "http://localhost:8000"

        def setup_services(
            primary_db: PrimaryDB, replica_db: ReplicaDB, server: ServerType
        ) -> str:
            """Function that receives named database types and server type."""
            assert primary_db.startswith("postgresql://primary")
            assert replica_db.startswith("postgresql://replica")
            assert server.startswith("http://")
            return f"Services setup with {primary_db}, {replica_db}, {server}"

        app = App(
            Provide(create_primary_db, create_replica_db, create_server),
            Provide(setup_services),
        )

        # Should not raise any errors
        app.validate()

        # The function should be properly injected with Named types
        # We can test this by running the app lifecycle
        async with app.lifecycle():
            # The Named types should be properly resolved during startup
            pass

    @pytest.mark.asyncio
    async def test_named_type_resolution(self):
        """Test that Named types are resolved correctly."""

        class Config:
            def __init__(self, source: str):
                self.source = source

        EnvConfig = Named("env", Config)
        FileConfig = Named("file", Config)

        def create_env_config() -> EnvConfig:
            return Config("environment")

        def create_file_config() -> FileConfig:
            return Config("file")

        def merge_configs(env_config: EnvConfig, file_config: FileConfig) -> str:
            """Function that merges different config sources."""
            return f"Config merged from {env_config.source} and {file_config.source}"

        app = App(
            Provide(create_env_config, create_file_config), Provide(merge_configs)
        )

        # Should not raise any errors
        app.validate()

        # The function should be properly injected with Named types
        # We can test this by running the app lifecycle
        async with app.lifecycle():
            # The Named types should be properly resolved during startup
            pass

    def test_named_type_validation(self):
        """Test that Named types are properly validated."""

        class Service:
            pass

        MainService = Named("main", Service)

        def create_service() -> MainService:
            return Service()

        def use_service(service: MainService) -> str:
            return "Service used"

        app = App(Provide(create_service), Provide(use_service))

        # Should not raise any errors
        app.validate()

    def test_named_type_mismatch(self):
        """Test that Named type mismatches are caught during validation."""

        class Service:
            pass

        MainService = Named("main", Service)
        OtherService = Named("other", Service)

        def create_service() -> MainService:
            return Service()

        def use_service(service: OtherService) -> str:
            return "Service used"

        app = App(Provide(create_service), Provide(use_service))

        # Should raise validation error because "other" named type is not provided
        with pytest.raises(Exception) as exc_info:
            app.validate()

        # Check that it's a validation error with the right message
        assert "ValidationError" in str(type(exc_info.value))
        # Check the error details
        validation_error = exc_info.value
        assert hasattr(validation_error, "errors")
        assert len(validation_error.errors) == 1
        assert "other:Service" in validation_error.errors[0]
