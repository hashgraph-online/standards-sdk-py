"""Parity manifest models."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ParityStatus(str, Enum):
    """Parity entry implementation status."""

    todo = "todo"
    in_progress = "in_progress"
    done = "done"
    verified = "verified"


class ParityEntry(BaseModel):
    """Single parity mapping row."""

    model_config = ConfigDict(extra="forbid")

    id: str
    source_sdk: str = Field(pattern="^(ts|go)$")
    source_symbol: str
    python_symbol: str
    status: ParityStatus
    notes: str | None = None


class ParityManifest(BaseModel):
    """Top-level parity manifest."""

    model_config = ConfigDict(extra="forbid")

    version: str
    metadata: dict[str, str]
    entries: list[ParityEntry]
