from asyncio import Event, get_event_loop, sleep

import pytest

from a_sync._smart import SmartTask, set_smart_task_factory
from a_sync.asyncio.create_task import _get_persisted_tasks, create_task


@pytest.mark.asyncio_cooperative
async def test_create_task_with_coroutine():
    async def sample_coroutine():
        return "Hello, World!"

    task = create_task(sample_coroutine())
    result = await task
    assert result == "Hello, World!"


@pytest.mark.asyncio_cooperative
async def test_create_task_with_future():
    loop = get_event_loop()
    future = loop.create_future()
    future.set_result("Future Result")

    task = create_task(future)
    result = await task
    assert result == "Future Result"


@pytest.mark.asyncio_cooperative
async def test_create_task_with_name():
    async def sample_coroutine():
        return "Named Task"

    task = create_task(sample_coroutine(), name="TestTask")
    assert task.get_name() == "TestTask"


@pytest.mark.asyncio_cooperative
async def test_create_task_skip_gc_until_done():
    async def sample_coroutine():
        return "GC Test"

    persisted_tasks = _get_persisted_tasks()

    before = set(persisted_tasks)
    task = create_task(sample_coroutine(), skip_gc_until_done=True)
    (persisted,) = persisted_tasks - before
    assert not persisted.done()
    result = await task
    await persisted
    # The callback removes this wrapper, independently of other cooperative tests.
    await sleep(0)
    assert persisted not in persisted_tasks
    assert result == "GC Test"


@pytest.mark.asyncio_cooperative
async def test_persisted_task_completion_preserves_other_pending_tasks():
    release = Event()
    persisted_tasks = _get_persisted_tasks()
    before = set(persisted_tasks)
    pending = create_task(release.wait(), skip_gc_until_done=True)
    (pending_wrapper,) = persisted_tasks - before
    try:
        before_complete = set(persisted_tasks)
        completed = create_task(sleep(0), skip_gc_until_done=True)
        (completed_wrapper,) = persisted_tasks - before_complete
        await completed
        await completed_wrapper
        await sleep(0)
        assert completed_wrapper not in persisted_tasks
        assert pending_wrapper in persisted_tasks
        assert not pending_wrapper.done()
    finally:
        release.set()
        await pending
        await pending_wrapper
        await sleep(0)
    assert pending_wrapper not in persisted_tasks


@pytest.mark.asyncio_cooperative
async def test_create_task_log_destroy_pending():
    async def sample_coroutine():
        return "Log Test"

    task = create_task(sample_coroutine(), log_destroy_pending=False)
    assert not task._log_destroy_pending


@pytest.mark.asyncio_cooperative
async def test_create_task_handles_non_coroutine_awaitable():
    class CustomAwaitable:
        def __await__(self):
            yield
            return "Custom Awaitable Result"

    result = await create_task(CustomAwaitable())
    assert result == "Custom Awaitable Result"


def test_create_task_with_smart_task_factory():
    loop = get_event_loop()
    set_smart_task_factory(loop)

    async def work():
        t = create_task(sleep(1))
        assert isinstance(t, SmartTask)
        return await t

    assert loop.run_until_complete(work()) is None
