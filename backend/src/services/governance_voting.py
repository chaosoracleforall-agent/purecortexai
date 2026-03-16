"""Helpers for signed governance votes and delegated tally computation."""

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from typing import Any

from algosdk.encoding import is_valid_address
from algosdk.util import verify_bytes


SIGNED_VOTE_CONTEXT = "PURECORTEX_GOVERNANCE_VOTE_V1"
SIGNED_VOTE_MAX_AGE = timedelta(minutes=10)
SIGNED_VOTE_MAX_FUTURE_SKEW = timedelta(minutes=1)


def build_signed_vote_message(
    *,
    proposal_id: int,
    voter: str,
    vote: str,
    issued_at: str,
    nonce: str,
) -> str:
    return "\n".join(
        [
            SIGNED_VOTE_CONTEXT,
            f"proposal_id:{proposal_id}",
            f"vote:{vote}",
            f"voter:{voter}",
            f"issued_at:{issued_at}",
            f"nonce:{nonce}",
        ]
    )


def verify_signed_vote(
    *,
    proposal_id: int,
    voter: str,
    vote: str,
    issued_at: str,
    nonce: str,
    signature_b64: str,
) -> None:
    if vote not in {"for", "against"}:
        raise ValueError("Vote must be 'for' or 'against'.")
    if not is_valid_address(voter):
        raise ValueError("Invalid voter address.")

    try:
        issued = datetime.fromisoformat(issued_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid vote timestamp.") from exc
    if issued.tzinfo is None:
        issued = issued.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    if issued - now > SIGNED_VOTE_MAX_FUTURE_SKEW:
        raise ValueError("Vote timestamp is too far in the future.")
    if now - issued > SIGNED_VOTE_MAX_AGE:
        raise ValueError("Vote signature expired.")

    try:
        base64.b64decode(signature_b64, validate=True)
    except Exception as exc:
        raise ValueError("Invalid vote signature encoding.") from exc

    message = build_signed_vote_message(
        proposal_id=proposal_id,
        voter=voter,
        vote=vote,
        issued_at=issued_at,
        nonce=nonce,
    ).encode("utf-8")
    if not verify_bytes(message, signature_b64, voter):
        raise ValueError("Vote signature verification failed.")


def normalize_proposal(proposal: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(proposal)
    normalized.setdefault("legacy_votes_for", int(normalized.get("votes_for", 0)))
    normalized.setdefault("legacy_votes_against", int(normalized.get("votes_against", 0)))
    normalized.setdefault("legacy_voter_count", len(normalized.get("voters", [])))
    normalized.setdefault("legacy_voters", list(normalized.get("voters", [])))

    vote_records = normalized.get("vote_records") or {}
    normalized["vote_records"] = vote_records if isinstance(vote_records, dict) else {}
    return normalized


def _iter_vote_records(proposal: dict[str, Any]) -> dict[str, dict[str, Any]]:
    records = normalize_proposal(proposal)["vote_records"]
    cleaned: dict[str, dict[str, Any]] = {}
    for actor, record in records.items():
        if not isinstance(record, dict):
            continue
        vote = record.get("vote")
        if vote not in {"for", "against"}:
            continue
        cleaned[actor] = {
            "vote": vote,
            "source": record.get("source") or "unknown",
            "recorded_at": record.get("recorded_at"),
            "weight_override": record.get("weight_override"),
        }
    return cleaned


def calculate_voter_power(
    voter: str,
    *,
    proposal: dict[str, Any],
    stake_snapshots: list[dict[str, Any]],
) -> dict[str, int]:
    records = _iter_vote_records(proposal)
    direct_voter_addresses = {address for address in records}
    own_snapshot = next((snapshot for snapshot in stake_snapshots if snapshot["address"] == voter), None)
    direct_weight = int(own_snapshot.get("ve_power", 0)) if own_snapshot else 0
    delegated_weight = sum(
        int(snapshot.get("ve_power", 0))
        for snapshot in stake_snapshots
        if snapshot.get("delegate") == voter and snapshot["address"] not in direct_voter_addresses
    )

    if own_snapshot and voter in records and records[voter].get("weight_override") is not None:
        direct_weight = int(records[voter]["weight_override"])

    return {
        "direct_weight": direct_weight,
        "delegated_weight": delegated_weight,
        "effective_weight": direct_weight + delegated_weight,
    }


def calculate_live_tally(
    proposal: dict[str, Any],
    *,
    stake_snapshots: list[dict[str, Any]],
) -> dict[str, Any]:
    normalized = normalize_proposal(proposal)
    records = _iter_vote_records(normalized)
    by_address = {snapshot["address"]: snapshot for snapshot in stake_snapshots}

    votes_for = int(normalized["legacy_votes_for"])
    votes_against = int(normalized["legacy_votes_against"])
    voter_count = int(normalized["legacy_voter_count"])

    counted_stakers: set[str] = set()
    manual_extra_voters: set[str] = set()

    for snapshot in stake_snapshots:
        address = snapshot["address"]
        record = records.get(address)
        if record is None and snapshot.get("delegate"):
            record = records.get(snapshot["delegate"])
        if record is None:
            continue

        weight = int(snapshot.get("ve_power", 0))
        if records.get(address) and records[address].get("weight_override") is not None:
            weight = int(records[address]["weight_override"])
        if weight <= 0:
            continue

        if record["vote"] == "for":
            votes_for += weight
        else:
            votes_against += weight
        counted_stakers.add(address)

    for actor, record in records.items():
        if actor in by_address:
            continue
        if record.get("weight_override") is None:
            continue
        weight = int(record["weight_override"])
        if weight <= 0:
            continue
        if record["vote"] == "for":
            votes_for += weight
        else:
            votes_against += weight
        manual_extra_voters.add(actor)

    voter_count += len(counted_stakers) + len(manual_extra_voters)
    visible_voters = sorted(set(normalized.get("legacy_voters", [])) | set(records.keys()))

    normalized["votes_for"] = votes_for
    normalized["votes_against"] = votes_against
    normalized["voter_count"] = voter_count
    normalized["voters"] = visible_voters
    normalized["vote_records"] = records
    return normalized
