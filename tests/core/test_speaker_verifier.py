"""Unit tests for viko.core.speaker_verifier.SpeakerVerifier (mocked resemblyzer)."""
from unittest.mock import patch
import numpy as np
import tempfile
import pytest
from pathlib import Path

from viko.core.speaker_verifier import SpeakerVerifier, SAMPLE_RATE, SIMILARITY_THRESHOLD


def _make_pcm(seconds: float = 3.0) -> bytes:
    n = int(SAMPLE_RATE * seconds)
    return np.zeros(n, dtype=np.int16).tobytes()


class TestSpeakerVerifier:
    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.profile = Path(self.tmp) / "voice_profile.npy"
        self.sv = SpeakerVerifier(profile_path=self.profile)

    def test_not_enrolled_initially(self):
        assert self.sv.is_enrolled() is False

    def test_enroll_creates_profile(self):
        fake_emb = np.ones(256, dtype=np.float64)
        with patch.object(self.sv, "_embed", return_value=fake_emb):
            self.sv.enroll(_make_pcm())
        assert self.profile.exists()

    def test_is_enrolled_after_enroll(self):
        fake_emb = np.ones(256, dtype=np.float64)
        with patch.object(self.sv, "_embed", return_value=fake_emb):
            self.sv.enroll(_make_pcm())
        assert self.sv.is_enrolled() is True

    def test_verify_returns_true_for_owner(self):
        emb = np.ones(256, dtype=np.float64)
        with patch.object(self.sv, "_embed", return_value=emb):
            self.sv.enroll(_make_pcm())
        with patch.object(self.sv, "_embed", return_value=emb):
            assert self.sv.verify(_make_pcm()) is True

    def test_verify_returns_false_for_stranger(self):
        owner_emb    = np.ones(256, dtype=np.float64)
        stranger_emb = -np.ones(256, dtype=np.float64)
        with patch.object(self.sv, "_embed", return_value=owner_emb):
            self.sv.enroll(_make_pcm())
        with patch.object(self.sv, "_embed", return_value=stranger_emb):
            assert self.sv.verify(_make_pcm()) is False

    def test_verify_returns_true_when_not_enrolled(self):
        # No profile → open access (enrollment not yet done)
        assert self.sv.verify(_make_pcm()) is True
