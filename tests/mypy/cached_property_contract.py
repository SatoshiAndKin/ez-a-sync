"""Static contract for the runtime cached-property descriptor."""

from typing import assert_type

import a_sync
from a_sync import cached_property


class CachedValue:
    @cached_property
    async def value(self) -> int:
        return 7


async def cached_property_contract() -> None:
    owner = CachedValue()
    owner.value = 11
    assert_type(await CachedValue.value.get(owner), int)
    assert_type(CachedValue.value.get_cache_value(owner), int)
    assert await CachedValue.value.get(owner) == 11
    CachedValue.value.set_cache_value(owner, 13)
    assert CachedValue.value.get_cache_value(owner) == 13
    del owner.value
    assert await CachedValue.value.get(owner) == 7


class FactoryValue:
    @a_sync.aka.cached_property
    async def value(self) -> int:
        return 17


class SyncFactoryValue:
    @a_sync.aka.cached_property
    def value(self) -> int:
        return 19


async def factory_contract() -> None:
    asynchronous, synchronous = FactoryValue(), SyncFactoryValue()
    assert_type(await FactoryValue.value.get(asynchronous), int)
    assert_type(await SyncFactoryValue.value.get(synchronous), int)
    assert await FactoryValue.value.get(asynchronous) == 17
    assert await SyncFactoryValue.value.get(synchronous) == 19
