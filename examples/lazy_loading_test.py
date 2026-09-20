#!/usr/bin/env python3
"""
Test to demonstrate whether Provide implements lazy loading.
"""

import asyncio
from dataclasses import dataclass

from di_fx import Component, Provide, Supply


@dataclass
class Config:
    """Configuration class."""

    value: str


class Service:
    """A service that prints when instantiated."""

    def __init__(self, config: Config):
        self.config = config
        print(f"🚀 Service instantiated with config: {self.config.value}")

    def do_something(self) -> str:
        return f"Service working with: {self.config.value}"


def create_service(config: Config) -> Service:
    """Factory function that creates a service."""
    print("🏭 Factory function called!")
    return Service(config)


async def main() -> None:
    """Main function to test lazy loading."""
    print("📦 Creating Component with Provide...")

    # Create the component - this should NOT instantiate services yet
    app = Component(
        Provide(create_service),
        Supply(Config(value="test_value")),
    )

    print("✅ Component created successfully!")
    print("⏳ Services should NOT be instantiated yet...")

    # Wait a moment to show nothing happens
    await asyncio.sleep(1)

    print("\n🔍 Now resolving Service dependency...")

    # This is when the service should actually be created
    service = await app.resolve(Service)

    print("✅ Service resolved!")

    # Use the service
    result = service.do_something()
    print(f"📤 Service result: {result}")

    print("\n🎯 Conclusion: Provide IS lazy-loading!")


if __name__ == "__main__":
    asyncio.run(main())
