"""Unit tests for viko.core.offline_stt.OfflineSTT (mocked model)."""
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from viko.core.offline_stt import OfflineSTT, SAMPLE_RATE


def _make_pcm(seconds: float = 1.0) -> bytes:
    """Generate 1 second of silent int16 PCM."""
    n = int(SAMPLE_RATE * seconds)
    return np.zeros(n, dtype=np.int16).tobytes()


class TestOfflineSTT:
    def test_init_does_not_load_model(self):
        """Model must not be loaded at construction time."""
        stt = OfflineSTT()
        assert stt._model is None

    def test_load_creates_whisper_model(self):
        """_load() must call WhisperModel with correct args and a project-local download_root."""
        stt = OfflineSTT()
        with patch("faster_whisper.WhisperModel") as mock_cls:
            mock_cls.return_value = MagicMock()
            stt._load()
            call_kwargs = mock_cls.call_args
            assert call_kwargs[0][0] == "small"
            assert call_kwargs[1]["device"] == "cpu"
            assert call_kwargs[1]["compute_type"] == "int8"
            assert "models/whisper" in call_kwargs[1]["download_root"]
            assert stt._model is not None

    def test_transcribe_pcm_calls_load_on_first_use(self):
        """transcribe_pcm() must call _load() if _model is None."""
        stt = OfflineSTT()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = (iter([]), MagicMock())

        def _fake_load():
            stt._model = mock_model

        with patch.object(stt, "_load", side_effect=_fake_load) as mock_load:
            stt.transcribe_pcm(_make_pcm())
            mock_load.assert_called_once()

    def test_transcribe_pcm_joins_segments(self):
        """transcribe_pcm() must join all segment texts with spaces and strip."""
        stt = OfflineSTT()
        seg1 = MagicMock(text=" halo ")
        seg2 = MagicMock(text=" dunia ")
        mock_model = MagicMock()
        mock_model.transcribe.return_value = (iter([seg1, seg2]), MagicMock())
        stt._model = mock_model

        result = stt.transcribe_pcm(_make_pcm())

        assert result == "halo dunia"

    def test_transcribe_empty_segments_returns_empty_string(self):
        """transcribe_pcm() with no segments must return empty string."""
        stt = OfflineSTT()
        mock_model = MagicMock()
        mock_model.transcribe.return_value = (iter([]), MagicMock())
        stt._model = mock_model

        result = stt.transcribe_pcm(_make_pcm())

        assert result == ""
