"""Classification backend interface and implementations."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from re import compile as re_compile, sub, DOTALL
from typing import IO

_THINK_RE = re_compile(r'<think>.*?</think>', flags=DOTALL)


def parse_category(raw: str, categories: list[str]) -> str:
    """Extract the first valid category word from a model response.

    Strips <think>…</think> blocks first (DeepSeek-R1 / reasoning models),
    then returns the first word that matches a known category.  Falls back to
    'manual-review' if no match is found.
    """
    text = _THINK_RE.sub('', raw)
    for word in text.split():
        candidate = sub(r'[^a-zA-Z-]', '', word).lower()
        if candidate in categories:
            return candidate
    return "manual-review"


@dataclass
class ClassificationResult:
    """Result returned by a classification backend."""
    category: str
    labels: list[str]
    scores: list[float]
    reasoning: str | None = None


class ClassifierBackend:
    """Base class for classification backends."""

    def classify(self, text: str, categories: list[str], **kwargs: object) -> ClassificationResult:
        raise NotImplementedError


class ZeroShotBackend(ClassifierBackend):
    """HuggingFace zero-shot NLI classification."""

    def __init__(self, model: str, multi_label: bool,
                 positive: list[str], negative: list[str], architectures: list[str],
                 compare_model: str | None = None) -> None:
        from transformers import pipeline as _pipeline

        self.classifier = _pipeline("zero-shot-classification", model=model)
        self.multi_label = multi_label
        self.positive = positive
        self.negative = negative
        self.architectures = architectures
        self.compare_classifier = None
        if compare_model:
            self.compare_classifier = _pipeline("zero-shot-classification", model=compare_model)

    def classify(self, text: str, categories: list[str], **kwargs: object) -> ClassificationResult:
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

    def __init__(self, model: str, preamble: str) -> None:
        self.model = model
        self.preamble = preamble

    def classify(self, text: str, categories: list[str], **kwargs: object) -> ClassificationResult:
        from ollama import chat

        response = chat(self.model, [{'role': 'user', 'content': text + "\n" + self.preamble}])
        raw = response['message']['content']
        category = parse_category(raw, categories)

        return ClassificationResult(
            category=category,
            labels=[],
            scores=[],
            reasoning=raw,
        )


class AnthropicBackend(ClassifierBackend):
    """Classification via the Anthropic Messages API."""

    def __init__(self, model: str, preamble: str, max_tokens: int = 1024) -> None:
        from anthropic import Anthropic

        self.client = Anthropic()  # uses ANTHROPIC_API_KEY env var
        self.model = model
        self.preamble = preamble
        self.max_tokens = max_tokens

    def classify(self, text: str, categories: list[str], **kwargs: object) -> ClassificationResult:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=self.preamble,
            messages=[{"role": "user", "content": text}],
        )
        raw = next(
            (t for b in response.content if isinstance(t := getattr(b, "text", None), str)),
            "",
        )
        category = parse_category(raw, categories)

        return ClassificationResult(
            category=category,
            labels=[],
            scores=[],
            reasoning=raw,
        )


class PiBackend(ClassifierBackend):
    """Classification via pi coding agent in RPC mode."""

    _stdin: IO[str]
    _stdout: IO[str]

    def __init__(self, model: str, preamble: str) -> None:
        import shutil

        pi_bin = shutil.which("pi")
        if pi_bin is None:
            raise RuntimeError(
                "pi binary not found on PATH. "
                "Run via `nix run .#bug-classifier-full` or enter `nix develop .#full`."
            )

        self.proc = subprocess.Popen(
            [
                pi_bin,
                "--mode", "rpc",
                "--no-session",
                "--no-tools",
                "--no-extensions",
                "--no-skills",
                "--thinking", "off",
                "--model", model,
                "--system-prompt", preamble,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
        )
        assert self.proc.stdin is not None
        assert self.proc.stdout is not None
        self._stdin = self.proc.stdin
        self._stdout = self.proc.stdout

    def classify(self, text: str, categories: list[str], **kwargs: object) -> ClassificationResult:
        import json

        # Send the prompt
        self._stdin.write(json.dumps({"type": "prompt", "message": text}) + "\n")
        self._stdin.flush()

        # Read until agent_end event
        raw = ""
        for line in self._stdout:
            line = line.rstrip("\n")
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "agent_end":
                # Extract the last assistant text content
                for msg in reversed(event.get("messages", [])):
                    if msg.get("role") == "assistant":
                        for block in reversed(msg.get("content", [])):
                            if isinstance(block, dict) and block.get("type") == "text":
                                raw = block["text"]
                                break
                            elif isinstance(block, str):
                                raw = block
                                break
                        if raw:
                            break
                break

        # Parse category
        category = parse_category(raw, categories)

        # Reset session context for the next bug
        self._stdin.write(json.dumps({"type": "new_session"}) + "\n")
        self._stdin.flush()

        # Drain until new_session response
        for line in self._stdout:
            line = line.rstrip("\n")
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "response" and event.get("command") == "new_session":
                break

        return ClassificationResult(
            category=category,
            labels=[],
            scores=[],
            reasoning=raw,
        )

    def close(self) -> None:
        """Terminate the pi subprocess."""
        if hasattr(self, 'proc') and self.proc.poll() is None:
            self._stdin.close()
            self.proc.terminate()
            self.proc.wait(timeout=5)

    def __del__(self) -> None:
        self.close()
