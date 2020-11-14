import asyncio
import sys
import traceback
from asyncio import AbstractEventLoop
from datetime import datetime
from typing import Callable, Awaitable, List

from bolinette import blnt
from bolinette import bolinette
from bolinette.testing import TestClient
from bolinette.utils import console


class TestResult:
    def __init__(self, name: str, ok: bool, time: float, error: Exception = None, tb: str = None):
        self.name = name
        self.ok = ok
        self.time = time
        self.error = error
        self.traceback = tb


class TestRunner:
    def __init__(self):
        pass

    def run_tests(self, blnt_app: 'bolinette.Bolinette'):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._run_tests(blnt_app, loop, blnt.cache.test_funcs))

    async def _run_tests(self, blnt_app: 'bolinette.Bolinette', loop: AbstractEventLoop,
                         functions: List[Callable[[TestClient], Awaitable[None]]]):
        tests_start_time = datetime.now()
        test_cnt = len(functions)
        console.print('** Bolinette API Tests **')
        console.print(f'Running {test_cnt} tests, starting at {tests_start_time}')
        console.print('====================\n')
        results = []
        test_index = 0
        for test_func in functions:
            client = TestClient(blnt_app, loop)
            async with client:
                console.print(f'Running: {test_func.__name__} [{test_index + 1}/{test_cnt}]', end=' ')
                result = await self._run_test(client, test_func)
                if result.ok:
                    console.print(f'OK in {result.time / 1000}ms')
                else:
                    console.print(f'FAILED ({result.error.__class__.__name__}) in {result.time / 1000}ms')
                results.append(result)
            test_index += 1
        tests_end_time = datetime.now()
        console.print()

        err_cnt = 0
        for result in results:
            if result.error:
                err_cnt += 1
                console.error(f'========== ERROR: {result.name} ==========')
                console.error(result.traceback)

        await asyncio.sleep(.1)
        console.print('====================')
        console.print(f'Ran {test_cnt} tests with {err_cnt} errors '
                      f'in {(tests_end_time - tests_start_time).seconds}s')
        if err_cnt > 0:
            sys.exit(1)

    async def _run_test(self, client: TestClient, test_func: Callable[[TestClient], Awaitable[None]]) -> TestResult:
        time_start = datetime.now()
        try:
            await test_func(client)
            time_end = datetime.now()
            return TestResult(test_func.__name__, True, (time_end - time_start).microseconds)
        except AssertionError as err:
            time_end = datetime.now()
            return TestResult(test_func.__name__, False, (time_end - time_start).microseconds,
                              err, traceback.format_exc())
