"""Reference adapters for Reliability Sidecar Contract v1."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
from typing import Any
import uuid


CONTRACT_VERSION = "1"
STAGES = {
    "planned",
    "claimed",
    "external_attempt_started",
    "external_result_uncertain",
    "caller_verified",
    "failed",
    "compensated",
}
FINAL_STAGES = {"caller_verified", "compensated"}
TRANSITIONS = {
    "planned": {"claimed", "failed"},
    "claimed": {"external_attempt_started", "failed"},
    "external_attempt_started": {
        "external_result_uncertain",
        "caller_verified",
        "failed",
    },
    "external_result_uncertain": {
        "caller_verified",
        "failed",
        "compensated",
    },
    "failed": set(),
    "caller_verified": set(),
    "compensated": set(),
}


class ContractError(RuntimeError):
    """Raised when an adapter operation violates the portable contract."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def opaque_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"{prefix}_{digest[:32]}"


def new_idempotency_key() -> str:
    return f"benchmark_{uuid.uuid4().hex}"


class InMemoryReliabilityAdapter:
    """Deterministic single-process reference adapter."""

    def __init__(self) -> None:
        self._checkpoints: dict[str, dict[str, Any]] = {}
        self.calls = 0

    def _snapshot(self, operation_id: str) -> dict[str, Any]:
        return deepcopy(self._checkpoints[operation_id])

    def claim(
        self,
        operation_id: str,
        holder_id: str,
    ) -> tuple[bool, dict[str, Any]]:
        self.calls += 1
        existing = self._checkpoints.get(operation_id)
        if existing is not None:
            return existing["holder_id"] == holder_id, self._snapshot(operation_id)
        checkpoint = {
            "contract_version": CONTRACT_VERSION,
            "operation_id": operation_id,
            "stage": "claimed",
            "generation": 1,
            "holder_id": holder_id,
            "updated_at": now_iso(),
            "external_proof": False,
        }
        self._checkpoints[operation_id] = checkpoint
        return True, self._snapshot(operation_id)

    def transition(
        self,
        operation_id: str,
        holder_id: str,
        to_stage: str,
    ) -> dict[str, Any]:
        self.calls += 1
        if to_stage not in STAGES:
            raise ContractError(f"unknown stage: {to_stage}")
        checkpoint = self._checkpoints.get(operation_id)
        if checkpoint is None:
            raise ContractError("checkpoint not found")
        if checkpoint["holder_id"] != holder_id:
            raise ContractError("checkpoint is owned by another holder")
        from_stage = checkpoint["stage"]
        if to_stage not in TRANSITIONS[from_stage]:
            raise ContractError(f"invalid transition: {from_stage} -> {to_stage}")
        checkpoint["stage"] = to_stage
        checkpoint["updated_at"] = now_iso()
        if to_stage in FINAL_STAGES or to_stage == "failed":
            checkpoint["holder_id"] = None
        return self._snapshot(operation_id)

    def status(self, operation_id: str) -> dict[str, Any]:
        self.calls += 1
        if operation_id not in self._checkpoints:
            raise ContractError("checkpoint not found")
        return self._snapshot(operation_id)


class RemoteAgentEnhancerAdapter:
    """Optional adapter for the live workflow-checkpoint MCP module."""

    def __init__(
        self,
        client: Any,
        *,
        namespace: str,
        claim_ttl_seconds: int = 60,
        state_ttl_seconds: int = 120,
    ) -> None:
        self.client = client
        self.namespace = namespace
        self.claim_ttl_seconds = claim_ttl_seconds
        self.state_ttl_seconds = state_ttl_seconds
        self._shadow_stage: dict[str, str] = {}

    def claim(
        self,
        operation_id: str,
        holder_id: str,
    ) -> tuple[bool, dict[str, Any]]:
        result = self.client.invoke_module(
            "workflow-checkpoint",
            {
                "action": "claim",
                "namespace": self.namespace,
                "workflow_key": operation_id,
                "holder": holder_id,
                "claim_ttl_seconds": self.claim_ttl_seconds,
                "state_ttl_seconds": self.state_ttl_seconds,
                "retry_failed": False,
            },
            idempotency_key=new_idempotency_key(),
        )
        self._shadow_stage[operation_id] = result["stage"]
        return bool(result["acquired"]), self._portable(result, operation_id)

    def transition(
        self,
        operation_id: str,
        holder_id: str,
        generation: int,
        to_stage: str,
        *,
        evidence_type: str | None = None,
        evidence_fingerprint: str | None = None,
    ) -> dict[str, Any]:
        if to_stage == "external_attempt_started":
            self._shadow_stage[operation_id] = to_stage
            return {
                "contract_version": CONTRACT_VERSION,
                "operation_id": operation_id,
                "stage": to_stage,
                "generation": generation,
                "holder_id": holder_id,
                "updated_at": now_iso(),
                "external_proof": False,
            }
        remote_from_stage = self._shadow_stage.get(operation_id, "claimed")
        if remote_from_stage == "external_attempt_started":
            remote_from_stage = "claimed"
        result = self.client.invoke_module(
            "workflow-checkpoint",
            {
                "action": "transition",
                "namespace": self.namespace,
                "workflow_key": operation_id,
                "holder": holder_id,
                "expected_generation": generation,
                "from_stage": remote_from_stage,
                "to_stage": to_stage,
                "observation_key": f"observation_{uuid.uuid4().hex}",
                "evidence_type": evidence_type,
                "evidence_fingerprint": evidence_fingerprint,
            },
            idempotency_key=new_idempotency_key(),
        )
        self._shadow_stage[operation_id] = result["stage"]
        return self._portable(result, operation_id)

    @staticmethod
    def _portable(result: dict[str, Any], operation_id: str) -> dict[str, Any]:
        return {
            "contract_version": CONTRACT_VERSION,
            "operation_id": operation_id,
            "stage": result["stage"],
            "generation": result["generation"],
            "holder_id": None,
            "updated_at": now_iso(),
            "external_proof": False,
        }
