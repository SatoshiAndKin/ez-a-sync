"""Completed awaits release callbacks and values while the caller keeps running."""

import asyncio
import weakref

import pytest

from a_sync._smart import SmartFuture, SmartTask, shield


@pytest.mark.parametrize("kind", ["future", "task", "shield"])
@pytest.mark.parametrize("outcome", ["success", "failure", "cancel"])
def test_completed_await_releases_caller_callbacks_and_results(kind, outcome):
    class Payload:
        pass

    async def produce(value):
        await asyncio.sleep(0)
        if outcome == "failure":
            raise ValueError("lookup failed")
        if outcome == "cancel":
            raise asyncio.CancelledError
        return value

    async def check():
        caller = asyncio.current_task()
        callbacks_before = len(caller._callbacks or ())
        payload = Payload()
        reference = weakref.ref(payload)
        inner = None
        if kind == "future":
            pending = SmartFuture()
            loop = asyncio.get_running_loop()
            if outcome == "failure":
                loop.call_soon(pending.set_exception, ValueError("lookup failed"))
            elif outcome == "cancel":
                loop.call_soon(pending.cancel)
            else:
                loop.call_soon(pending.set_result, payload)
        elif kind == "task":
            pending = SmartTask(produce(payload))
        else:
            inner = asyncio.create_task(produce(payload))
            pending = shield(inner)

        if outcome == "success":
            result = await pending
            assert result is payload
            del result
        elif outcome == "failure":
            with pytest.raises(ValueError, match="lookup failed"):
                await pending
        else:
            with pytest.raises(asyncio.CancelledError):
                await pending

        assert len(caller._callbacks or ()) == callbacks_before
        del payload, pending, inner
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        if outcome == "success":
            assert reference() is None

    asyncio.get_event_loop().run_until_complete(check())
