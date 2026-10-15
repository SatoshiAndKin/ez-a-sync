"""Cancellation propagation from executor shutdown to async callers."""

import asyncio
import threading

import pytest

from a_sync.executor import PruningThreadPoolExecutor, ThreadPoolExecutor


@pytest.mark.parametrize("executor_class", [ThreadPoolExecutor, PruningThreadPoolExecutor])
def test_shutdown_cancels_queued_async_waiter_without_callback_errors(executor_class):
    """Executor shutdown must finish async waiters for work that never started."""

    async def exercise():
        loop = asyncio.get_running_loop()
        errors = []
        previous_handler = loop.get_exception_handler()
        loop.set_exception_handler(lambda loop, context: errors.append(context))
        executor = executor_class(1)
        started, release = threading.Event(), threading.Event()

        def block_worker():
            started.set()
            assert release.wait(5)

        running = executor.submit(block_worker)
        queued = None
        try:
            deadline = loop.time() + 1
            while not started.is_set():
                assert loop.time() < deadline
                await asyncio.sleep(0)
            queued = executor.submit(lambda: None)
            executor.shutdown(wait=False, cancel_futures=True)
            done, _ = await asyncio.wait([queued], timeout=0.5)
            assert queued in done, "Shutdown left the cancelled job's async waiter pending"
            assert queued.cancelled()
            with pytest.raises(asyncio.CancelledError):
                await queued
            assert not errors
        finally:
            release.set()
            await asyncio.wait_for(running, 2)
            if queued is not None:
                queued.cancel()
            executor.shutdown(wait=True)
            loop.set_exception_handler(previous_handler)

    asyncio.run(exercise())
