from __future__ import annotations

import numpy as np

SAMPLE_RATE = 16000


class OfflineSTT:
    """Offline speech-to-text via faster-whisper (small/int8/cpu/id).

    Model is lazy-loaded on first transcribe_pcm() call. First call
    downloads ~500 MB to ~/.cache/huggingface/hub/ if not cached.
    """

    MODEL_SIZE = "small"
    LANGUAGE = "id"

    def __init__(self) -> None:
        self._model = None

    def _load(self) -> None:
        from faster_whisper import WhisperModel
        self._model = WhisperModel(
            self.MODEL_SIZE,
            device="cpu",
            compute_type="int8",
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
