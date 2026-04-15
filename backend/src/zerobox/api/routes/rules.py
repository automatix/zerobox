"""Rule profile CRUD routes (#18)."""

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from zerobox.api.dependencies import get_rules
from zerobox.rules.models import Rule, RuleProfile
from zerobox.rules.service import RuleService

router = APIRouter()


# ── Request bodies ─────────────────────────────────────────────────


class CreateProfileBody(BaseModel):
    id: str
    name: str
    description: str = ""


class AddRuleBody(BaseModel):
    id: str
    patterns: list[str]
    target_name_template: str
    target_folder_template: str
    priority: int = 0
    examples: list[str] = []


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
    try:
        rules.get_profile(body.id)
    except FileNotFoundError:
        pass
    else:
        raise HTTPException(status_code=409, detail=f"Profile already exists: {body.id}")

    profile = RuleProfile(id=body.id, name=body.name, description=body.description)
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
        rule = Rule(
            id=body.id,
            profile_id=profile_id,
            patterns=body.patterns,
            target_name_template=body.target_name_template,
            target_folder_template=body.target_folder_template,
            priority=body.priority,
            examples=body.examples,
        )
        rules.add_rule(profile_id, rule)
        profile = rules.get_profile(profile_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Profile not found: {profile_id}")
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
