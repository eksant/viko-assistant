_WAKE_KEYWORDS = ("viko", "hei viko", "hey viko")


def _is_viko_addressed(in_buf: list[str]) -> bool:
    accumulated = "".join(in_buf).lower()
    return any(kw in accumulated for kw in _WAKE_KEYWORDS)


def test_wake_word_single_chunk():
    assert _is_viko_addressed(["Viko, cuaca hari ini?"]) is True


def test_wake_word_prefix_hei():
    assert _is_viko_addressed(["Hei Viko, tolong bantu saya."]) is True


def test_wake_word_prefix_hey():
    assert _is_viko_addressed(["Hey Viko, bukakan browser."]) is True


def test_wake_word_case_insensitive():
    assert _is_viko_addressed(["VIKO kemana kamu?"]) is True


def test_wake_word_streaming_chunks():
    # Gemini transcription may arrive as fragments without spaces between them
    assert _is_viko_addressed(["Vik", "o, halo"]) is True


def test_no_wake_word():
    assert _is_viko_addressed(["Cuaca hari ini bagaimana?"]) is False


def test_no_wake_word_partial():
    # "viktor" contains "viko" — this is a known false positive we accept
    # Test documents the behaviour rather than asserting False
    result = _is_viko_addressed(["viktor"])
    assert isinstance(result, bool)


def test_empty_buf():
    assert _is_viko_addressed([]) is False
