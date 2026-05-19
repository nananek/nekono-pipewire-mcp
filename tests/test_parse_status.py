"""Parse the wpctl status fixture and validate the structure.

The fixture (= tests/fixtures/wpctl-status-ayaka.txt) is a real `wpctl status`
output captured on ayaka (= Arch + wireplumber 1.6.5)。 Format drift in future
wireplumber versions will be caught by this test failing — capture a new fixture
and update expectations.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from nekono_pipewire_mcp import server

FIXTURE = Path(__file__).parent / "fixtures" / "wpctl-status-ayaka.txt"


@pytest.fixture
def parsed() -> dict:
    """Run _parse_status() against the fixture instead of live wpctl."""
    text = FIXTURE.read_text()
    with patch.object(server, "_run_wpctl", return_value=text):
        return server._parse_status()


def test_top_level_sections(parsed: dict) -> None:
    assert "Audio" in parsed
    assert "Video" in parsed


def test_audio_subsections(parsed: dict) -> None:
    audio = parsed["Audio"]
    for sub in ("Devices", "Sinks", "Sources"):
        assert sub in audio, f"missing Audio.{sub}"


def test_default_sink_marker(parsed: dict) -> None:
    sinks = parsed["Audio"]["Sinks"]
    defaults = [s for s in sinks if s["default"]]
    assert len(defaults) == 1, "exactly one sink should be marked default"
    assert defaults[0]["id"] > 0
    assert "name" in defaults[0]


def test_sink_volume_parsed(parsed: dict) -> None:
    sinks = parsed["Audio"]["Sinks"]
    for s in sinks:
        assert "volume" in s
        assert "muted" in s
        assert 0.0 <= s["volume"] <= 2.0
        assert isinstance(s["muted"], bool)


def test_device_entries_have_no_volume(parsed: dict) -> None:
    """Devices (= ALSA cards) don't carry a [vol: ...] suffix."""
    for d in parsed["Audio"]["Devices"]:
        assert "volume" not in d
        assert "muted" not in d


def test_entry_id_is_int(parsed: dict) -> None:
    for sub_entries in parsed["Audio"].values():
        for entry in sub_entries:
            assert isinstance(entry["id"], int)
            assert entry["id"] > 0
