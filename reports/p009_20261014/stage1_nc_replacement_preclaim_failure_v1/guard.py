"""CPU-only admission for a finite campaign; no dispatch, deletion, or cloud calls.

The backend must provide durable, atomic ``put(..., skip_if_exists=True)`` and
consistent reads (e.g. a new Modal Dict, not Volume lock files). All run slots
reserve their worst-case cost up front; reservations are never recycled. Thus
admission needs no unsafe read/modify/write budget counter. Dict's seven-day
inactivity expiry is bounded by the campaign's strictly shorter fixed lifetime.

A claim is permanent. A crash, lost RPC response, or ambiguous record NEVER
permits reacquiring that run. Reconciliation may authorize a distinct, already
budgeted child slot. An Admission must remain in its winning process: do not
persist it as permission for a restarted worker. The caller owns authentication,
real clocks, truthful cost bounds, checkpoint validation, and worker fencing.
Archive the immutable records separately before Dict retention expires; the
archive is evidence, never a replacement for the atomic admission backend.
This is fail-closed admission, not an exactly-once scientific execution engine.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol


DICT_TTL_SECONDS = 7 * 24 * 60 * 60
_ID = re.compile(r"[A-Za-z0-9_.-]{1,100}\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


class GuardError(RuntimeError):
    """No scientific work may follow a failed admission or active check."""


class AtomicStore(Protocol):
    def get(self, key: str, default: Any = None) -> Any: ...

    def put(self, key: str, value: Any, *, skip_if_exists: bool = False) -> bool: ...


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def identity_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _copy(value: Any) -> Any:
    return json.loads(canonical_json(value))


def _id(value: Any) -> None:
    if not isinstance(value, str) or not _ID.fullmatch(value):
        raise GuardError("invalid identifier")


def _hash(value: Any) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise GuardError("expected lowercase SHA-256")


def _money(value: Any) -> None:
    if type(value) is not int or value < 0:
        raise GuardError("cost must be nonnegative integer cents")


def _time(value: Any) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise GuardError("time must be finite epoch seconds")


@dataclass(frozen=True)
class Admission:
    campaign_id: str
    run_id: str
    attempt_id: str
    claim_sha256: str


class RunGuard:
    """Plan schema: campaign_id, created_epoch, deadline_epoch, total_cap_cents,
    stage_caps_cents={stage: cap}, slots={run_id: {stage, reserved_cents}}.

    Intent schema: run_id, config_sha256, source_sha256, data_sha256; optionally
    parent_run_id and reconciliation_sha256, both required for a recovery child.
    Source SHA-256 identifies a pinned source bundle/manifest, not a git SHA-1.
    """

    def __init__(self, store: AtomicStore, plan: Mapping[str, Any]):
        self.store = store
        self.plan = _copy(plan)
        p = self.plan
        required = {"campaign_id", "created_epoch", "deadline_epoch", "total_cap_cents",
                    "stage_caps_cents", "slots"}
        if set(p) != required:
            raise GuardError("unexpected campaign fields")
        _id(p["campaign_id"])
        for field in ("created_epoch", "deadline_epoch"):
            _time(p[field])
        if not 0 < p["deadline_epoch"] - p["created_epoch"] < DICT_TTL_SECONDS:
            raise GuardError("campaign lifetime must be strictly less than seven days")
        _money(p["total_cap_cents"])
        caps, slots = p["stage_caps_cents"], p["slots"]
        if not isinstance(caps, dict) or not caps or not isinstance(slots, dict) or not slots:
            raise GuardError("campaign needs stages and finite run slots")
        for stage, cap in caps.items():
            _id(stage)
            _money(cap)
        if sum(caps.values()) > p["total_cap_cents"]:
            raise GuardError("stage caps exceed total campaign budget")
        reserved = dict.fromkeys(caps, 0)
        for run_id, slot in slots.items():
            _id(run_id)
            if not isinstance(slot, dict) or set(slot) != {"stage", "reserved_cents"}:
                raise GuardError("invalid run slot")
            if slot["stage"] not in caps:
                raise GuardError("unknown stage")
            _money(slot["reserved_cents"])
            if slot["reserved_cents"] == 0:
                raise GuardError("run needs a positive conservative reservation")
            reserved[slot["stage"]] += slot["reserved_cents"]
        if any(reserved[s] > caps[s] for s in caps):
            raise GuardError("run reservations exceed a stage budget")
        self.plan_hash = identity_hash(p)
        self.prefix = "midpoint/" + p["campaign_id"] + "/"

    def _key(self, kind: str, run_id: str = "") -> str:
        return self.prefix + kind + ("/" + run_id if run_id else "")

    def _same_or_new(self, key: str, value: Any) -> None:
        if not self.store.put(key, _copy(value), skip_if_exists=True):
            if self.store.get(key) != value:
                raise GuardError("immutable record conflict: " + key)

    def _clock(self, now_epoch: float) -> None:
        _time(now_epoch)
        if not self.plan["created_epoch"] <= now_epoch < self.plan["deadline_epoch"]:
            raise GuardError("campaign not started or absolute deadline expired")

    def _registered(self) -> None:
        if identity_hash(self.plan) != self.plan_hash:
            raise GuardError("in-memory plan was changed")
        if self.store.get(self._key("campaign")) != self.plan:
            raise GuardError("campaign is absent or differs; no automatic recreation")

    def register(self, *, now_epoch: float) -> None:
        """Persist the fixed envelope before jobs are scheduled; no reservations released."""
        self._clock(now_epoch)
        if identity_hash(self.plan) != self.plan_hash:
            raise GuardError("in-memory plan was changed")
        self._same_or_new(self._key("campaign"), self.plan)

    def _slot(self, run_id: str) -> dict[str, Any]:
        _id(run_id)
        if run_id not in self.plan["slots"]:
            raise GuardError("run is not a pre-reserved slot")
        return self.plan["slots"][run_id]

    def record_reconciliation(self, receipt: Mapping[str, Any]) -> str:
        """Store explicit operator evidence; this does not stop workers or approve dose.

        Required fields bind one failed/interrupted parent to one child config.
        Both boolean attestations must be True. Evidence/remaining-work hashes
        must identify separately retained reviewed records, not just this receipt.
        """
        self._registered()
        r = _copy(receipt)
        expected = {"parent_run_id", "child_run_id", "child_config_sha256",
                    "evidence_sha256", "remaining_work_sha256", "workers_stopped",
                    "no_ambiguous_replay"}
        if set(r) != expected:
            raise GuardError("invalid reconciliation fields")
        self._slot(r["parent_run_id"])
        self._slot(r["child_run_id"])
        if r["parent_run_id"] == r["child_run_id"]:
            raise GuardError("a recovery child must have a new run id")
        for field in ("child_config_sha256", "evidence_sha256", "remaining_work_sha256"):
            _hash(r[field])
        if r["workers_stopped"] is not True or r["no_ambiguous_replay"] is not True:
            raise GuardError("reconciliation must attest stopped workers and no ambiguous replay")
        if self.store.get(self._key("claim", r["parent_run_id"])) is None:
            raise GuardError("parent has no claim to reconcile")
        terminal = self.store.get(self._key("terminal", r["parent_run_id"]))
        if terminal and terminal["status"] == "completed":
            raise GuardError("completed parent cannot be replayed as recovery")
        key = self._key("reconciliation", r["child_run_id"])
        self._same_or_new(key, r)
        return identity_hash(r)

    def admit(self, intent: Mapping[str, Any], *, attempt_id: str,
              now_epoch: float, max_runtime_seconds: float) -> Admission:
        self._registered()
        self._clock(now_epoch)
        _id(attempt_id)
        _time(max_runtime_seconds)
        if max_runtime_seconds <= 0 or now_epoch + max_runtime_seconds > self.plan["deadline_epoch"]:
            raise GuardError("runtime exceeds remaining absolute window")
        i = _copy(intent)
        base = {"run_id", "config_sha256", "source_sha256", "data_sha256"}
        recovery = {"parent_run_id", "reconciliation_sha256"}
        if set(i) not in (base, base | recovery):
            raise GuardError("invalid intent fields")
        slot = self._slot(i["run_id"])
        if self.store.get(self._key("terminal", i["run_id"])) is not None:
            raise GuardError("run is already terminal; missing claims cannot authorize replay")
        for field in ("config_sha256", "source_sha256", "data_sha256"):
            _hash(i[field])
        if recovery <= set(i):
            _hash(i["reconciliation_sha256"])
            r = self.store.get(self._key("reconciliation", i["run_id"]))
            if (not r or identity_hash(r) != i["reconciliation_sha256"]
                    or r["parent_run_id"] != i["parent_run_id"]
                    or r["child_config_sha256"] != i["config_sha256"]):
                raise GuardError("recovery has no matching explicit reconciliation")
            parent_terminal = self.store.get(self._key("terminal", i["parent_run_id"]))
            if parent_terminal and parent_terminal["status"] == "completed":
                raise GuardError("completed parent cannot be replayed as recovery")
        elif self.store.get(self._key("reconciliation", i["run_id"])) is not None:
            raise GuardError("reconciled child must retain its parent linkage")
        for run_id, run_slot in self.plan["slots"].items():
            t = self.store.get(self._key("terminal", run_id))
            if t and t["actual_cost_cents"] is not None and t["actual_cost_cents"] > run_slot["reserved_cents"]:
                raise GuardError("prior reservation overrun: reconcile campaign before new work")
        # The intent may exist without a claim after a pre-admission crash. No
        # scientific work is allowed before the winning claim and attempt persist.
        self._same_or_new(self._key("intent", i["run_id"]), i)
        claim = {"intent_sha256": identity_hash(i), "plan_sha256": self.plan_hash,
                 "run_id": i["run_id"], "attempt_id": attempt_id, "stage": slot["stage"],
                 "reserved_cents": slot["reserved_cents"], "claimed_epoch": now_epoch,
                 "deadline_epoch": now_epoch + max_runtime_seconds}
        if not self.store.put(self._key("claim", i["run_id"]), claim, skip_if_exists=True):
            raise GuardError("run already claimed; completed, failed, or ambiguous work cannot replay")
        self._same_or_new(self._key("attempt", i["run_id"] + "/" + attempt_id), claim)
        return Admission(self.plan["campaign_id"], i["run_id"], attempt_id, identity_hash(claim))

    def _owned(self, admission: Admission) -> dict[str, Any]:
        self._registered()
        if admission.campaign_id != self.plan["campaign_id"]:
            raise GuardError("admission belongs to another campaign")
        self._slot(admission.run_id)
        _id(admission.attempt_id)
        claim = self.store.get(self._key("claim", admission.run_id))
        attempt = self.store.get(self._key("attempt", admission.run_id + "/" + admission.attempt_id))
        if (claim is None or identity_hash(claim) != admission.claim_sha256
                or claim["attempt_id"] != admission.attempt_id or attempt != claim):
            raise GuardError("missing or conflicting ownership evidence")
        return claim

    def check_active(self, admission: Admission, *, now_epoch: float,
                     spent_cents: int, next_cost_cents: int = 0) -> None:
        """Caller checks before work units; this function does not monitor or kill them."""
        claim = self._owned(admission)
        self._clock(now_epoch)
        if now_epoch < claim["claimed_epoch"] or now_epoch >= claim["deadline_epoch"]:
            raise GuardError("run absolute deadline expired or clock moved backwards")
        if self.store.get(self._key("terminal", admission.run_id)) is not None:
            raise GuardError("run is terminal")
        for run_id in self.plan["slots"]:
            r = self.store.get(self._key("reconciliation", run_id))
            if r and r["parent_run_id"] == admission.run_id:
                raise GuardError("parent was reconciled; its original admission is fenced")
        _money(spent_cents)
        _money(next_cost_cents)
        if spent_cents + next_cost_cents > claim["reserved_cents"]:
            raise GuardError("next work would exceed conservative reservation")

    def finish(self, admission: Admission, *, status: str, evidence_sha256: str,
               actual_cost_cents: int | None, finished_epoch: float) -> dict[str, Any]:
        """Append a terminal receipt even after deadlines/overruns; never release claim.

        Repeating exactly the same receipt is idempotent. A negative scientific
        result is still 'completed'; 'failed' records engineering failure.
        Unknown costs are permitted only for 'ambiguous'. Costs are caller-supplied
        conservative accounting, not a claim of provider invoice verification.
        """
        claim = self._owned(admission)
        _time(finished_epoch)
        if finished_epoch < claim["claimed_epoch"]:
            raise GuardError("receipt predates admission")
        if status not in {"completed", "failed", "ambiguous"}:
            raise GuardError("invalid terminal status")
        _hash(evidence_sha256)
        if actual_cost_cents is None:
            if status != "ambiguous":
                raise GuardError("unknown cost requires ambiguous status")
        else:
            _money(actual_cost_cents)
        receipt = {"run_id": admission.run_id, "attempt_id": admission.attempt_id,
                   "claim_sha256": admission.claim_sha256, "status": status,
                   "evidence_sha256": evidence_sha256, "actual_cost_cents": actual_cost_cents,
                   "finished_epoch": finished_epoch}
        self._same_or_new(self._key("terminal", admission.run_id), receipt)
        return receipt
