"""The in-process sweeper schedule: the loop, and its switch in the app lifespan.
No database: the sweep itself is replaced by a counter."""

import asyncio
import threading
import time
from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.main as main
from app.config import get_settings
from app.services import sweeper


def test_tests_run_with_the_sweeper_disabled():
    assert get_settings().sweeper_enabled is False


def test_loop_runs_at_once_then_every_interval_until_stopped():
    calls = []

    async def scenario():
        stop = asyncio.Event()
        task = asyncio.create_task(sweeper.run_periodically(0.01, lambda: calls.append(1), stop))
        while len(calls) < 3:
            await asyncio.sleep(0.005)
        stop.set()
        await asyncio.wait_for(task, timeout=1)

    asyncio.run(scenario())
    assert len(calls) >= 3


def test_a_failing_sweep_is_logged_and_the_loop_carries_on(caplog):
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("database unavailable")

    async def scenario():
        stop = asyncio.Event()
        task = asyncio.create_task(sweeper.run_periodically(0.01, flaky, stop))
        while len(calls) < 2:
            await asyncio.sleep(0.005)
        stop.set()
        await asyncio.wait_for(task, timeout=1)

    asyncio.run(scenario())
    assert len(calls) >= 2
    assert "Background sweep failed" in caplog.text


def _lifespan_runs_sweep(monkeypatch, enabled: bool) -> bool:
    ran = threading.Event()
    monkeypatch.setattr(main, "get_settings", lambda: SimpleNamespace(sweeper_enabled=enabled))
    monkeypatch.setattr(sweeper, "sweep_now", ran.set)
    with TestClient(main.app):
        deadline = time.monotonic() + 2
        while not ran.is_set() and time.monotonic() < deadline:
            time.sleep(0.01)
    return ran.is_set()


def test_lifespan_starts_the_sweeper_when_enabled(monkeypatch):
    assert _lifespan_runs_sweep(monkeypatch, enabled=True)


def test_lifespan_does_not_start_the_sweeper_when_disabled(monkeypatch):
    assert not _lifespan_runs_sweep(monkeypatch, enabled=False)
