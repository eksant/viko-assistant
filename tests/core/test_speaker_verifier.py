"""Unit tests for viko.core.speaker_verifier.SpeakerVerifier (mocked resemblyzer)."""
from unittest.mock import patch, MagicMock
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


# --- Bug-fix regression tests ---

def _make_verifier_with_profile(tmp_path: Path, embedding: np.ndarray):
    profile = tmp_path / "voice_profile.npy"
    np.save(str(profile), embedding)
    sv = SpeakerVerifier(profile_path=profile)
    return sv


def test_similarity_zero_norm_returns_zero(tmp_path):
    """similarity() must return 0.0, not NaN, when embedding is a zero vector."""
    sv = _make_verifier_with_profile(tmp_path, np.array([1.0, 0.0, 0.0]))
    with patch.object(sv, "_embed", return_value=np.zeros(3)):
        result = sv.similarity(b"\x00" * 64)
    assert result == 0.0, f"Expected 0.0, got {result}"
    assert not np.isnan(result), "similarity() must not return NaN"


def test_similarity_loads_profile_once_across_two_calls(tmp_path):
    """np.load must be called once total across two similarity() calls (cached)."""
    stored = np.array([1.0, 0.0, 0.0])
    sv = _make_verifier_with_profile(tmp_path, stored)
    candidate = np.array([1.0, 0.0, 0.0])
    with patch.object(sv, "_embed", return_value=candidate):
        with patch("numpy.load", wraps=np.load) as mock_load:
            sv.similarity(b"\x00" * 64)
            sv.similarity(b"\x00" * 64)
            assert mock_load.call_count == 1, (
                f"np.load called {mock_load.call_count} times; expected 1 after caching"
            )


def test_is_enrolled_uses_cached_flag_after_enroll(tmp_path):
    """is_enrolled() must not call Path.exists() after enroll() sets the cache."""
    sv = SpeakerVerifier(profile_path=tmp_path / "voice_profile.npy")
    with patch.object(sv, "_embed", return_value=np.array([1.0, 0.0, 0.0])):
        sv.enroll(b"\x00" * 1024)
    # Replace _path with a MagicMock — any call to .exists() would be detected
    mock_path = MagicMock(spec=Path)
    sv._path = mock_path
    sv.is_enrolled()
    sv.is_enrolled()
    sv.is_enrolled()
    mock_path.exists.assert_not_called()


def test_enroll_invalidates_embedding_cache(tmp_path):
    """enroll() must update the cached embedding so next similarity() uses new profile."""
    stored_v1 = np.array([1.0, 0.0, 0.0])
    sv = _make_verifier_with_profile(tmp_path, stored_v1)
    with patch.object(sv, "_embed", return_value=stored_v1):
        sv.similarity(b"\x00" * 64)  # populates cache with v1
    stored_v2 = np.array([0.0, 1.0, 0.0])
    with patch.object(sv, "_embed", return_value=stored_v2):
        sv.enroll(b"\x00" * 1024)   # re-enroll with v2
        result = sv.similarity(b"\x00" * 64)
    # dot(v2, v2) / (|v2| * |v2|) = 1.0
    assert abs(result - 1.0) < 1e-6, f"Expected 1.0 after re-enroll, got {result}"
