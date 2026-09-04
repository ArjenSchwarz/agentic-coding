"""Warning collector threaded through parsing and rendering.

Each warning is printed to stderr the moment it is added, so a crash later
in the run still leaves the earlier warnings visible, and the full list is
available afterwards for the page.
"""
from __future__ import annotations

import sys


class Warnings:
    def __init__(self) -> None:
        self.items: list[str] = []

    def add(self, message: str) -> None:
        self.items.append(message)
        print(f"warning: {message}", file=sys.stderr)
