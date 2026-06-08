import numpy as np
import pytest
import torch


def test_silero_vad_loads():
    from silero_vad import load_silero_vad
    model = load_silero_vad()
    assert model is not None


def test_silero_vad_scores_silence():
    from silero_vad import load_silero_vad
    model = load_silero_vad()
    silence = np.zeros(512, dtype=np.float32)
    prob = float(model(torch.from_numpy(silence), 16000))
    assert 0.0 <= prob <= 1.0
    assert prob < 0.5, f"Expected silence < 0.5, got {prob}"


def test_silero_vad_scores_tone():
    from silero_vad import load_silero_vad
    model = load_silero_vad()
    t = np.linspace(0, 512 / 16000, 512, dtype=np.float32)
    tone = np.sin(2 * np.pi * 300 * t) * 0.5
    prob = float(model(torch.from_numpy(tone), 16000))
    assert 0.0 <= prob <= 1.0
