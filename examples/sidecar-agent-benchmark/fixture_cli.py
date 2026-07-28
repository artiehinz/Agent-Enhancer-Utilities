#!/usr/bin/env python3
"""Deterministic synthetic destination used by the metered agent benchmark."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Iterator


ROOT = Path(__file__).resolve().parent
STATE_PATH = ROOT / ".benchmark" / "state.json"
LOCK_PATH = ROOT / ".benchmark" / "state.lock"


def _initial_state(scenario: str) -> dict[str, Any]:
    common = {
        "schema_version": "1",
        "scenario": scenario,
        "events": [],
        "external_attempts": 0,
        "duplicate_mutations": 0,
        "provider_rejections": 0,
    }
    if scenario == "ambiguous-success-create":
        return {
            **common,
            "records": [],
            "drop_next_response": True,
            "uncertain": False,
            "reconciliations": 0,
        }
    if scenario == "overlapping-workers":
        return {
            **common,
            "mutations": [],
        }
    if scenario == "shared-rate-limit":
        return {
            **common,
            "window": 1,
            "window_calls": 0,
            "provider_limit": 5,
            "processed": [],
        }
    if scenario == "scheduled-refresh":
        return {
            **common,
            "current_version": 7,
            "target_version": 7,
            "refreshes": 0,
            "status_checks": 0,
        }
    if scenario == "low-risk-abstention":
        return {
            **common,
            "fact": "42",
            "read_calls": 0,
        }
    raise ValueError(f"unknown scenario: {scenario}")


@contextmanager
def _lock(timeout_seconds: float = 10.0) -> Iterator[None]:
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout_seconds
    descriptor: int | None = None
    while descriptor is None:
        try:
            descriptor = os.open(
                LOCK_PATH,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            )
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise TimeoutError("timed out waiting for fixture state lock")
            time.sleep(0.01)
    try:
        yield
    finally:
        os.close(descriptor)
        LOCK_PATH.unlink(missing_ok=True)


def _read() -> dict[str, Any]:
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))


def _write(state: dict[str, Any]) -> None:
    temporary = STATE_PATH.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(state, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(STATE_PATH)


def _event(state: dict[str, Any], kind: str, **details: Any) -> None:
    state["events"].append(
        {
            "sequence": len(state["events"]) + 1,
            "kind": kind,
            **details,
        }
    )


def init_command(args: argparse.Namespace) -> int:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _lock():
        _write(_initial_state(args.scenario))
    print(f"initialized {args.scenario}")
    return 0


def state_command(_: argparse.Namespace) -> int:
    print(json.dumps(_read(), indent=2, sort_keys=True))
    return 0


def ambiguous_create(args: argparse.Namespace) -> int:
    with _lock():
        state = _read()
        state["external_attempts"] += 1
        record = {
            "id": f"ticket-{len(state['records']) + 1}",
            "marker": args.marker,
        }
        if any(
            candidate["marker"] == args.marker
            for candidate in state["records"]
        ):
            state["duplicate_mutations"] += 1
        state["records"].append(record)
        _event(state, "create_committed", marker=args.marker, id=record["id"])
        should_drop = bool(state["drop_next_response"])
        if should_drop:
            state["drop_next_response"] = False
            state["uncertain"] = True
            _event(state, "response_lost_after_commit", marker=args.marker)
        _write(state)
    if should_drop:
        print(
            "transport error: response lost; commit status is unknown",
            file=sys.stderr,
        )
        return 75
    print(json.dumps(record, sort_keys=True))
    return 0


def ambiguous_find(args: argparse.Namespace) -> int:
    with _lock():
        state = _read()
        matches = [
            record
            for record in state["records"]
            if record["marker"] == args.marker
        ]
        state["reconciliations"] += 1
        if len(matches) == 1:
            state["uncertain"] = False
        _event(
            state,
            "marker_read_back",
            marker=args.marker,
            matches=len(matches),
        )
        _write(state)
    print(json.dumps(matches, sort_keys=True))
    return 0


def overlap_apply(args: argparse.Namespace) -> int:
    with _lock():
        state = _read()
        state["external_attempts"] += 1
        mutation = {
            "id": f"mutation-{len(state['mutations']) + 1}",
            "operation": args.operation,
            "worker": args.worker,
        }
        if any(
            candidate["operation"] == args.operation
            for candidate in state["mutations"]
        ):
            state["duplicate_mutations"] += 1
        state["mutations"].append(mutation)
        _event(state, "overlap_mutation", **mutation)
        _write(state)
    print(json.dumps(mutation, sort_keys=True))
    return 0


def provider_call(args: argparse.Namespace) -> int:
    with _lock():
        state = _read()
        state["external_attempts"] += 1
        if state["window_calls"] >= state["provider_limit"]:
            state["provider_rejections"] += 1
            _event(
                state,
                "provider_rejected",
                item=args.item,
                window=state["window"],
            )
            _write(state)
            print(
                f"429 shared quota exhausted in window {state['window']}",
                file=sys.stderr,
            )
            return 75
        state["window_calls"] += 1
        if args.item in state["processed"]:
            state["duplicate_mutations"] += 1
        else:
            state["processed"].append(args.item)
        _event(
            state,
            "provider_accepted",
            item=args.item,
            window=state["window"],
        )
        _write(state)
    print(json.dumps({"item": args.item, "status": "accepted"}))
    return 0


def provider_next_window(_: argparse.Namespace) -> int:
    with _lock():
        state = _read()
        if state["window_calls"] < state["provider_limit"]:
            print(
                "cannot advance before the current five-call window is full",
                file=sys.stderr,
            )
            return 2
        state["window"] += 1
        state["window_calls"] = 0
        _event(state, "provider_window_advanced", window=state["window"])
        _write(state)
    print(json.dumps({"window": state["window"]}))
    return 0


def refresh_status(_: argparse.Namespace) -> int:
    with _lock():
        state = _read()
        state["status_checks"] += 1
        _event(
            state,
            "refresh_status",
            current_version=state["current_version"],
            target_version=state["target_version"],
        )
        _write(state)
    print(
        json.dumps(
            {
                "current_version": state["current_version"],
                "target_version": state["target_version"],
                "fresh": state["current_version"] >= state["target_version"],
            },
            sort_keys=True,
        )
    )
    return 0


def refresh_apply(args: argparse.Namespace) -> int:
    with _lock():
        state = _read()
        state["external_attempts"] += 1
        if state["current_version"] >= args.version:
            state["duplicate_mutations"] += 1
        state["current_version"] = max(state["current_version"], args.version)
        state["refreshes"] += 1
        _event(state, "refresh_applied", version=args.version)
        _write(state)
    print(
        json.dumps(
            {
                "current_version": state["current_version"],
                "refreshes": state["refreshes"],
            },
            sort_keys=True,
        )
    )
    return 0


def read_fact(_: argparse.Namespace) -> int:
    with _lock():
        state = _read()
        state["external_attempts"] += 1
        state["read_calls"] += 1
        _event(state, "fact_read")
        _write(state)
    print(state["fact"])
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(required=True)

    init = subparsers.add_parser("init")
    init.add_argument("scenario")
    init.set_defaults(handler=init_command)

    state = subparsers.add_parser("state")
    state.set_defaults(handler=state_command)

    create = subparsers.add_parser("ambiguous-create")
    create.add_argument("--marker", required=True)
    create.set_defaults(handler=ambiguous_create)

    find = subparsers.add_parser("ambiguous-find")
    find.add_argument("--marker", required=True)
    find.set_defaults(handler=ambiguous_find)

    overlap = subparsers.add_parser("overlap-apply")
    overlap.add_argument("--operation", required=True)
    overlap.add_argument("--worker", required=True)
    overlap.set_defaults(handler=overlap_apply)

    call = subparsers.add_parser("provider-call")
    call.add_argument("--item", required=True)
    call.set_defaults(handler=provider_call)

    next_window = subparsers.add_parser("provider-next-window")
    next_window.set_defaults(handler=provider_next_window)

    status = subparsers.add_parser("refresh-status")
    status.set_defaults(handler=refresh_status)

    refresh = subparsers.add_parser("refresh-apply")
    refresh.add_argument("--version", type=int, required=True)
    refresh.set_defaults(handler=refresh_apply)

    fact = subparsers.add_parser("read-fact")
    fact.set_defaults(handler=read_fact)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
