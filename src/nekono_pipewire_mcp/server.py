"""nekono-pipewire-mcp: MCP server for PipeWire / wireplumber.

Tools (MVP):
- pipewire_status() — snapshot of `wpctl status` (sinks/sources/streams/default)
- pipewire_set_default_sink(node_id) — switch default sink
- pipewire_set_volume(node_id, percent) — set volume (0-100, opt-in above 100)

Mutation tools return the post-mutation snapshot for readback verification.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from typing import Any

from fastmcp import FastMCP

mcp = FastMCP("nekono-pipewire")

WPCTL = shutil.which("wpctl") or "/usr/bin/wpctl"


def _run_wpctl(*args: str) -> str:
    """Run wpctl with args. Returns stdout. Raises CalledProcessError on non-zero."""
    result = subprocess.run(
        [WPCTL, *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


# Section header regex: top-level word (= "Audio", "Video"), no leading whitespace.
_SECTION_RE = re.compile(r"^[A-Z][A-Za-z]+\s*$")
# Subsection (= " ├─ Sinks:" etc), uses unicode box-drawing chars.
_SUBSECTION_RE = re.compile(r"^[\s│]*[├└]─\s+(\w+):")
# Entry row: optional leading `│` + optional `*` (default marker) + numeric id + rest.
_ENTRY_RE = re.compile(r"^[\s│]*(\*)?\s*(\d+)\.\s+(.*)$")
# Volume suffix: `[vol: 1.00]` or `[vol: 1.00 MUTED]`.
_VOL_RE = re.compile(r"\[vol:\s*([\d.]+)(?:\s+(MUTED))?\]")
# Trailing `[...]` annotation (= profile name, capabilities) to strip from display name.
_TRAILING_BRACKET_RE = re.compile(r"\s*\[[^\]]+\]\s*$")


def _parse_status() -> dict[str, dict[str, list[dict[str, Any]]]]:
    """Parse `wpctl status` output into a nested dict.

    Returns: {section: {subsection: [{id, name, default, volume?, muted?}, ...]}}
    e.g. {"Audio": {"Sinks": [{"id": 75, "name": "Steinberg ...", "default": True,
                                "volume": 1.0, "muted": False}, ...]}}
    """
    text = _run_wpctl("status")
    out: dict[str, dict[str, list[dict[str, Any]]]] = {}
    section: str | None = None
    subsection: str | None = None

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        # Section header: no leading box-drawing, just a capitalized word.
        if _SECTION_RE.match(line):
            section = line.strip()
            out.setdefault(section, {})
            subsection = None
            continue
        # Subsection header.
        m_sub = _SUBSECTION_RE.match(line)
        if m_sub and section is not None:
            subsection = m_sub.group(1)
            out[section].setdefault(subsection, [])
            continue
        # Entry row.
        m_entry = _ENTRY_RE.match(line)
        if m_entry and section is not None and subsection is not None:
            is_default = m_entry.group(1) == "*"
            entry_id = int(m_entry.group(2))
            rest = m_entry.group(3).strip()
            entry: dict[str, Any] = {
                "id": entry_id,
                "name": _TRAILING_BRACKET_RE.sub("", rest).strip(),
                "default": is_default,
            }
            m_vol = _VOL_RE.search(rest)
            if m_vol:
                entry["volume"] = float(m_vol.group(1))
                entry["muted"] = m_vol.group(2) == "MUTED"
            out[section][subsection].append(entry)

    return out


@mcp.tool
def pipewire_status() -> dict[str, Any]:
    """Get a snapshot of the current PipeWire / wireplumber state.

    Parses `wpctl status` and returns a structured dict keyed by section
    ("Audio", "Video", ...) and subsection ("Devices", "Sinks", "Sources",
    "Streams", "Filters"). Each entry has {id, name, default, volume?, muted?}.

    Use this first to find the numeric id of the sink/source you want to
    operate on, then pass that id to the mutation tools below.
    """
    return _parse_status()


@mcp.tool(annotations={"destructiveHint": True})
def pipewire_set_default_sink(node_id: int) -> dict[str, Any]:
    """Set the default audio output sink to the node with the given id.

    Changing the default sink reroutes all subsequent audio streams to it.
    Existing streams already routed to a specific sink stay where they are.

    Use pipewire_status() first to find the id; do not guess.
    Returns the post-mutation status snapshot for readback verification.
    """
    _run_wpctl("set-default", str(node_id))
    return {"changed": True, "status": _parse_status()}


@mcp.tool(annotations={"destructiveHint": True})
def pipewire_set_volume(
    node_id: int,
    percent: int,
    allow_above_100: bool = False,
) -> dict[str, Any]:
    """Set the volume of a sink or source by node id, as a percent (0-100).

    Values above 100 (= analog gain boost, can clip and damage equipment)
    require allow_above_100=True as an explicit opt-in.

    Returns the post-mutation status snapshot for readback verification.
    """
    if percent < 0:
        raise ValueError("percent must be >= 0")
    if percent > 100 and not allow_above_100:
        raise ValueError("percent > 100 requires allow_above_100=True")
    _run_wpctl("set-volume", str(node_id), f"{percent}%")
    return {"changed": True, "status": _parse_status()}


def main() -> None:
    """Entry point for the `nekono-pipewire-mcp` console script."""
    mcp.run()


if __name__ == "__main__":
    main()
