import pytest
import sys
from unittest.mock import patch, MagicMock
from bug_classifier.backend import (
    ClassifierBackend,
    ClassificationResult,
    OllamaBackend,
)


POSITIVE = ['semantic', 'TCG', 'assembly', 'architecture', 'mistranslation', 'register', 'user-level']
NEGATIVE = ['boot', 'network', 'kvm', 'vnc', 'graphic', 'device', 'socket', 'debug', 'files', 'PID', 'permissions', 'performance', 'kernel', 'peripherals', 'VMM', 'hypervisor', 'virtual', 'other']
ARCHITECTURES = ['x86', 'arm', 'risc-v', 'i386', 'ppc']
CATEGORIES = POSITIVE + NEGATIVE + ARCHITECTURES


class TestClassificationResult:
    def test_defaults(self):
        r = ClassificationResult(category="network", labels=["network"], scores=[0.9])
        assert r.category == "network"
        assert r.reasoning is None

    def test_with_reasoning(self):
        r = ClassificationResult(category="boot", labels=[], scores=[], reasoning="because")
        assert r.reasoning == "because"


class TestClassifierBackend:
    def test_base_raises(self):
        backend = ClassifierBackend()
        with pytest.raises(NotImplementedError):
            backend.classify("text", ["a", "b"])


class TestZeroShotBackend:
    def _make_backend(self, primary_result, multi_label=False, compare_result=None):
        """Create a ZeroShotBackend with mocked transformers.pipeline."""
        primary_pipe = MagicMock(return_value=primary_result)
        compare_pipe = MagicMock(return_value=compare_result) if compare_result else None

        pipes = iter([primary_pipe] + ([compare_pipe] if compare_pipe else []))
        mock_pipeline = MagicMock(side_effect=lambda *a, **kw: next(pipes))

        # Inject a fake transformers module so the import inside __init__ works
        fake_transformers = MagicMock()
        fake_transformers.pipeline = mock_pipeline
        with patch.dict(sys.modules, {"transformers": fake_transformers}):
            from bug_classifier.backend import ZeroShotBackend
            backend = ZeroShotBackend(
                model="test-model",
                multi_label=multi_label,
                positive=POSITIVE,
                negative=NEGATIVE,
                architectures=ARCHITECTURES,
                compare_model="compare-model" if compare_result else None,
            )

        return backend

    def test_single_label_returns_highest(self):
        backend = self._make_backend({
            'labels': ['network', 'boot', 'kvm'],
            'scores': [0.95, 0.5, 0.3],
        })

        result = backend.classify("some bug text", CATEGORIES)
        assert result.category == 'network'
        assert result.labels == ['network', 'boot', 'kvm']
        assert result.scores == [0.95, 0.5, 0.3]
        assert result.reasoning is None

    def test_multi_label_positive_with_arch(self):
        backend = self._make_backend(
            {'labels': ['mistranslation', 'x86', 'boot'], 'scores': [0.9, 0.85, 0.3]},
            multi_label=True,
        )

        result = backend.classify("some bug text", CATEGORIES)
        assert result.category == 'mistranslation-x86'

    def test_multi_label_all_low_returns_none(self):
        backend = self._make_backend(
            {'labels': ['network', 'boot'], 'scores': [0.7, 0.6]},
            multi_label=True,
        )

        result = backend.classify("some bug text", CATEGORIES)
        assert result.category == 'none'

    def test_compare_model_keeps_positive(self):
        backend = self._make_backend(
            {'labels': ['semantic', 'boot', 'network'], 'scores': [0.9, 0.5, 0.3]},
            compare_result={'labels': ['semantic', 'boot'], 'scores': [0.9, 0.5]},
        )

        result = backend.classify("some bug text", CATEGORIES)
        assert result.category == 'semantic'
        assert 'SPLIT' in result.labels

    def test_compare_model_returns_review(self):
        backend = self._make_backend(
            {'labels': ['semantic', 'boot', 'network'], 'scores': [0.9, 0.5, 0.3]},
            compare_result={'labels': ['boot', 'network'], 'scores': [0.5, 0.3]},
        )

        result = backend.classify("some bug text", CATEGORIES)
        assert result.category == 'review'


class TestOllamaBackend:
    def _mock_chat(self, content):
        """Patch ollama.chat to return a canned response."""
        fake_ollama = MagicMock()
        fake_ollama.chat.return_value = {'message': {'content': content}}
        return patch.dict(sys.modules, {"ollama": fake_ollama}), fake_ollama.chat

    def test_valid_category(self):
        ctx, mock_chat = self._mock_chat('The category is network')
        with ctx:
            from bug_classifier.backend import OllamaBackend as OB
            backend = OB(model="test-model", preamble="classify this")
            result = backend.classify("some bug", CATEGORIES)

        assert result.category == 'network'
        assert result.labels == []
        assert result.scores == []
        assert result.reasoning == 'The category is network'

    def test_unknown_category_falls_back(self):
        ctx, _ = self._mock_chat('I think this is a banana')
        with ctx:
            from bug_classifier.backend import OllamaBackend as OB
            backend = OB(model="test-model", preamble="classify this")
            result = backend.classify("some bug", CATEGORIES)

        assert result.category == 'manual-review'

    def test_strips_non_alpha(self):
        ctx, _ = self._mock_chat('Result: **boot**!')
        with ctx:
            from bug_classifier.backend import OllamaBackend as OB
            backend = OB(model="test-model", preamble="classify this")
            result = backend.classify("some bug", CATEGORIES)

        assert result.category == 'boot'

    def test_preamble_appended_to_text(self):
        ctx, mock_chat = self._mock_chat('network')
        with ctx:
            from bug_classifier.backend import OllamaBackend as OB
            backend = OB(model="test-model", preamble="MY PREAMBLE")
            backend.classify("bug text", CATEGORIES)

        content = mock_chat.call_args[0][1][0]['content']
        assert "bug text" in content
        assert "MY PREAMBLE" in content
