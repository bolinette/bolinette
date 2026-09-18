import inspect
import json
from collections.abc import AsyncIterator, Callable, Iterator
from types import CoroutineType
from typing import Any, Protocol

from soupape import AsyncInjector

from bolinette.core.mapping import Mapper
from bolinette.web._abstract import Response
from bolinette.web._headers import HttpHeaders
from bolinette.web._json import to_json_value
from bolinette.web._resources._data import ResponseData


class ResponseWriter:
    def __init__(self, injector: AsyncInjector, mapper: Mapper, response: Response) -> None:
        self.injector = injector
        self.mapper = mapper
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
            return await self._unpack_result(await self.injector.call(result), data)
        if inspect.isasyncgenfunction(result) or callable(result):
            return await self._unpack_result(await self.injector.call(result), data)
        await self._write_single(result, data)

    def to_json_value(self, value: Any) -> Any:
        return to_json_value(self.mapper, value)

    def _get_value_writer(self, value: Any, data: ResponseData, as_list: bool) -> "ValueWriter[Any]":
        value_writer: ValueWriter[Any]
        match value:
            case None | bytes():
                value_writer = RawValueTransformer()
            case str():
                value_writer = StringValueTransformer()
            case _ if as_list:
                value_writer = JsonListValueTransformer(self.to_json_value)
            case _:
                value_writer = JsonValueTransformer(self.to_json_value)
        if not data.has_header(HttpHeaders.ContentType):
            data.set_header(HttpHeaders.ContentType, value_writer.default_content_type())
        return value_writer

    async def _write_async_iterator(self, result: AsyncIterator[object], data: ResponseData) -> None:
        try:
            chunk = await anext(result)
        except StopAsyncIteration:
            return await self._write_empty_list(data)
        value_writer = self._get_value_writer(chunk, data, True)
        await self._open_response(data)
        try:
            await self._write_chunk(chunk, value_writer)
            while True:
                chunk = await anext(result)
                await self._write_chunk(chunk, value_writer)
        except StopAsyncIteration:
            pass
        finally:
            await self._close_writer(value_writer)

    async def _write_iterator(self, result: Iterator[object], data: ResponseData) -> None:
        try:
            chunk = next(result)
        except StopIteration:
            return await self._write_empty_list(data)
        value_writer = self._get_value_writer(chunk, data, True)
        await self._open_response(data)
        try:
            await self._write_chunk(chunk, value_writer)
            while True:
                chunk = next(result)
                await self._write_chunk(chunk, value_writer)
        except StopIteration:
            pass
        finally:
            await self._close_writer(value_writer)

    async def _write_empty_list(self, data: ResponseData) -> None:
        value_writer = JsonListValueTransformer(self.to_json_value)
        if not data.has_header(HttpHeaders.ContentType):
            data.set_header(HttpHeaders.ContentType, value_writer.default_content_type())
        await self._open_response(data)
        await self.response.write(b"[")
        await self._close_writer(value_writer)

    async def _write_single(self, result: Any, data: ResponseData) -> None:
        value_writer = self._get_value_writer(result, data, False)
        await self._open_response(data)
        await self._write_chunk(result, value_writer)
        await self._close_writer(value_writer)

    def _write_chunk(self, value: object, value_writer: "ValueWriter[object]") -> CoroutineType[Any, Any, None]:
        return value_writer.write(self.response.write, value)

    def _close_writer(self, value_writer: "ValueWriter[object]") -> CoroutineType[Any, Any, None]:
        return value_writer.close(self.response.write)


class ValueWriter[T](Protocol):
    def default_content_type(self) -> str: ...
    async def write(self, write: Callable[[bytes], CoroutineType[Any, Any, None]], value: T) -> None: ...
    async def close(self, write: Callable[[bytes], CoroutineType[Any, Any, None]]) -> None: ...


class RawValueTransformer:
    def default_content_type(self) -> str:
        return "application/octet-stream"

    def write(
        self, write: Callable[[bytes], CoroutineType[Any, Any, None]], value: bytes | None
    ) -> CoroutineType[Any, Any, None]:
        return write(b"" if value is None else value)

    async def close(self, write: Callable[[bytes], CoroutineType[Any, Any, None]]) -> None:
        pass


class StringValueTransformer:
    def default_content_type(self) -> str:
        return "text/plain"

    def write(
        self, write: Callable[[bytes], CoroutineType[Any, Any, None]], value: str
    ) -> CoroutineType[Any, Any, None]:
        return write(value.encode())

    async def close(self, write: Callable[[bytes], CoroutineType[Any, Any, None]]) -> None:
        pass


class JsonValueTransformer:
    def __init__(self, encode: Callable[[Any], Any]) -> None:
        self.encode = encode
        self.item = 0

    def default_content_type(self) -> str:
        return "application/json"

    def write(
        self, write: Callable[[bytes], CoroutineType[Any, Any, None]], value: Any
    ) -> CoroutineType[Any, Any, None]:
        return write(json.dumps(self.encode(value), separators=(", ", ": ")).encode())

    async def close(self, write: Callable[[bytes], CoroutineType[Any, Any, None]]) -> None:
        pass


class JsonListValueTransformer:
    def __init__(self, encode: Callable[[Any], Any]) -> None:
        self.encode = encode
        self.item = 0

    def default_content_type(self) -> str:
        return "application/json"

    async def write(self, write: Callable[[bytes], CoroutineType[Any, Any, None]], value: Any) -> None:
        if self.item == 0:
            await write(b"[")
        else:
            await write(b", ")
        await write(json.dumps(self.encode(value), separators=(", ", ": ")).encode())
        self.item += 1

    def close(self, write: Callable[[bytes], CoroutineType[Any, Any, None]]) -> CoroutineType[Any, Any, None]:
        return write(b"]")
