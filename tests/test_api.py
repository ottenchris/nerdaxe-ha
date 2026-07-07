from __future__ import annotations

import unittest
from typing import Any

try:
    from custom_components.nerdaxe_miner.api import MinerApiClient, MinerApiError
except ModuleNotFoundError as err:
    if err.name == "aiohttp":
        raise unittest.SkipTest("aiohttp is not installed") from err
    raise


class FakeResponse:
    def __init__(
        self,
        *,
        status: int = 200,
        payload: Any = None,
        text: str = "",
    ) -> None:
        self.status = status
        self._payload = payload if payload is not None else {}
        self._text = text

    async def __aenter__(self) -> FakeResponse:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def json(self, *, content_type: str | None = None) -> Any:
        return self._payload

    async def text(self) -> str:
        return self._text


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append({"method": method, "url": url, "kwargs": kwargs})
        return self.response


class MinerApiClientTest(unittest.IsolatedAsyncioTestCase):
    async def test_get_info_constructs_get_system_info_request(self) -> None:
        session = FakeSession(FakeResponse(payload={"hashRate": 1}))
        client = MinerApiClient("miner.local", session)  # type: ignore[arg-type]

        payload = await client.async_get_info()

        self.assertEqual(payload, {"hashRate": 1})
        self.assertEqual(session.calls[0]["method"], "GET")
        self.assertEqual(
            session.calls[0]["url"],
            "http://miner.local/api/system/info",
        )

    async def test_restart_constructs_post_restart_request_without_body(self) -> None:
        session = FakeSession(FakeResponse(text='{"message":"restarting"}'))
        client = MinerApiClient("http://miner.local/", session)  # type: ignore[arg-type]

        await client.async_restart()

        self.assertEqual(session.calls[0]["method"], "POST")
        self.assertEqual(
            session.calls[0]["url"],
            "http://miner.local/api/system/restart",
        )
        self.assertNotIn("json", session.calls[0]["kwargs"])
        self.assertNotIn("data", session.calls[0]["kwargs"])

    async def test_http_error_raises_api_error_with_body_preview(self) -> None:
        session = FakeSession(FakeResponse(status=500, text="broken miner"))
        client = MinerApiClient("miner.local", session)  # type: ignore[arg-type]

        with self.assertRaises(MinerApiError) as ctx:
            await client.async_get_info()

        self.assertEqual(ctx.exception.status, 500)
        self.assertEqual(ctx.exception.body_preview, "broken miner")
        self.assertEqual(ctx.exception.url, "http://miner.local/api/system/info")


if __name__ == "__main__":
    unittest.main()
