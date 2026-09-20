#!/usr/bin/env python3
"""
Test to demonstrate singleton behavior of providers.
"""

import asyncio
from dataclasses import dataclass

from di_fx import Component, Provide, Supply


@dataclass
class Config:
    """Configuration class."""

    value: str


class Service:
    """A service that tracks instantiation count."""

    _instance_count = 0

    def __init__(self, config: Config):
        Service._instance_count += 1
        self.instance_id = Service._instance_count
        self.config = config
        print(
            f"🚀 Service #{self.instance_id} instantiated with config: {self.config.value}"
        )

    def do_something(self) -> str:
        return f"Service #{self.instance_id} working with: {self.config.value}"


def create_service(config: Config) -> Service:
    """Factory function that creates a service."""
    print("🏭 Factory function called!")
    return Service(config)


async def main() -> None:
    """Main function to test singleton behavior."""
    print("📦 Creating Component with Provide...")

    app = Component(
        Provide(create_service),
        Supply(Config(value="test_value")),
    )

    print("\n🔍 Resolving Service dependency for the first time...")
    service1 = await app.resolve(Service)
    print(f"📤 Service 1 result: {service1.do_something()}")

    print("\n🔍 Resolving Service dependency for the second time...")
    service2 = await app.resolve(Service)
    print(f"📤 Service 2 result: {service2.do_something()}")

    print(f"\n🔍 Are they the same instance? {service1 is service2}")
    print(f"🔍 Service 1 ID: {service1.instance_id}")
    print(f"🔍 Service 2 ID: {service2.instance_id}")

    print("\n🎯 Conclusion: Providers are SINGLETON by default!")


if __name__ == "__main__":
    asyncio.run(main())
