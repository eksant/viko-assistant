import asyncio
import json
import os
import urllib.request

import numpy as np
import sounddevice as sd


def ollama_chat(text: str, system: str) -> str:
    """Call local Ollama (localhost:11434). Raises on failure."""
    model = os.environ.get("OLLAMA_MODEL", "qwen2.5:1.5b")
    payload = json.dumps({
        "model": model, "system": system, "prompt": text, "stream": False,
    }).encode()
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    return data["response"].strip()


async def offline_respond(text: str, *, write_log) -> None:
    """Get LLM reply and speak via macOS say.

    Priority: Ollama (local) → cloud LLM → static fallback.
    """
    loop = asyncio.get_running_loop()
    system = (
        "Kamu adalah VIKO, asisten AI suara pribadi milik Eksa. "
        "Jawab dalam Bahasa Indonesia, singkat dan jelas (1-2 kalimat). "
        "Mode offline — tidak ada akses internet saat ini."
    )
    reply = None

    try:
        reply = await loop.run_in_executor(None, ollama_chat, text, system)
        print(f"[Viko] Offline via Ollama: {reply[:60]}…")
    except Exception as e:
        print(f"[Viko] Ollama unavailable: {e}")

    if not reply:
        try:
            from viko.core.client import LLMClient
            reply = await loop.run_in_executor(None, LLMClient().chat, text, system)
        except Exception as e:
            print(f"[Viko] Offline LLM failed: {e}")

    if not reply:
        reply = "Maaf, saya sedang offline dan tidak bisa menjawab sekarang."

    write_log(f"Viko [offline]: {reply}")
    try:
        proc = await asyncio.create_subprocess_exec(
            "say", "-v", "Damayanti", reply,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await proc.wait()
    except Exception:
        try:
            proc = await asyncio.create_subprocess_exec("say", reply)
            await proc.wait()
        except Exception as e:
            print(f"[Viko] say failed: {e}")


async def offline_mode(
    *,
    stt,
    sv,
    sv_pass_threshold: float,
    verification_bypass: bool,
    is_muted,
    is_paused,
    write_log,
    sample_rate: int,
    channels: int,
    chunk_size: int,
    speech_threshold: int,
    silence_chunks: int,
    min_speech_chunks: int,
    max_seconds: int = 60,
) -> None:
    """Offline listen-and-respond loop: faster-whisper STT + LLM + macOS say.

    VAD constants (caller-supplied):
      speech_threshold  — int16 RMS above this = active speech
      silence_chunks    — consecutive silent chunks that end an utterance
      min_speech_chunks — minimum speech chunks before transcribing
    """
    loop = asyncio.get_running_loop()
    audio_q: asyncio.Queue = asyncio.Queue()

    def _rms(data: bytes) -> float:
        arr = np.frombuffer(data, dtype=np.int16).astype(np.float32)
        return float(np.sqrt(np.mean(arr ** 2))) if len(arr) else 0.0

    def _cb(indata, frames, time_info, status):
        if is_muted() or is_paused():
            return
        loop.call_soon_threadsafe(audio_q.put_nowait, indata.tobytes())

    buf: list[bytes] = []
    silence_count = 0
    speech_count = 0
    in_speech = False
    deadline = loop.time() + max_seconds

    with sd.InputStream(
        samplerate=sample_rate,
        channels=channels,
        dtype="int16",
        blocksize=chunk_size,
        callback=_cb,
    ):
        write_log("SYS: Mode offline. Whisper aktif.")
        print("[Viko] Offline STT active")

        while loop.time() < deadline:
            try:
                chunk = await asyncio.wait_for(audio_q.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            rms = _rms(chunk)

            if rms > speech_threshold:
                buf.append(chunk)
                speech_count += 1
                silence_count = 0
                in_speech = True
            elif in_speech:
                buf.append(chunk)
                silence_count += 1
                if silence_count >= silence_chunks:
                    if speech_count >= min_speech_chunks:
                        pcm = b"".join(buf)
                        sim = await loop.run_in_executor(None, sv.similarity, pcm)
                        is_owner = (
                            verification_bypass
                            or not sv.is_enrolled()
                            or sim >= sv_pass_threshold
                        )
                        if is_owner:
                            text = await loop.run_in_executor(
                                None, stt.transcribe_pcm, pcm
                            )
                            if text.strip():
                                write_log(f"You [offline]: {text}")
                                await offline_respond(text, write_log=write_log)
                    buf = []
                    silence_count = 0
                    speech_count = 0
                    in_speech = False

    print("[Viko] Offline mode ended — reconnecting")
