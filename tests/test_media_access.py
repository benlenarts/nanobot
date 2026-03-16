"""Integration tests: media dir is readable but not writable under restrictToWorkspace."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from nanobot.agent.loop import AgentLoop
from nanobot.bus.queue import MessageBus


def _make_loop(workspace, media_dir):
    """Create an AgentLoop with restrict_to_workspace=True and a custom media dir."""
    bus = MessageBus()
    provider = MagicMock()
    provider.get_default_model.return_value = "test-model"

    with patch("nanobot.agent.loop.ContextBuilder"), \
         patch("nanobot.agent.loop.SessionManager"), \
         patch("nanobot.agent.loop.SubagentManager"), \
         patch("nanobot.agent.loop.get_media_dir", return_value=media_dir):
        loop = AgentLoop(
            bus=bus,
            provider=provider,
            workspace=workspace,
            restrict_to_workspace=True,
        )
    return loop


class TestMediaAccessUnderRestriction:

    @pytest.mark.asyncio
    async def test_read_file_can_access_media_dir(self, tmp_path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        media_dir = tmp_path / "media"
        media_dir.mkdir()
        voice = media_dir / "telegram" / "abc123.ogg"
        voice.parent.mkdir()
        voice.write_text("fake audio data")

        loop = _make_loop(workspace, media_dir)
        tool = loop.tools.get("read_file")
        result = await tool.execute(path=str(voice))

        assert "fake audio data" in result
        assert "Error" not in result

    @pytest.mark.asyncio
    async def test_write_file_cannot_access_media_dir(self, tmp_path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        media_dir = tmp_path / "media"
        media_dir.mkdir()
        target = media_dir / "telegram" / "abc123.ogg"
        target.parent.mkdir()

        loop = _make_loop(workspace, media_dir)
        tool = loop.tools.get("write_file")
        result = await tool.execute(path=str(target), content="overwritten")

        assert "Error" in result
        assert "outside" in result.lower()
