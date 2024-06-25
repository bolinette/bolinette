import inspect
import json
from collections.abc import AsyncIterator, Callable, Coroutine, Iterator
from typing import Any, Protocol

from bolinette.core.injection import Injection
from bolinette.core.mapping import JsonObjectEncoder
from bolinette.web.abstract import Response
from bolinette.web.resources import HttpHeaders, ResponseData


class ResponseWriter:
    def __init__(self, inject: Injection, response: Response) -> None:
        self.inject = inject
        self.response = response

    async def close(self) -> None:
        await self.response.close()

    async def _open_response(self, data: ResponseData) -> None:
        self.response.set_status(data.status)
        for header, value in data.headers.items():
            self.response.set_header(header, value)
        await self.response.open()

    async def write_result(self, result: object, data: ResponseData) -> None:
        await self._unpack_result(result, data)

    async def _unpack_result(self, result: object, data: ResponseData) -> None:
        if inspect.iscoroutine(result) or inspect.isawaitable(result):
            return await self._unpack_result(await result, data)
        if inspect.isasyncgen(result):
            return await self._write_async_iterator(result, data)
        if inspect.isgenerator(result):
            return await self._write_iterator(result, data)
        if inspect.iscoroutinefunction(result):
            return await self._unpack_result(await self.inject.call(result), data)
        if inspect.isasyncgenfunction(result) or callable(result):
            return await self._unpack_result(self.inject.call(result), data)
        await self._write_single(result, data)

    @staticmethod
    def _get_value_writer(value: Any, data: ResponseData, as_list: bool) -> "ValueWriter[Any]":
        value_writer: ValueWriter[Any] | None = None
        match value:
            case None | bytes():
                value_writer = RawValueTransformer()
            case str():
                value_writer = StringValueTransformer()
            case _ if as_list:
                value_writer = JsonListValueTransformer()
            case _:
                value_writer = JsonValueTransformer()
        if not data.has_header(HttpHeaders.ContentType):
            data.set_header(HttpHeaders.ContentType, value_writer.default_content_type())
        return value_writer

    async def _write_async_iterator(self, result: AsyncIterator[object], data: ResponseData) -> None:
        value_writer: ValueWriter[Any] | None = None
        try:
            chunk = await anext(result)
            value_writer = self._get_value_writer(chunk, data, True)
            await self._open_response(data)
            await self._write_chunk(chunk, value_writer)
            while True:
                chunk = await anext(result)
                await self._write_chunk(chunk, value_writer)
        except StopAsyncIteration:
            pass
        finally:
            if value_writer is not None:
                await self._close_writer(value_writer)

    async def _write_iterator(self, result: Iterator[object], data: ResponseData) -> None:
        value_writer: ValueWriter[Any] | None = None
        try:
            chunk = next(result)
            value_writer = self._get_value_writer(chunk, data, True)
            await self._open_response(data)
            await self._write_chunk(chunk, value_writer)
            while True:
                chunk = next(result)
                await self._write_chunk(chunk, value_writer)
        except StopIteration:
            pass
        finally:
            if value_writer is not None:
                await self._close_writer(value_writer)

    async def _write_single(self, result: Any, data: ResponseData) -> None:
        value_writer = self._get_value_writer(result, data, False)
        await self._open_response(data)
        await self._write_chunk(result, value_writer)
        await self._close_writer(value_writer)

    def _write_chunk(self, value: object, value_writer: "ValueWriter[object]") -> Coroutine[Any, Any, None]:
        return value_writer.write(self.response.write, value)

    def _close_writer(self, value_writer: "ValueWriter[object]") -> Coroutine[Any, Any, None]:
        return value_writer.close(self.response.write)


class ValueWriter[T](Protocol):
    def default_content_type(self) -> str: ...
    async def write(self, write: Callable[[bytes], Coroutine[Any, Any, None]], value: T) -> None: ...
    async def close(self, write: Callable[[bytes], Coroutine[Any, Any, None]]) -> None: ...


class RawValueTransformer:
    def default_content_type(self) -> str:
        return "application/octet-stream"

    def write(self, write: Callable[[bytes], Coroutine[Any, Any, None]], value: bytes) -> Coroutine[Any, Any, None]:
        return write(value)

    async def close(self, write: Callable[[bytes], Coroutine[Any, Any, None]]) -> None:
        pass


class StringValueTransformer:
    def default_content_type(self) -> str:
        return "text/plain"

    def write(self, write: Callable[[bytes], Coroutine[Any, Any, None]], value: str) -> Coroutine[Any, Any, None]:
        return write(value.encode())

    async def close(self, write: Callable[[bytes], Coroutine[Any, Any, None]]) -> None:
        pass


class JsonValueTransformer:
    def __init__(self) -> None:
        self.item = 0

    def default_content_type(self) -> str:
        return "application/json"

    def write(self, write: Callable[[bytes], Coroutine[Any, Any, None]], value: Any) -> Coroutine[Any, Any, None]:
        return write(json.dumps(value, cls=JsonObjectEncoder, separators=(", ", ": ")).encode())

    async def close(self, write: Callable[[bytes], Coroutine[Any, Any, None]]) -> None:
        pass


class JsonListValueTransformer:
    def __init__(self) -> None:
        self.item = 0

    def default_content_type(self) -> str:
        return "application/json"

    async def write(self, write: Callable[[bytes], Coroutine[Any, Any, None]], value: Any) -> None:
        if self.item == 0:
            await write(b"[")
        else:
            await write(b", ")
        await write(json.dumps(value, cls=JsonObjectEncoder, separators=(", ", ": ")).encode())
        self.item += 1

    def close(self, write: Callable[[bytes], Coroutine[Any, Any, None]]) -> Coroutine[Any, Any, None]:
        return write(b"]")
