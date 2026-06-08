import re

# Mirrors viko.py `_is_viko_addressed`. Gemini Live's input transcription has no
# language setting and renders the Indonesian wake word "Viko" inconsistently —
# "Vico", "Pico", "Biko", "Fico", "Ficou", "Focou" etc. We match the phonetic
# SHAPE (labial onset + front vowel + velar + back vowel) rather than a fixed list.
_WAKE_RE = re.compile(r"^[vbpfw][ieo]+[ck]+[ou]+$")
_WAKE_EXTRA = frozenset({"viktor"})


def _is_viko_addressed(accumulated: str) -> bool:
    return any(_WAKE_RE.match(w) or w in _WAKE_EXTRA
               for w in re.findall(r"[a-z]+", accumulated.lower()))


# --- mishearings that MUST wake VIKO (observed from real Gemini transcriptions) ---

def test_exact_viko():
    assert _is_viko_addressed("Viko, cuaca hari ini?") is True


def test_case_insensitive():
    assert _is_viko_addressed("VIKO kemana kamu?") is True


def test_mishearing_vico():
    assert _is_viko_addressed("Hello Vico") is True


def test_mishearing_pico_picco():
    assert _is_viko_addressed("Pico, hello.") is True
    assert _is_viko_addressed("Picco.") is True


def test_mishearing_biko():
    assert _is_viko_addressed("Biko, halo") is True


def test_mishearing_fico_ficou_focou():
    # The cases the user reported as failing before the phonetic matcher
    assert _is_viko_addressed("Fico") is True
    assert _is_viko_addressed("Ficou.") is True
    assert _is_viko_addressed("Focou") is True


def test_outlier_viktor():
    assert _is_viko_addressed("viktor") is True


# --- normal words that MUST NOT wake VIKO ---

def test_reject_indonesian_words():
    for w in ["buka pintu", "baik sekali", "fokus dulu", "bocor atapnya",
              "pojok kanan", "bagus banget", "buku ini", "bisa tidak"]:
        assert _is_viko_addressed(w) is False, w


def test_reject_english_words():
    for w in ["go back", "a book", "hello there", "the topic", "because of"]:
        assert _is_viko_addressed(w) is False, w


def test_no_wake_word():
    assert _is_viko_addressed("Cuaca hari ini bagaimana?") is False


def test_empty():
    assert _is_viko_addressed("") is False
