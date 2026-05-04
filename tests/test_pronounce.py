from podcastgen.util.pronounce import apply_pronunciations


def test_say_letters_whole_word_only() -> None:
    rules = {"say_letters": ["GPU"]}
    assert apply_pronunciations("Buy a GPU now.", rules) == "Buy a G P U now."
    # Case-sensitive: lowercase isn't touched
    assert apply_pronunciations("the gpu cluster", rules) == "the gpu cluster"
    # Word boundary respected
    assert apply_pronunciations("GPUs are everywhere", rules) == "GPUs are everywhere"


def test_say_word_phonetic() -> None:
    rules = {"say_word": {"NATO": "nay-toh", "Zelensky": "zeh-len-skee"}}
    assert apply_pronunciations("NATO and Zelensky.", rules) == "nay-toh and zeh-len-skee."


def test_replace_literal() -> None:
    rules = {"replace": {"xAI": "x A I", "GPT-4": "G P T four"}}
    assert apply_pronunciations("xAI ships GPT-4.", rules) == "x A I ships G P T four."


def test_combined_pipeline() -> None:
    rules = {
        "say_letters": ["GPU"],
        "say_word": {"NATO": "nay-toh"},
        "replace": {"xAI": "x A I"},
    }
    out = apply_pronunciations("xAI bought a GPU; NATO approved.", rules)
    assert out == "x A I bought a G P U; nay-toh approved."
