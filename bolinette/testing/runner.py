import asyncio
import sys
import traceback
from asyncio import AbstractEventLoop
from datetime import datetime
from typing import List

from bolinette import console, blnt
from bolinette import bolinette
from bolinette.testing import TestClient, Bolitest


class TestResult:
    def __init__(self, name: str, ok: bool, time: float, error: Exception = None, tb: str = None):
        self.name = name
        self.ok = ok
        self.time = time
        self.error = error
        self.traceback = tb


class TestRunner:
    def __init__(self, context: 'blnt.BolinetteContext', run_only: str):
        self.context = context
        self.run_only = run_only

    def run_tests(self, blnt_app: 'bolinette.Bolinette'):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self._run_tests(blnt_app, loop, self._gather_tests()))

    def _gather_tests(self):
        tests = []
        for test in blnt.cache.test_funcs:
            test.set_name(self.context.root_path('tests'))
            if self._match_test(test):
                tests.append(test)
        return tests

    def _match_test(self, test: Bolitest):
        if self.run_only is None:
            return True
        if '::' in self.run_only:
            return self.run_only == test.name
        return test.name.startswith(self.run_only)

    async def _run_tests(self, blnt_app: 'bolinette.Bolinette', loop: AbstractEventLoop, tests: List[Bolitest]):
        tests_start_time = datetime.now()
        test_cnt = len(tests)
        console.print('** Bolinette API Tests **')
        console.print(f'Running {test_cnt} tests ({self.run_only or "all tests"}), starting at {tests_start_time}')
        console.print('====================\n')
        results = []
        test_index = 0
        for test in tests:
            client = TestClient(blnt_app, loop)
            async with client:
                console.print(f'Running: {test.name} [{test_index + 1}/{test_cnt}]', end=' ')
                result = await self._run_test(client, test)
                if result.ok:
                    console.print(f'OK in {result.time / 1000}ms')
                else:
                    console.print(f'FAILED ({result.error.__class__.__name__}) in {result.time / 1000}ms')
                results.append(result)
            test_index += 1
        tests_end_time = datetime.now()

        err_cnt = 0
        for result in results:
            if result.error:
                err_cnt += 1
                console.error(f'\n========== ERROR: {result.name} ==========')
                console.error(result.traceback, end='')

        await asyncio.sleep(.1)
        console.print('\n====================')
        console.print(f'Ran {test_cnt} tests with {err_cnt} errors '
                      f'in {(tests_end_time - tests_start_time).seconds}s')
        if err_cnt > 0:
            sys.exit(1)

    async def _run_test(self, client: TestClient, test: Bolitest) -> TestResult:
        time_start = datetime.now()
        try:
            await test.func(client)
            time_end = datetime.now()
            return TestResult(test.name, True, (time_end - time_start).microseconds)
        except Exception as err:
            time_end = datetime.now()
            return TestResult(test.name, False, (time_end - time_start).microseconds,
                              err, traceback.format_exc())
