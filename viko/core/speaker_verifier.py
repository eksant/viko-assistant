from __future__ import annotations
import numpy as np
from pathlib import Path

SAMPLE_RATE          = 16000
SIMILARITY_THRESHOLD = 0.65
_PROFILE_PATH = Path(__file__).resolve().parent.parent.parent / "memory" / "voice_profile.npy"


class SpeakerVerifier:
    def __init__(self, profile_path: Path = _PROFILE_PATH) -> None:
        self._path              = profile_path
        self._encoder           = None
        self._stored_embedding: np.ndarray | None = None  # cache — invalidated by enroll()
        self._is_enrolled_flag: bool | None = None        # cache — avoids Path.exists() on hot path

    def _load_encoder(self) -> None:
        from resemblyzer import VoiceEncoder
        self._encoder = VoiceEncoder()

    def _embed(self, pcm_bytes: bytes) -> np.ndarray:
        if self._encoder is None:
            self._load_encoder()
        from resemblyzer import preprocess_wav
        audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        wav   = preprocess_wav(audio, source_sr=SAMPLE_RATE)
        return self._encoder.embed_utterance(wav)

    def is_enrolled(self) -> bool:
        if self._is_enrolled_flag is None:
            self._is_enrolled_flag = self._path.exists()
        return self._is_enrolled_flag

    def enroll(self, pcm_bytes: bytes) -> None:
        embedding = self._embed(pcm_bytes)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        np.save(str(self._path), embedding)
        self._stored_embedding = embedding   # update cache immediately
        self._is_enrolled_flag = True        # mark enrolled without re-stat

    def similarity(self, pcm_bytes: bytes) -> float:
        """Return cosine similarity (0–1); returns 0.0 for unenrolled or zero-norm vectors."""
        if not self.is_enrolled():
            return 1.0
        if self._stored_embedding is None:
            self._stored_embedding = np.load(str(self._path))
        candidate = self._embed(pcm_bytes)
        denom = float(np.linalg.norm(self._stored_embedding) * np.linalg.norm(candidate))
        if denom == 0.0:
            return 0.0
        return float(np.dot(self._stored_embedding, candidate) / denom)

    def verify(self, pcm_bytes: bytes) -> bool:
        return self.similarity(pcm_bytes) >= SIMILARITY_THRESHOLD
