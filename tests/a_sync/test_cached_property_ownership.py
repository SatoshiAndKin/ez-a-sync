"""A descriptor must not own the first instance passed to its shared loader."""

import asyncio
import weakref

import pytest

from a_sync.a_sync.property import ASyncCachedPropertyDescriptor
from a_sync.async_property.cached import AsyncCachedPropertyDescriptor


@pytest.mark.parametrize(
    "descriptor_type", [AsyncCachedPropertyDescriptor, ASyncCachedPropertyDescriptor]
)
@pytest.mark.parametrize("with_setter", [False, True])
def test_cached_loader_releases_instances_and_reuses_values(descriptor_type, with_setter):
    calls, setters = {}, {}

    async def value(instance):
        calls[instance.key] = calls.get(instance.key, 0) + 1
        return (instance.key, bytearray(1024))

    def store(instance, result):
        setters[instance.key] = result[0]

    descriptor = descriptor_type(value, _fset=store if with_setter else None)

    class Sample:
        value = descriptor

        def __init__(self, key):
            self.key = key

    async def check():
        first, second = Sample("first"), Sample("second")
        references = weakref.ref(first), weakref.ref(second)
        first_value = await descriptor.get_loader(first)()
        second_value = await descriptor.get_loader(second)()
        assert first_value is await descriptor.get_loader(first)()
        assert second_value is await descriptor.get_loader(second)()
        assert first_value[0] == "first" and second_value[0] == "second"
        assert first_value is not second_value
        assert calls == {"first": 1, "second": 1}
        assert setters == ({"first": "first", "second": "second"} if with_setter else {})
        del first, second
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert references[0]() is None
        assert references[1]() is None

    asyncio.get_event_loop().run_until_complete(check())
