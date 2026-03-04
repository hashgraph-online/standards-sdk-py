"""HCS client method-surface parity checks."""

from __future__ import annotations

import re

import pytest

from standards_sdk_py.hcs2 import AsyncHCS2Client, HCS2Client
from standards_sdk_py.hcs3 import HCS, AsyncHCS3Client
from standards_sdk_py.hcs5 import AsyncHCS5Client, HCS5Client
from standards_sdk_py.hcs6 import AsyncHCS6Client, HCS6Client
from standards_sdk_py.hcs7 import AsyncHCS7Client, HCS7Client
from standards_sdk_py.hcs10 import AsyncHCS10Client, HCS10Client
from standards_sdk_py.hcs11 import AsyncHCS11Client, HCS11Client
from standards_sdk_py.hcs12 import AsyncHCS12Client, HCS12Client
from standards_sdk_py.hcs14 import AsyncHCS14Client, HCS14Client
from standards_sdk_py.hcs15 import AsyncHCS15Client, HCS15Client
from standards_sdk_py.hcs16 import AsyncHCS16Client, HCS16Client
from standards_sdk_py.hcs17 import AsyncHCS17Client, HCS17Client
from standards_sdk_py.hcs18 import AsyncHCS18Client, HCS18Client
from standards_sdk_py.hcs20 import AsyncHCS20Client, HCS20Client
from standards_sdk_py.hcs21 import AsyncHCS21Client, HCS21Client
from standards_sdk_py.hcs26 import AsyncHCS26Client, HCS26Client
from standards_sdk_py.hcs27 import AsyncHCS27Client, HCS27Client
from standards_sdk_py.shared.hcs_method_inventory import HCS_STANDARD_METHODS

_CAMEL_BOUNDARY = re.compile(r"(?<!^)(?=[A-Z])")
_TEST_OPERATOR_ID = "0.0.1001"
_TEST_OPERATOR_KEY = (
    "302e020100300506032b657004220420fb77695921a5c79474d57c42006f03ff"
    "178688514d797fb30f60fd0fc9e82716"
)


def _camel_to_snake(name: str) -> str:
    return _CAMEL_BOUNDARY.sub("_", name).lower()


_SYNC_CLASS_MAP: dict[str, type] = {
    "hcs2": HCS2Client,
    "hcs3": HCS,
    "hcs5": HCS5Client,
    "hcs6": HCS6Client,
    "hcs7": HCS7Client,
    "hcs10": HCS10Client,
    "hcs11": HCS11Client,
    "hcs12": HCS12Client,
    "hcs14": HCS14Client,
    "hcs15": HCS15Client,
    "hcs16": HCS16Client,
    "hcs17": HCS17Client,
    "hcs18": HCS18Client,
    "hcs20": HCS20Client,
    "hcs21": HCS21Client,
    "hcs26": HCS26Client,
    "hcs27": HCS27Client,
}

_ASYNC_CLASS_MAP: dict[str, type] = {
    "hcs2": AsyncHCS2Client,
    "hcs3": AsyncHCS3Client,
    "hcs5": AsyncHCS5Client,
    "hcs6": AsyncHCS6Client,
    "hcs7": AsyncHCS7Client,
    "hcs10": AsyncHCS10Client,
    "hcs11": AsyncHCS11Client,
    "hcs12": AsyncHCS12Client,
    "hcs14": AsyncHCS14Client,
    "hcs15": AsyncHCS15Client,
    "hcs16": AsyncHCS16Client,
    "hcs17": AsyncHCS17Client,
    "hcs18": AsyncHCS18Client,
    "hcs20": AsyncHCS20Client,
    "hcs21": AsyncHCS21Client,
    "hcs26": AsyncHCS26Client,
    "hcs27": AsyncHCS27Client,
}


def test_hcs_method_surface_presence() -> None:
    for standard, methods in HCS_STANDARD_METHODS.items():
        sync_cls = _SYNC_CLASS_MAP[standard]
        async_cls = _ASYNC_CLASS_MAP[standard]
        for method in methods:
            snake = _camel_to_snake(method)
            assert hasattr(sync_cls, method), f"{sync_cls.__name__} missing {method}"
            assert hasattr(sync_cls, snake), f"{sync_cls.__name__} missing {snake}"
            assert hasattr(async_cls, method), f"{async_cls.__name__} missing {method}"
            assert hasattr(async_cls, snake), f"{async_cls.__name__} missing {snake}"


def test_hcs2_sdk_client_initializes_with_operator_credentials() -> None:
    client = HCS2Client(
        operator_id=_TEST_OPERATOR_ID,
        operator_key=_TEST_OPERATOR_KEY,
        network="testnet",
    )
    assert isinstance(client.getKeyType(), str)


@pytest.mark.asyncio
async def test_hcs2_async_sdk_client_initializes_with_operator_credentials() -> None:
    client = AsyncHCS2Client(
        operator_id=_TEST_OPERATOR_ID,
        operator_key=_TEST_OPERATOR_KEY,
        network="testnet",
    )
    result = await client.getKeyType()
    assert isinstance(result, str)
