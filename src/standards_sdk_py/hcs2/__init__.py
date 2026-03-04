"""HCS-2 module."""

from standards_sdk_py.hcs2.client import AsyncHcs2Client, Hcs2Client
from standards_sdk_py.hcs2.models import (
    CreateRegistryOptions,
    CreateRegistryResult,
    DeleteEntryOptions,
    Hcs2DeleteMessage,
    Hcs2Message,
    Hcs2MigrateMessage,
    Hcs2Operation,
    Hcs2RegisterMessage,
    Hcs2RegistryType,
    Hcs2UpdateMessage,
    MigrateRegistryOptions,
    OperationResult,
    QueryRegistryOptions,
    RegisterEntryOptions,
    RegistryEntry,
    TopicRegistry,
    UpdateEntryOptions,
)

HCS2Client = Hcs2Client
AsyncHCS2Client = AsyncHcs2Client

__all__ = [
    "AsyncHCS2Client",
    "AsyncHcs2Client",
    "CreateRegistryOptions",
    "CreateRegistryResult",
    "DeleteEntryOptions",
    "HCS2Client",
    "Hcs2Client",
    "Hcs2DeleteMessage",
    "Hcs2Message",
    "Hcs2MigrateMessage",
    "Hcs2Operation",
    "Hcs2RegisterMessage",
    "Hcs2RegistryType",
    "Hcs2UpdateMessage",
    "MigrateRegistryOptions",
    "OperationResult",
    "QueryRegistryOptions",
    "RegisterEntryOptions",
    "RegistryEntry",
    "TopicRegistry",
    "UpdateEntryOptions",
]
