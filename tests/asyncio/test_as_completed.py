import asyncio

import pytest

import a_sync
from tests.fixtures import sample_exc, sample_task, timeout_task


@pytest.mark.asyncio_cooperative
async def test_as_completed_with_awaitables():
    tasks = [sample_task(i) for i in range(5)]
    results = [await result for result in a_sync.as_completed(tasks, aiter=False)]
    assert sorted(results) == list(range(5)), "Results should be in ascending order from 0 to 4"


@pytest.mark.asyncio_cooperative
async def test_as_completed_with_awaitables_aiter():
    tasks = [sample_task(i) for i in range(5)]
    results = []
    async for result in a_sync.as_completed(tasks, aiter=True):
        results.append(result)
    assert sorted(results) == list(range(5)), "Results should be in ascending order from 0 to 4"


@pytest.mark.asyncio_cooperative
async def test_as_completed_with_mapping():
    tasks = {"task1": sample_task(1), "task2": sample_task(2)}
    results = {}
    for result in a_sync.as_completed(tasks, aiter=False):
        key, value = await result
        results[key] = value
    assert results == {"task1": 1, "task2": 2}, "Results should match the input mapping"


@pytest.mark.asyncio_cooperative
async def test_as_completed_with_mapping_aiter():
    tasks = {"task1": sample_task(1), "task2": sample_task(2)}
    results = {}
    async for key, result in a_sync.as_completed(tasks, aiter=True):
        results[key] = result
    assert results == {"task1": 1, "task2": 2}, "Results should match the input mapping"


@pytest.mark.asyncio_cooperative
async def test_as_completed_with_timeout():
    tasks = [timeout_task(i) for i in range(2)]
    with pytest.raises(asyncio.TimeoutError):
        [await result for result in a_sync.as_completed(tasks, aiter=False, timeout=0.05)]


@pytest.mark.asyncio_cooperative
async def test_as_completed_with_timeout_aiter():
    tasks = [timeout_task(i) for i in range(2)]
    with pytest.raises(asyncio.TimeoutError):
        [result async for result in a_sync.as_completed(tasks, aiter=True, timeout=0.05)]


@pytest.mark.asyncio_cooperative
async def test_as_completed_return_exceptions():
    tasks = [sample_exc(i) for i in range(1)]
    results = [
        await result for result in a_sync.as_completed(tasks, aiter=False, return_exceptions=True)
    ]
    assert isinstance(results[0], ValueError), f"The result should be an exception {results}"


@pytest.mark.asyncio_cooperative
async def test_as_completed_return_exceptions_aiter():
    tasks = [sample_exc(i) for i in range(1)]
    results = []
    async for result in a_sync.as_completed(tasks, aiter=True, return_exceptions=True):
        results.append(result)
    assert isinstance(results[0], ValueError), "The result should be an exception"


@pytest.mark.asyncio_cooperative
async def test_as_completed_with_tqdm_disabled():
    tasks = [sample_task(i) for i in range(5)]
    results = [await result for result in a_sync.as_completed(tasks, aiter=False, tqdm=False)]
    assert sorted(results) == list(range(5)), "Results should be in ascending order from 0 to 4"


@pytest.mark.asyncio_cooperative
async def test_as_completed_with_tqdm_disabled_aiter():
    tasks = [sample_task(i) for i in range(5)]
    results = []
    async for result in a_sync.as_completed(tasks, aiter=True, tqdm=False):
        results.append(result)
    assert sorted(results) == list(range(5)), "Results should be in ascending order from 0 to 4"


@pytest.mark.asyncio_cooperative
async def test_as_completed_with_mapping_and_return_exceptions():
    tasks = {"task1": sample_exc(1), "task2": sample_task(2)}
    results = {}
    for result in a_sync.as_completed(tasks, return_exceptions=True, aiter=False):
        key, value = await result
        results[key] = value
    assert isinstance(results["task1"], ValueError), "Result should be ValueError"
    assert results["task2"] == 2, "Results should match the input mapping"


@pytest.mark.asyncio_cooperative
async def test_as_completed_with_mapping_and_return_exceptions_aiter():
    tasks = {"task1": sample_exc(1), "task2": sample_task(2)}
    results = {}
    async for key, result in a_sync.as_completed(tasks, return_exceptions=True, aiter=True):
        results[key] = result
    assert isinstance(results["task1"], ValueError), "Result should be ValueError"
    assert results["task2"] == 2, "Results should match the input mapping"


@pytest.mark.asyncio_cooperative
@pytest.mark.parametrize("mapping", [False, True])
@pytest.mark.parametrize("aiter", [False, True])
async def test_return_exceptions_preserves_cancelled_child_and_other_results(mapping, aiter):
    loop = asyncio.get_running_loop()
    cancelled = loop.create_future()
    cancelled.cancel()
    completed = loop.create_future()
    completed.set_result(42)
    inputs = {"cancelled": cancelled, "completed": completed} if mapping else [cancelled, completed]
    iterator = a_sync.as_completed(inputs, return_exceptions=True, aiter=aiter)
    results = (
        [result async for result in iterator] if aiter else [await result for result in iterator]
    )
    if mapping:
        results = dict(results)
        assert isinstance(results["cancelled"], asyncio.CancelledError)
        assert results["completed"] == 42
    else:
        assert 42 in results
        assert sum(isinstance(result, asyncio.CancelledError) for result in results) == 1


@pytest.mark.asyncio_cooperative
@pytest.mark.parametrize("mapping", [False, True])
async def test_exception_wrapper_propagates_its_own_cancellation(mapping):
    from a_sync.asyncio.as_completed import _exc_wrap, __mapping_wrap

    child = asyncio.get_running_loop().create_future()
    wrapped = __mapping_wrap("key", child, return_exceptions=True) if mapping else _exc_wrap(child)
    task = asyncio.create_task(wrapped)
    await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert task.cancelled()
    assert child.cancelled()
