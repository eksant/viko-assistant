from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

SAMPLE_RATE = 16000


def _model_dir() -> Path:
    """Return models/whisper/ inside the project root (works in source and frozen app)."""
    if getattr(sys, "frozen", False):
        for parent in Path(sys.executable).resolve().parents:
            candidate = parent / "models" / "whisper"
            if candidate.exists():
                return candidate
        return Path(sys.executable).resolve().parent / "models" / "whisper"
    return Path(__file__).resolve().parent.parent.parent / "models" / "whisper"


class OfflineSTT:
    """Offline speech-to-text via faster-whisper (small/int8/cpu/id).

    Model is lazy-loaded on first transcribe_pcm() call. First call
    downloads ~500 MB to models/whisper/ in the project root.
    """

    MODEL_SIZE = "small"
    LANGUAGE = "id"

    def __init__(self) -> None:
        self._model = None

    def _load(self) -> None:
        from faster_whisper import WhisperModel
        model_dir = _model_dir()
        model_dir.mkdir(parents=True, exist_ok=True)
        self._model = WhisperModel(
            self.MODEL_SIZE,
            device="cpu",
            compute_type="int8",
            download_root=str(model_dir),
        )

    def transcribe_pcm(self, pcm_bytes: bytes, sample_rate: int = SAMPLE_RATE) -> str:
        """Transcribe raw int16 PCM bytes to Indonesian text.

        Safe to call from a thread executor — ctranslate2 releases the GIL.
        """
        if self._model is None:
            self._load()
        audio = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
        segments, _ = self._model.transcribe(
            audio,
            language=self.LANGUAGE,
            beam_size=5,
            vad_filter=True,
        )
        return " ".join(seg.text.strip() for seg in segments).strip()
