"""Abstract LLM provider interface (FR-08)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from zerobox.classifier.models import ClassificationContext, ClassificationResult, UserCorrection
    from zerobox.rules.models import Rule


class LLMProvider(ABC):
    """Base class for all LLM providers.

    Concrete implementations must handle prompt construction, API calls,
    and response parsing for their respective LLM service.
    """

    @abstractmethod
    async def classify(
        self,
        text: str,
        rules: list[Rule],
        context: ClassificationContext,
    ) -> ClassificationResult:
        """Classify extracted text and propose a name and folder.

        Args:
            text: OCR-extracted text from the scanned document.
            rules: Active rules from the current profile.
            context: Metadata about the original file.

        Returns:
            A classification result with proposed name, folder, and confidence.
        """

    @abstractmethod
    async def extract_rule(
        self,
        text: str,
        correction: UserCorrection,
    ) -> Rule:
        """Derive a new rule from a user correction.

        Args:
            text: OCR-extracted text from the scanned document.
            correction: The user's correction to the original proposal.

        Returns:
            A new rule that captures the correction pattern.
        """
