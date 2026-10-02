from rapidfuzz import fuzz


def normalize(text: str) -> str:
    if not text:
        return ""

    text = text.lower()

    replacements = [
        ":", "-", "_", ".", ","
    ]

    for char in replacements:
        text = text.replace(char, " ")

    return " ".join(text.split())


def name_similarity(source_name: str, target_name: str) -> float:
    source = normalize(source_name)
    target = normalize(target_name)

    return fuzz.token_set_ratio(source, target) / 100.0


def developer_similarity(
    source_developer: str,
    target_developer: str
) -> float:

    if not source_developer or not target_developer:
        return 0.0

    source = normalize(source_developer)
    target = normalize(target_developer)

    return fuzz.token_set_ratio(source, target) / 100.0


def calculate_confidence(
    source_name: str,
    target_name: str,
    source_developer: str | None = None,
    target_developer: str | None = None,
    category_match: bool = False
) -> dict:

    name_score = name_similarity(
        source_name,
        target_name
    )

    developer_score = developer_similarity(
        source_developer or "",
        target_developer or ""
    )

    category_score = 1.0 if category_match else 0.0

    confidence = (
        0.50 * name_score +
        0.30 * developer_score +
        0.20 * category_score
    )

    return {
        "name_similarity": round(name_score, 3),
        "developer_similarity": round(developer_score, 3),
        "category_match": category_match,
        "confidence": round(confidence, 3)
    }
