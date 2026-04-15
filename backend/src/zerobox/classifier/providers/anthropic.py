"""Anthropic (Claude) LLM provider implementation (T-08)."""

from __future__ import annotations

import json
import os
import re
import uuid
from typing import TYPE_CHECKING

import anthropic

from zerobox.classifier.providers import register
from zerobox.classifier.providers.base import LLMProvider

if TYPE_CHECKING:
    from zerobox.classifier.models import ClassificationContext, ClassificationResult, UserCorrection
    from zerobox.config import LLMConfig
    from zerobox.rules.models import Rule

_SYSTEM_PROMPT = (
    "You are Zerobox, an AI assistant that classifies scanned documents. "
    "You analyze OCR-extracted text and propose a file name and folder. "
    "Always respond with a single JSON object — no markdown fences, no commentary."
)

_CLASSIFY_TEMPLATE = """\
Classify the following scanned document.

## OCR Text
{text}

## File Metadata
- Original path: {original_path}
- Original name: {original_name}
- File type: {file_type}

## Active Rules
{rules_block}

Return a JSON object with exactly these keys:
- "proposed_name": a descriptive file name (without extension)
- "proposed_folder": the target folder path
- "confidence": a float between 0.0 and 1.0
- "matched_rule_id": the ID of the matched rule, or null if none matched
- "reasoning": a brief explanation of the classification decision
"""

_EXTRACT_RULE_TEMPLATE = """\
A user corrected a classification. Derive a reusable rule from the correction.

## OCR Text
{text}

## Original Proposal
- Name: {original_name}
- Folder: {original_folder}

## User Correction
- Corrected name: {corrected_name}
- Corrected folder: {corrected_folder}

Return a JSON object with exactly these keys:
- "patterns": a list of text patterns (strings) that identify this document type
- "target_name_template": a name template, e.g. "{{date}}_{{type}}_{{sender}}"
- "target_folder_template": the target folder path
- "priority": an integer priority (higher = checked first), default 0
- "examples": a list of example texts that match this rule
"""


def _format_rules(rules: list[Rule]) -> str:
    if not rules:
        return "(no active rules)"
    lines: list[str] = []
    for r in rules:
        lines.append(
            f"- Rule {r.id}: patterns={r.patterns}, "
            f"name_template={r.target_name_template!r}, "
            f"folder_template={r.target_folder_template!r}, "
            f"priority={r.priority}"
        )
    return "\n".join(lines)


def _extract_json(text: str) -> dict:
    """Extract a JSON object from the response text.

    Handles both raw JSON and JSON wrapped in markdown code fences.
    """
    # Try to extract from code fences first
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1)
    return json.loads(text)


@register("anthropic")
class AnthropicProvider(LLMProvider):
    """Claude-based LLM provider using the Anthropic SDK."""

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def classify(
        self,
        text: str,
        rules: list[Rule],
        context: ClassificationContext,
    ) -> ClassificationResult:
        from zerobox.classifier.models import ClassificationResult

        prompt = _CLASSIFY_TEMPLATE.format(
            text=text,
            original_path=context.original_path,
            original_name=context.original_name,
            file_type=context.file_type,
            rules_block=_format_rules(rules),
        )

        response = await self._client.messages.create(
            model=self.config.model,
            max_tokens=1024,
            temperature=self.config.temperature,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text
        data = _extract_json(raw)

        return ClassificationResult(
            proposed_name=data["proposed_name"],
            proposed_folder=data["proposed_folder"],
            confidence=float(data["confidence"]),
            matched_rule_id=data.get("matched_rule_id"),
            reasoning=data.get("reasoning", ""),
        )

    async def extract_rule(
        self,
        text: str,
        correction: UserCorrection,
    ) -> Rule:
        from zerobox.rules.models import Rule

        prompt = _EXTRACT_RULE_TEMPLATE.format(
            text=text,
            original_name=correction.original_proposal_name,
            original_folder=correction.original_proposal_folder,
            corrected_name=correction.corrected_name,
            corrected_folder=correction.corrected_folder,
        )

        response = await self._client.messages.create(
            model=self.config.model,
            max_tokens=1024,
            temperature=self.config.temperature,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = response.content[0].text
        data = _extract_json(raw)

        return Rule(
            id=uuid.uuid4().hex[:8],
            profile_id="",
            patterns=data["patterns"],
            target_name_template=data["target_name_template"],
            target_folder_template=data["target_folder_template"],
            priority=data.get("priority", 0),
            examples=data.get("examples", []),
        )
