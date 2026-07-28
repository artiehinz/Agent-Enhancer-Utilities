"""Small standard-library client for the Agent Enhancer Streamable HTTP MCP."""

from __future__ import annotations

import json
from threading import Lock
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class McpError(RuntimeError):
    """Raised when the transport, protocol, or invoked module reports an error."""


class McpClient:
    def __init__(self, url: str, timeout_seconds: float = 20.0) -> None:
        self.url = url
        self.timeout_seconds = timeout_seconds
        self._next_id = 1
        self._id_lock = Lock()

    def _request_id(self) -> int:
        with self._id_lock:
            request_id = self._next_id
            self._next_id += 1
            return request_id

    @staticmethod
    def _decode_response(raw: str) -> dict[str, Any]:
        stripped = raw.strip()
        if stripped.startswith("{"):
            return json.loads(stripped)

        data_lines = [
            line.removeprefix("data:").strip()
            for line in stripped.splitlines()
            if line.startswith("data:")
        ]
        if not data_lines:
            raise McpError("MCP response was neither JSON nor a data-bearing SSE event")
        return json.loads(data_lines[-1])

    def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id(),
            "method": method,
            "params": params,
        }
        request = Request(
            self.url,
            data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            headers={
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
                "User-Agent": "agent-enhancer-public-example/1.6.0",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                message = self._decode_response(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise McpError(f"MCP HTTP {exc.code}: {detail}") from exc
        except URLError as exc:
            raise McpError(f"MCP connection failed: {exc.reason}") from exc

        if "error" in message:
            raise McpError(f"MCP protocol error: {message['error']}")
        result = message.get("result")
        if not isinstance(result, dict):
            raise McpError("MCP response did not contain an object result")
        return result

    def initialize(self) -> dict[str, Any]:
        return self.request(
            "initialize",
            {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {
                    "name": "agent-enhancer-public-example",
                    "version": "1.6.0",
                },
            },
        )

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        result = self.request(
            "tools/call",
            {"name": name, "arguments": arguments},
        )
        if result.get("isError") is True:
            raise McpError(f"{name} returned an MCP tool error: {result.get('content')}")

        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            return structured

        for item in result.get("content", []):
            if item.get("type") == "text":
                try:
                    parsed = json.loads(item["text"])
                except (KeyError, TypeError, json.JSONDecodeError):
                    continue
                if isinstance(parsed, dict):
                    return parsed
        raise McpError(f"{name} did not return structured JSON")

    def invoke_module(
        self,
        slug: str,
        module_input: dict[str, Any],
        *,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        arguments: dict[str, Any] = {"slug": slug, "input": module_input}
        if idempotency_key is not None:
            arguments["idempotency_key"] = idempotency_key
        invocation = self.call_tool("lab.invoke_tool", arguments)
        if invocation.get("ok") is not True:
            raise McpError(f"{slug} invocation failed: {invocation}")
        result = invocation.get("result")
        if not isinstance(result, dict):
            raise McpError(f"{slug} invocation did not contain an object result")
        return result
