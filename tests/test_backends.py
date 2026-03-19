import json
import pytest
import sys
from unittest.mock import patch, MagicMock
from bug_classifier.backend import (
    ClassifierBackend,
    ClassificationResult,
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
    def _make_backend(self, primary_result: object, multi_label: bool = False, compare_result: object = None):
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
    def _mock_chat(self, content: str):
        """Patch ollama.chat to return a canned response."""
        fake_ollama = MagicMock()
        fake_ollama.chat.return_value = {'message': {'content': content}}
        return patch.dict(sys.modules, {"ollama": fake_ollama}), fake_ollama.chat

    def test_valid_category(self):
        ctx, _ = self._mock_chat('The category is network')
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


class TestAnthropicBackend:
    def _make_backend(self, response_text: str):
        """Create an AnthropicBackend with a mocked Anthropic client."""
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text=response_text)]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_message

        fake_anthropic = MagicMock()
        fake_anthropic.Anthropic.return_value = mock_client

        ctx = patch.dict(sys.modules, {"anthropic": fake_anthropic})
        ctx.start()
        from bug_classifier.backend import AnthropicBackend
        backend = AnthropicBackend(model="claude-test", preamble="classify this")
        ctx.stop()

        return backend, mock_client

    def test_valid_category(self):
        backend, _ = self._make_backend('The category is network')
        result = backend.classify("some bug", CATEGORIES)

        assert result.category == 'network'
        assert result.labels == []
        assert result.scores == []
        assert result.reasoning == 'The category is network'

    def test_unknown_category_falls_back(self):
        backend, _ = self._make_backend('I think this is a banana')
        result = backend.classify("some bug", CATEGORIES)

        assert result.category == 'manual-review'

    def test_strips_non_alpha(self):
        backend, _ = self._make_backend('Result: **boot**!')
        result = backend.classify("some bug", CATEGORIES)

        assert result.category == 'boot'

    def test_preamble_sent_as_system(self):
        backend, mock_client = self._make_backend('network')
        backend.classify("bug text", CATEGORIES)

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs['system'] == 'classify this'
        assert call_kwargs['messages'][0]['content'] == 'bug text'
        assert call_kwargs['messages'][0]['role'] == 'user'

    def test_model_passed_through(self):
        backend, mock_client = self._make_backend('network')
        backend.classify("bug text", CATEGORIES)

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs['model'] == 'claude-test'


