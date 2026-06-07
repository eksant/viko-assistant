from __future__ import annotations
import numpy as np
from pathlib import Path

SAMPLE_RATE          = 16000
SIMILARITY_THRESHOLD = 0.75
_PROFILE_PATH = Path(__file__).resolve().parent.parent.parent / "memory" / "voice_profile.npy"


class SpeakerVerifier:
    def __init__(self, profile_path: Path = _PROFILE_PATH) -> None:
        self._path    = profile_path
        self._encoder = None

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
        return self._path.exists()

    def enroll(self, pcm_bytes: bytes) -> None:
        embedding = self._embed(pcm_bytes)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        np.save(str(self._path), embedding)

    def verify(self, pcm_bytes: bytes) -> bool:
        if not self.is_enrolled():
            return True
        stored    = np.load(str(self._path))
        candidate = self._embed(pcm_bytes)
        similarity = float(
            np.dot(stored, candidate)
            / (np.linalg.norm(stored) * np.linalg.norm(candidate))
        )
        return similarity >= SIMILARITY_THRESHOLD
