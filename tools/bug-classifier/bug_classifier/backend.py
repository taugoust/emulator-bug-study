"""Classification backend interface and implementations."""

from __future__ import annotations
from dataclasses import dataclass
from re import sub


@dataclass
class ClassificationResult:
    """Result returned by a classification backend."""
    category: str
    labels: list[str]
    scores: list[float]
    reasoning: str | None = None


class ClassifierBackend:
    """Base class for classification backends."""

    def classify(self, text: str, categories: list[str], **kwargs) -> ClassificationResult:
        raise NotImplementedError


class ZeroShotBackend(ClassifierBackend):
    """HuggingFace zero-shot NLI classification."""

    def __init__(self, model: str, multi_label: bool,
                 positive: list[str], negative: list[str], architectures: list[str],
                 compare_model: str | None = None):
        from transformers import pipeline as _pipeline

        self.classifier = _pipeline("zero-shot-classification", model=model)
        self.multi_label = multi_label
        self.positive = positive
        self.negative = negative
        self.architectures = architectures
        self.compare_classifier = None
        if compare_model:
            self.compare_classifier = _pipeline("zero-shot-classification", model=compare_model)

    def classify(self, text: str, categories: list[str], **kwargs) -> ClassificationResult:
        from bug_classifier.main import get_category, compare_category

        result = self.classifier(text, categories, multi_label=self.multi_label)
        category = get_category(result, self.positive, self.negative, self.architectures, self.multi_label)

        if self.compare_classifier and sum(1 for c in self.positive if c in category) >= 1:
            compare_result = self.compare_classifier(text, categories, multi_label=self.multi_label)
            category = compare_category(compare_result, category, self.positive)

            result['labels'] = result['labels'] + ['SPLIT'] + compare_result['labels']
            result['scores'] = result['scores'] + [0] + compare_result['scores']

        return ClassificationResult(
            category=category,
            labels=result['labels'],
            scores=result['scores'],
        )


class OllamaBackend(ClassifierBackend):
    """Local LLM classification via Ollama."""

    def __init__(self, model: str, preamble: str):
        self.model = model
        self.preamble = preamble

    def classify(self, text: str, categories: list[str], **kwargs) -> ClassificationResult:
        from ollama import chat

        response = chat(self.model, [{'role': 'user', 'content': text + "\n" + self.preamble}])
        raw = response['message']['content']
        category = sub(r'[^a-zA-Z]', '', raw.split()[-1]).lower()
        if category not in categories:
            category = "manual-review"

        return ClassificationResult(
            category=category,
            labels=[],
            scores=[],
            reasoning=raw,
        )


class AnthropicBackend(ClassifierBackend):
    """Classification via the Anthropic Messages API."""

    def __init__(self, model: str, preamble: str, max_tokens: int = 1024):
        from anthropic import Anthropic

        self.client = Anthropic()  # uses ANTHROPIC_API_KEY env var
        self.model = model
        self.preamble = preamble
        self.max_tokens = max_tokens

    def classify(self, text: str, categories: list[str], **kwargs) -> ClassificationResult:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.preamble,
            messages=[{"role": "user", "content": text}],
        )
        raw = response.content[0].text
        category = sub(r'[^a-zA-Z]', '', raw.split()[-1]).lower()
        if category not in categories:
            category = "manual-review"

        return ClassificationResult(
            category=category,
            labels=[],
            scores=[],
            reasoning=raw,
        )
