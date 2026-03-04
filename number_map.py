# number_mapp.py

UNITS = {
    "zero": 0, "one": 1, "two" or "to": 2, "three": 3, "four" or "for": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9
}

TEENS = {
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19
}

TENS = {
    "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90
}


def words_to_number(words):
    words = words.split()
    current = 0

    for w in words:
        if w in UNITS:
            current += UNITS[w]
        elif w in TEENS:
            current += TEENS[w]
        elif w in TENS:
            current += TENS[w]
        elif w == "hundred":
            current *= 100
        else:
            return None

    return current


def normalize_numbers(text):
    words = text.split()
    out = []
    buffer = []

    for w in words:
        if w.isdigit():
            out.append(w)
        elif w in UNITS or w in TEENS or w in TENS or w == "hundred":
            buffer.append(w)
        else:
            if buffer:
                num = words_to_number(" ".join(buffer))
                if num is not None:
                    out.append(str(num))
                buffer.clear()
            out.append(w)

    if buffer:
        num = words_to_number(" ".join(buffer))
        if num is not None:
            out.append(str(num))

    return " ".join(out)
