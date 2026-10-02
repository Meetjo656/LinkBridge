import re
import urllib.request
import json
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

from google_play_scraper.constants.element import ElementSpecs
from google_play_scraper import search

# Patch google_play_scraper's appId extraction for the top featured card
if "appId" in ElementSpecs.SearchResultOnTop:
    ElementSpecs.SearchResultOnTop["appId"].data_map = [2, 41, 0, 2]
    ElementSpecs.SearchResultOnTop["appId"].post_processor = (
        lambda u: re.search(r"id=([a-zA-Z0-9_.]+)", u).group(1)
        if u and "id=" in u
        else u
    )


def fetch_apple_metadata(app_id: str, country: str = "us") -> Optional[Dict[str, Any]]:
    """
    Fetch app metadata from Apple's iTunes Lookup API.
    """
    url = f"https://itunes.apple.com/lookup?id={app_id}&country={country}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("resultCount", 0) > 0:
                result = data["results"][0]
                return {
                    "app_id": str(result.get("trackId", app_id)),
                    "app_name": result.get("trackName") or result.get("trackCensoredName"),
                    "developer": result.get("artistName"),
                    "bundle_id": result.get("bundleId"),
                    "primary_genre": result.get("primaryGenreName"),
                    "genres": result.get("genres", []),
                    "icon": result.get("artworkUrl512") or result.get("artworkUrl100"),
                    "url": result.get("trackViewUrl"),
                }
    except Exception as e:
        print(f"Error fetching Apple metadata for {app_id}: {e}")

    return None


def search_android_candidates(query: str, country: str = "us", n_hits: int = 10) -> List[Dict[str, Any]]:
    """
    Search the Google Play Store for candidate apps matching the query.
    """
    if not query:
        return []

    try:
        raw_results = search(query, n_hits=n_hits, country=country)
        candidates = []
        for r in raw_results:
            pkg = r.get("appId")
            if not pkg:
                # Fallback package extraction if still empty
                match = re.search(r"id=([a-zA-Z0-9_.]+)", str(r))
                if match:
                    pkg = match.group(1)

            if not pkg:
                continue

            candidates.append({
                "app_name": r.get("title"),
                "package": pkg,
                "developer": r.get("developer"),
                "genre": r.get("genre"),
                "score": r.get("score"),
                "icon": r.get("icon"),
                "url": f"https://play.google.com/store/apps/details?id={pkg}",
            })
        return candidates
    except Exception as e:
        print(f"Error searching Google Play for '{query}': {e}")
        return []


def _normalize_corp(name: Optional[str]) -> str:
    """Normalize corporate and developer names by removing entity types."""
    if not name:
        return ""
    cleaned = name.lower()
    cleaned = re.sub(r"[^\w\s]", "", cleaned)
    suffixes = [
        "llc",
        "inc",
        "corp",
        "corporation",
        "ltd",
        "limited",
        "co",
        "technologies",
        "software",
        "gmbh",
        "sa",
        "srl",
    ]
    for suffix in suffixes:
        cleaned = re.sub(rf"\b{suffix}\b", "", cleaned)
    return " ".join(cleaned.split())


def _normalize_title(title: Optional[str]) -> str:
    """Normalize app title by removing punctuation and subtitles."""
    if not title:
        return ""
    # Remove subtitles separated by common delimiters: -, :, |, etc.
    main_title = re.split(r"[-:|–—]", title)[0]
    cleaned = re.sub(r"[^\w\s]", "", main_title.lower())
    return " ".join(cleaned.split())


def calculate_match_score(
    ios_meta: Dict[str, Any], candidate: Dict[str, Any]
) -> float:
    """
    Calculate confidence score between an iOS app and an Android candidate app.
    Formula:
      - Name similarity: 50%
      - Developer similarity: 30%
      - Category & Package heuristic: 20%
    """
    ios_name = ios_meta.get("app_name") or ""
    ios_dev = ios_meta.get("developer") or ""
    android_name = candidate.get("app_name") or ""
    android_dev = candidate.get("developer") or ""
    android_pkg = candidate.get("package") or ""

    norm_ios_name = _normalize_title(ios_name)
    norm_and_name = _normalize_title(android_name)

    # 1. Name similarity (50%)
    if norm_ios_name == norm_and_name:
        name_sim = 1.0
    elif norm_ios_name in norm_and_name or norm_and_name in norm_ios_name:
        name_sim = max(0.9, SequenceMatcher(None, norm_ios_name, norm_and_name).ratio())
    else:
        name_sim = SequenceMatcher(None, norm_ios_name, norm_and_name).ratio()

    # 2. Developer similarity (30%)
    norm_ios_dev = _normalize_corp(ios_dev)
    norm_and_dev = _normalize_corp(android_dev)
    if norm_ios_dev and norm_and_dev:
        if norm_ios_dev == norm_and_dev:
            dev_sim = 1.0
        elif norm_ios_dev in norm_and_dev or norm_and_dev in norm_ios_dev:
            dev_sim = max(0.85, SequenceMatcher(None, norm_ios_dev, norm_and_dev).ratio())
        else:
            dev_sim = SequenceMatcher(None, norm_ios_dev, norm_and_dev).ratio()
    else:
        dev_sim = 0.5  # Neutral if developer metadata is missing

    # 3. Category & Package heuristics (20%)
    heuristics = 0.0
    # Package name contains app name or developer
    pkg_clean = android_pkg.lower().replace(".", "")
    if norm_ios_name.replace(" ", "") in pkg_clean:
        heuristics += 0.10
    if norm_ios_dev.replace(" ", "") in pkg_clean:
        heuristics += 0.10

    # Strong match shortcut: exact/near-exact name and same verified developer
    if name_sim >= 0.95 and dev_sim >= 0.95:
        return 1.0

    total_score = (name_sim * 0.50) + (dev_sim * 0.30) + heuristics
    return min(1.0, round(total_score, 2))


def find_best_android_match(
    ios_meta: Dict[str, Any], country: str = "us", min_confidence: float = 0.50
) -> Optional[Tuple[Dict[str, Any], float]]:
    """
    Find the best matching Android app for the given iOS app metadata.
    """
    app_name = ios_meta.get("app_name")
    if not app_name:
        return None

    # Query Play Store using the app's clean title
    search_query = _normalize_title(app_name) or app_name
    candidates = search_android_candidates(search_query, country=country, n_hits=10)

    if not candidates:
        return None

    scored_candidates = []
    for candidate in candidates:
        score = calculate_match_score(ios_meta, candidate)
        scored_candidates.append((candidate, score))

    scored_candidates.sort(key=lambda x: x[1], reverse=True)
    best_candidate, best_score = scored_candidates[0]

    if best_score < min_confidence:
        return None

    return best_candidate, best_score
