"""Rule profile CRUD routes (#18)."""

import re
import uuid
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from zerobox.api.dependencies import get_rules
from zerobox.rules.models import Rule, RuleProfile
from zerobox.rules.service import RuleService

router = APIRouter()


# ── Request bodies ─────────────────────────────────────────────────


class CreateProfileBody(BaseModel):
    name: str
    id: str | None = None
    description: str = ""


class AddRuleBody(BaseModel):
    patterns: list[str]
    target_name_template: str
    target_folder_template: str
    id: str | None = None
    priority: int = 0
    examples: list[str] = []


# ── ID generation ──────────────────────────────────────────────────


_SLUG_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _slugify(name: str) -> str:
    """Lowercase, non-alphanumeric → `-`, collapse dashes, strip.

    Returns `""` if the name has no alphanumeric characters at all — the
    caller is expected to handle that (falling back to a random id).
    """
    slug = _SLUG_NON_ALNUM.sub("-", name.lower()).strip("-")
    return slug


def _unique_profile_id(name: str, rules: RuleService) -> str:
    """Derive a unique profile id from `name`, appending `-2`, `-3`, … on collision."""
    base = _slugify(name) or uuid.uuid4().hex[:8]
    candidate = base
    suffix = 2
    while True:
        try:
            rules.get_profile(candidate)
        except FileNotFoundError:
            return candidate
        candidate = f"{base}-{suffix}"
        suffix += 1


def _unique_rule_id(profile: RuleProfile) -> str:
    """Generate a short random id that doesn't collide with existing rules in this profile."""
    taken = {r.id for r in (profile.rules or [])}
    while True:
        candidate = uuid.uuid4().hex[:8]
        if candidate not in taken:
            return candidate


# ── Helpers ────────────────────────────────────────────────────────


def _serialize_profile(profile: RuleProfile) -> dict:
    return asdict(profile)


# ── Routes ─────────────────────────────────────────────────────────


@router.get("/profiles")
def list_profiles(rules: RuleService = Depends(get_rules)) -> list[dict]:
    return [_serialize_profile(p) for p in rules.list_profiles()]


@router.get("/profiles/{profile_id}")
def get_profile(profile_id: str, rules: RuleService = Depends(get_rules)) -> dict:
    try:
        profile = rules.get_profile(profile_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile not found: {profile_id}")
    return _serialize_profile(profile)


@router.post("/profiles", status_code=201)
def create_profile(
    body: CreateProfileBody,
    rules: RuleService = Depends(get_rules),
) -> dict:
    if body.id is not None:
        profile_id = body.id
        try:
            rules.get_profile(profile_id)
        except FileNotFoundError:
            pass
        else:
            raise HTTPException(
                status_code=409, detail=f"Profile already exists: {profile_id}"
            )
    else:
        profile_id = _unique_profile_id(body.name, rules)

    profile = RuleProfile(
        id=profile_id, name=body.name, description=body.description
    )
    rules.save_profile(profile)
    return _serialize_profile(profile)


@router.delete("/profiles/{profile_id}")
def delete_profile(profile_id: str, rules: RuleService = Depends(get_rules)) -> dict:
    try:
        rules.delete_profile(profile_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile not found: {profile_id}")
    return {"status": "deleted"}


@router.post("/profiles/{profile_id}/rules", status_code=201)
def add_rule(
    profile_id: str,
    body: AddRuleBody,
    rules: RuleService = Depends(get_rules),
) -> dict:
    try:
        profile = rules.get_profile(profile_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile not found: {profile_id}")

    rule_id = body.id if body.id is not None else _unique_rule_id(profile)
    rule = Rule(
        id=rule_id,
        profile_id=profile_id,
        patterns=body.patterns,
        target_name_template=body.target_name_template,
        target_folder_template=body.target_folder_template,
        priority=body.priority,
        examples=body.examples,
    )
    rules.add_rule(profile_id, rule)
    profile = rules.get_profile(profile_id)
    return _serialize_profile(profile)


@router.delete("/profiles/{profile_id}/rules/{rule_id}")
def remove_rule(
    profile_id: str,
    rule_id: str,
    rules: RuleService = Depends(get_rules),
) -> dict:
    try:
        rules.remove_rule(profile_id, rule_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile not found: {profile_id}")
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Rule not found: {rule_id}")
    return {"status": "deleted"}
