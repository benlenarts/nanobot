"""Context-compaction notices follow ``send_progress``, except failures.

Idle auto-compaction runs after every quiet spell, so on a channel fed by
frequent scheduled jobs its notices become routine chatter. A channel with
``send_progress`` off gets only a failed compaction; a channel with it on
gets the full lifecycle.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from nanobot.bus.outbound_events import (
    ContextCompactionEvent,
    ProgressEvent,
    outbound_message_for_event,
)
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel
from nanobot.channels.manager import ChannelManager
from nanobot.config.schema import Config


class _MockChannel(BaseChannel):
    name = "mock"
    display_name = "Mock"

    def __init__(self, config, bus):
        super().__init__(config, bus)
        self._send_mock = AsyncMock()

    async def start(self):  # pragma: no cover - not exercised
        pass

    async def stop(self):  # pragma: no cover - not exercised
        pass

    async def send(self, msg):
        return await self._send_mock(msg)


@pytest.fixture
def manager() -> ChannelManager:
    config = Config.model_validate({"channels": {"websocket": {"enabled": False}}})
    mgr = ChannelManager(config, MessageBus())
    mgr.channels["mock"] = _MockChannel({}, mgr.bus)
    return mgr


async def _dispatch_until(manager: ChannelManager, expected: int) -> None:
    task = asyncio.create_task(manager._dispatch_outbound())
    try:
        for _ in range(40):
            if manager.channels["mock"]._send_mock.await_count >= expected:
                break
            await asyncio.sleep(0.05)
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def _sent_contents(manager: ChannelManager) -> list[str]:
    return [call.args[0].content for call in manager.channels["mock"]._send_mock.await_args_list]


async def _publish(manager: ChannelManager, *events) -> None:
    for event in events:
        await manager.bus.publish_outbound(
            outbound_message_for_event(channel="mock", chat_id="chat", event=event)
        )


@pytest.mark.asyncio
async def test_compaction_notices_suppressed_with_progress_off(manager: ChannelManager) -> None:
    manager.channels["mock"].send_progress = False
    await _publish(
        manager,
        ProgressEvent(content="ordinary progress"),
        ContextCompactionEvent(compaction_id="c1", phase="started"),
        ContextCompactionEvent(compaction_id="c1", phase="succeeded"),
        ContextCompactionEvent(compaction_id="c2", phase="started"),
        ContextCompactionEvent(compaction_id="c2", phase="cancelled"),
        ContextCompactionEvent(compaction_id="c3", phase="started"),
        ContextCompactionEvent(compaction_id="c3", phase="failed"),
    )

    await _dispatch_until(manager, 1)

    sent = [call.args[0].event for call in manager.channels["mock"]._send_mock.await_args_list]
    assert sent == [ContextCompactionEvent(compaction_id="c3", phase="failed")]


@pytest.mark.asyncio
async def test_compaction_lifecycle_is_delivered_with_progress_on(manager: ChannelManager) -> None:
    manager.channels["mock"].send_progress = True
    await _publish(
        manager,
        ContextCompactionEvent(compaction_id="c1", phase="started"),
        ContextCompactionEvent(compaction_id="c1", phase="succeeded"),
    )

    await _dispatch_until(manager, 2)

    assert len(_sent_contents(manager)) == 2
