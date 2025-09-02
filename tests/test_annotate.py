"""Tests for Annotate and As functionality."""

import pytest

from di_fx import Annotate, App, As, Provide


class TestAnnotate:
    """Test the Annotate and As classes."""

    def test_as_creation(self):
        """Test creating As annotations."""
        class UserRepository:
            pass

        class UserAccessor:
            pass

        as_annotation = As(UserAccessor)
        assert as_annotation.interface_type == UserAccessor
        assert repr(as_annotation) == "As(UserAccessor)"

    def test_annotate_creation(self):
        """Test creating Annotate tuples."""
        def create_user_repo():
            return "UserRepository"

        class UserAccessor:
            pass

        class UserStorage:
            pass

        result = Annotate(create_user_repo, As(UserAccessor), As(UserStorage))

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert result[0] == create_user_repo
        assert len(result[1]) == 2
        assert isinstance(result[1][0], As)
        assert isinstance(result[1][1], As)

    @pytest.mark.asyncio
    async def test_interface_registration(self):
        """Test that interfaces are properly registered and can be resolved."""

        def create_user_repository() -> str:
            return "UserRepository"

        class UserAccessor:
            pass

        class UserStorage:
            pass

        app = App(
            Provide(
                Annotate(create_user_repository, As(UserAccessor), As(UserStorage))
            )
        )

        # Should be able to resolve the concrete type
        user_repo = await app.resolve(str)
        assert user_repo == "UserRepository"

        # Should be able to resolve the interface types
        user_accessor = await app.resolve(UserAccessor)
        assert user_accessor == "UserRepository"

        user_storage = await app.resolve(UserStorage)
        assert user_storage == "UserRepository"

    @pytest.mark.asyncio
    async def test_multiple_providers_same_interface(self):
        """Test that multiple providers can provide the same interface."""

        def create_user_repo() -> str:
            return "UserRepository"

        def create_admin_repo() -> str:
            return "AdminRepository"

        class UserAccessor:
            pass

        app = App(
            Provide(
                Annotate(create_user_repo, As(UserAccessor)),
                Annotate(create_admin_repo, As(UserAccessor))
            )
        )

        # Should be able to resolve the concrete types
        user_repo = await app.resolve(str)
        # Note: This will resolve to the last registered provider
        assert user_repo in ["UserRepository", "AdminRepository"]

        # Should be able to resolve the interface type
        user_accessor = await app.resolve(UserAccessor)
        assert user_accessor in ["UserRepository", "AdminRepository"]
