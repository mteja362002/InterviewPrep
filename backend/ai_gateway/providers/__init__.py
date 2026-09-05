"""Provider adapter package.

Contains only provider adapter implementations.  Adapters are stateless,
reusable, and know nothing about environment variables, priorities, or
routing policy.

Provider discovery and registration is owned exclusively by
``ai_gateway.routing.ProviderRegistry.load_from_environment()``.
"""
from ai_gateway.providers.base import ProviderAdapter

__all__ = ["ProviderAdapter"]