class TestPiBackend:
    """Tests for PiBackend using a mocked subprocess."""

    def _make_agent_end(self, text: str):
        """Build an agent_end JSON line with the given assistant text."""
        return json.dumps({
            "type": "agent_end",
            "messages": [
                {
                    "role": "assistant",
                    "content": [{"type": "text", "text": text}],
                }
            ],
        })

    NEW_SESSION_RESPONSE = json.dumps({"type": "response", "command": "new_session"})

    def _make_backend(self, stdout_lines: list[str]):
        """Create a PiBackend with mocked subprocess.Popen and shutil.which."""
        mock_proc = MagicMock()
        mock_proc.stdin = MagicMock()
        # stdout is iterated line-by-line; simulate with a list iterator
        mock_proc.stdout = iter(line + "\n" for line in stdout_lines)
        mock_proc.poll.return_value = None

        mock_popen = MagicMock(return_value=mock_proc)

        with patch("shutil.which", return_value="/usr/bin/pi"), \
             patch("subprocess.Popen", mock_popen):
            from bug_classifier.backend import PiBackend
            backend = PiBackend(model="test-model", preamble="classify this")

        return backend, mock_proc, mock_popen

    def test_valid_category(self):
        lines = [
            self._make_agent_end("The category is network"),
            self.NEW_SESSION_RESPONSE,
        ]
        backend, _, _ = self._make_backend(lines)
        result = backend.classify("some bug", CATEGORIES)

        assert result.category == "network"
        assert result.labels == []
        assert result.scores == []
        assert result.reasoning == "The category is network"

    def test_unknown_category_falls_back(self):
        lines = [
            self._make_agent_end("I think this is a banana"),
            self.NEW_SESSION_RESPONSE,
        ]
        backend, _, _ = self._make_backend(lines)
        result = backend.classify("some bug", CATEGORIES)

        assert result.category == "manual-review"

    def test_strips_non_alpha(self):
        lines = [
            self._make_agent_end("Result: **boot**!"),
            self.NEW_SESSION_RESPONSE,
        ]
        backend, _, _ = self._make_backend(lines)
        result = backend.classify("some bug", CATEGORIES)

        assert result.category == "boot"

    def test_empty_response_falls_back(self):
        lines = [
            self._make_agent_end(""),
            self.NEW_SESSION_RESPONSE,
        ]
        backend, _, _ = self._make_backend(lines)
        result = backend.classify("some bug", CATEGORIES)

        assert result.category == "manual-review"

    def test_non_json_lines_are_skipped(self):
        lines = [
            "some debug log output",
            "not valid json at all",
            self._make_agent_end("network"),
            self.NEW_SESSION_RESPONSE,
        ]
        backend, _, _ = self._make_backend(lines)
        result = backend.classify("some bug", CATEGORIES)

        assert result.category == "network"

    def test_sends_prompt_and_new_session(self):
        lines = [
            self._make_agent_end("network"),
            self.NEW_SESSION_RESPONSE,
        ]
        backend, mock_proc, _ = self._make_backend(lines)
        backend.classify("bug text", CATEGORIES)

        writes = [call.args[0] for call in mock_proc.stdin.write.call_args_list]
        prompt_msg = json.loads(writes[0])
        assert prompt_msg == {"type": "prompt", "message": "bug text"}

        new_session_msg = json.loads(writes[1])
        assert new_session_msg == {"type": "new_session"}

    def test_popen_flags(self):
        lines = [
            self._make_agent_end("network"),
            self.NEW_SESSION_RESPONSE,
        ]
        _, _, mock_popen = self._make_backend(lines)

        args = mock_popen.call_args[0][0]
        assert args[0] == "/usr/bin/pi"
        assert "--mode" in args and "rpc" in args
        assert "--no-session" in args
        assert "--no-tools" in args
        assert "--no-extensions" in args
        assert "--no-skills" in args
        assert "--thinking" in args and "off" in args
        assert "--model" in args and "test-model" in args
        assert "--system-prompt" in args and "classify this" in args

    def test_close_terminates_subprocess(self):
        lines = [
            self._make_agent_end("network"),
            self.NEW_SESSION_RESPONSE,
        ]
        backend, mock_proc, _ = self._make_backend(lines)
        backend.close()

        mock_proc.stdin.close.assert_called_once()
        mock_proc.terminate.assert_called_once()
        mock_proc.wait.assert_called_once_with(timeout=5)

    def test_close_noop_when_already_exited(self):
        lines = [
            self._make_agent_end("network"),
            self.NEW_SESSION_RESPONSE,
        ]
        backend, mock_proc, _ = self._make_backend(lines)
        mock_proc.poll.return_value = 0  # already exited
        backend.close()

        mock_proc.terminate.assert_not_called()

    def test_missing_pi_binary_raises(self):
        with patch("shutil.which", return_value=None):
            from bug_classifier.backend import PiBackend
            with pytest.raises(RuntimeError, match="pi binary not found"):
                PiBackend(model="test-model", preamble="classify this")

    def test_string_content_block(self):
        """agent_end with plain string content blocks (not dict)."""
        event = json.dumps({
            "type": "agent_end",
            "messages": [
                {"role": "assistant", "content": ["boot"]},
            ],
        })
        lines = [event, self.NEW_SESSION_RESPONSE]
        backend, _, _ = self._make_backend(lines)
        result = backend.classify("some bug", CATEGORIES)

        assert result.category == "boot"
