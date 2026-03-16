"""Integration tests: shell guard allows media dir paths under restrictToWorkspace."""

from __future__ import annotations

from nanobot.agent.tools.shell import ExecTool


class TestShellGuardMediaAccess:

    def test_media_dir_path_allowed(self, tmp_path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        media_dir = tmp_path / "media"
        media_dir.mkdir()

        tool = ExecTool(
            working_dir=str(workspace),
            restrict_to_workspace=True,
            extra_allowed_dirs=[str(media_dir)],
        )
        result = tool._guard_command(
            f"cat {media_dir}/telegram/abc123.ogg", str(workspace)
        )
        assert result is None

    def test_other_outside_path_still_blocked(self, tmp_path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        media_dir = tmp_path / "media"
        media_dir.mkdir()

        tool = ExecTool(
            working_dir=str(workspace),
            restrict_to_workspace=True,
            extra_allowed_dirs=[str(media_dir)],
        )
        result = tool._guard_command(
            "cat /etc/passwd", str(workspace)
        )
        assert result is not None
        assert "outside working dir" in result

    def test_workspace_path_still_allowed(self, tmp_path):
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        media_dir = tmp_path / "media"
        media_dir.mkdir()

        tool = ExecTool(
            working_dir=str(workspace),
            restrict_to_workspace=True,
            extra_allowed_dirs=[str(media_dir)],
        )
        result = tool._guard_command(
            f"cat {workspace}/file.txt", str(workspace)
        )
        assert result is None
