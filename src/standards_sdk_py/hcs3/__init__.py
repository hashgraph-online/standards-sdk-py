"""HCS-3 module."""

# ruff: noqa: N802

from __future__ import annotations

from standards_sdk_py.shared.http import AsyncHttpTransport, SyncHttpTransport
from standards_sdk_py.shared.operation_dispatch import (
    AsyncTypedOperationClient,
    OperationOptions,
    TypedOperationClient,
)
from standards_sdk_py.shared.types import JsonValue


class Hcs3Client(TypedOperationClient):
    """Synchronous HCS-3 client."""

    def __init__(self, transport: SyncHttpTransport) -> None:
        super().__init__("hcs3", transport)

    def error(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("error", options=options, **kwargs)

    def fetchWithRetry(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("fetchWithRetry", options=options, **kwargs)

    def init(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("init", options=options, **kwargs)

    def isDuplicate(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("isDuplicate", options=options, **kwargs)

    def loadAndPlayAudio(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("loadAndPlayAudio", options=options, **kwargs)

    def loadConfigFromHTML(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("loadConfigFromHTML", options=options, **kwargs)

    def loadGLB(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("loadGLB", options=options, **kwargs)

    def loadImage(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("loadImage", options=options, **kwargs)

    def loadMedia(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("loadMedia", options=options, **kwargs)

    def loadModuleExports(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("loadModuleExports", options=options, **kwargs)

    def loadResource(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("loadResource", options=options, **kwargs)

    def loadScript(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("loadScript", options=options, **kwargs)

    def loadStylesheet(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("loadStylesheet", options=options, **kwargs)

    def log(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("log", options=options, **kwargs)

    def pauseAudio(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("pauseAudio", options=options, **kwargs)

    def playAudio(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("playAudio", options=options, **kwargs)

    def preloadAudio(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("preloadAudio", options=options, **kwargs)

    def preloadImage(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("preloadImage", options=options, **kwargs)

    def processQueue(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("processQueue", options=options, **kwargs)

    def retrieveHCS1Data(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("retrieveHCS1Data", options=options, **kwargs)

    def sleep(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("sleep", options=options, **kwargs)

    def updateLoadingStatus(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return self._invoke_typed("updateLoadingStatus", options=options, **kwargs)

    fetch_with_retry = fetchWithRetry
    is_duplicate = isDuplicate
    load_and_play_audio = loadAndPlayAudio
    load_config_from_h_t_m_l = loadConfigFromHTML
    load_g_l_b = loadGLB
    load_image = loadImage
    load_media = loadMedia
    load_module_exports = loadModuleExports
    load_resource = loadResource
    load_script = loadScript
    load_stylesheet = loadStylesheet
    pause_audio = pauseAudio
    play_audio = playAudio
    preload_audio = preloadAudio
    preload_image = preloadImage
    process_queue = processQueue
    retrieve_h_c_s1_data = retrieveHCS1Data
    update_loading_status = updateLoadingStatus


class AsyncHcs3Client(AsyncTypedOperationClient):
    """Asynchronous HCS-3 client."""

    def __init__(self, transport: AsyncHttpTransport) -> None:
        super().__init__("hcs3", transport)

    async def error(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("error", options=options, **kwargs)

    async def fetchWithRetry(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("fetchWithRetry", options=options, **kwargs)

    async def init(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("init", options=options, **kwargs)

    async def isDuplicate(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("isDuplicate", options=options, **kwargs)

    async def loadAndPlayAudio(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("loadAndPlayAudio", options=options, **kwargs)

    async def loadConfigFromHTML(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("loadConfigFromHTML", options=options, **kwargs)

    async def loadGLB(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("loadGLB", options=options, **kwargs)

    async def loadImage(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("loadImage", options=options, **kwargs)

    async def loadMedia(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("loadMedia", options=options, **kwargs)

    async def loadModuleExports(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("loadModuleExports", options=options, **kwargs)

    async def loadResource(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("loadResource", options=options, **kwargs)

    async def loadScript(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("loadScript", options=options, **kwargs)

    async def loadStylesheet(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("loadStylesheet", options=options, **kwargs)

    async def log(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("log", options=options, **kwargs)

    async def pauseAudio(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("pauseAudio", options=options, **kwargs)

    async def playAudio(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("playAudio", options=options, **kwargs)

    async def preloadAudio(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("preloadAudio", options=options, **kwargs)

    async def preloadImage(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("preloadImage", options=options, **kwargs)

    async def processQueue(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("processQueue", options=options, **kwargs)

    async def retrieveHCS1Data(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("retrieveHCS1Data", options=options, **kwargs)

    async def sleep(self, options: OperationOptions = None, **kwargs: object) -> JsonValue:
        return await self._invoke_typed("sleep", options=options, **kwargs)

    async def updateLoadingStatus(
        self, options: OperationOptions = None, **kwargs: object
    ) -> JsonValue:
        return await self._invoke_typed("updateLoadingStatus", options=options, **kwargs)

    fetch_with_retry = fetchWithRetry
    is_duplicate = isDuplicate
    load_and_play_audio = loadAndPlayAudio
    load_config_from_h_t_m_l = loadConfigFromHTML
    load_g_l_b = loadGLB
    load_image = loadImage
    load_media = loadMedia
    load_module_exports = loadModuleExports
    load_resource = loadResource
    load_script = loadScript
    load_stylesheet = loadStylesheet
    pause_audio = pauseAudio
    play_audio = playAudio
    preload_audio = preloadAudio
    preload_image = preloadImage
    process_queue = processQueue
    retrieve_h_c_s1_data = retrieveHCS1Data
    update_loading_status = updateLoadingStatus


HCS3Client = Hcs3Client
AsyncHCS3Client = AsyncHcs3Client
HCS = Hcs3Client
AsyncHCS = AsyncHcs3Client

__all__ = [
    "AsyncHCS3Client",
    "AsyncHcs3Client",
    "HCS3Client",
    "Hcs3Client",
    "AsyncHCS",
    "HCS",
]
