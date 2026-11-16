"""Pure-Python matcher for RabbitMQ topic routing predictions.

`*` matches exactly one dot-separated word; `#` matches zero or more words.
The broker remains the authority: this helper is used only for predictions/tests.
"""
DRIVERS = {
    "Ravi": "bangalore.koramangala.*",
    "Priya": "bangalore.indiranagar.*",
    "Arjun": "bangalore.*.ride",
    "Meena": "bangalore.*.food",
    "Karthik": "chennai.tnagar.food",
    "Control": "bangalore.#",
}


def topic_match(pattern: str, key: str) -> bool:
    return _match(pattern.split("."), key.split("."))


def _match(pattern_words: list[str], key_words: list[str]) -> bool:
    if not pattern_words:
        return not key_words
    head, rest = pattern_words[0], pattern_words[1:]
    if head == "#":
        return any(_match(rest, key_words[index:]) for index in range(len(key_words) + 1))
    if not key_words:
        return False
    if head == "*" or head == key_words[0]:
        return _match(rest, key_words[1:])
    return False


def receivers(key: str) -> list[str]:
    return [name for name, pattern in DRIVERS.items() if topic_match(pattern, key)]


if __name__ == "__main__":
    keys = [
        "bangalore.koramangala.food",
        "bangalore.indiranagar.ride",
        "bangalore.whitefield.ride",
        "chennai.tnagar.food",
        "chennai.whitefield.ride",
        "bangalore.koramangala",
    ]
    for number, key in enumerate(keys, 1):
        print(number, key, "->", receivers(key) or "dropped")
