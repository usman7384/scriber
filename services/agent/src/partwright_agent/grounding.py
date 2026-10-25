import re

from partwright_agent.requirements import Requirement

NUMBER_WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "twelve": 12}


def grounded(reqs: list[Requirement], text: str) -> list[Requirement]:
    numbers = _numbers(text)
    return [r for r in reqs if _is_grounded(r, numbers, text)]


def _is_grounded(r: Requirement, numbers: set[float], text: str) -> bool:
    if r.kind != "holes":
        return r.value is not None and round(r.value, 3) in numbers
    count_ok = r.count is None or float(r.count) in numbers
    explicit = [d for d in (r.diameter_min, r.diameter_max) if d is not None]
    size_ok = not explicit or bool(re.search(r"\bM\d", text)) or any(round(d, 3) in numbers for d in _bounds_mid(explicit))
    return count_ok and size_ok


def _bounds_mid(bounds: list[float]) -> list[float]:
    return [*bounds, round(sum(bounds) / len(bounds), 3)]


def _numbers(text: str) -> set[float]:
    found = {round(float(n), 3) for n in re.findall(r"\d+(?:\.\d+)?", text)}
    words = {float(v) for w, v in NUMBER_WORDS.items() if re.search(rf"\b{w}\b", text, re.IGNORECASE)}
    return found | words
