import json
import re
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

from google_play_scraper import search
from google_play_scraper.constants.element import ElementSpecs

from rapidfuzz_matcher import (
    calculate_confidence,
    developer_similarity,
    name_similarity,
    normalize,
)

# Patch google_play_scraper's appId extraction for the top featured card
if "appId" in ElementSpecs.SearchResultOnTop:
    ElementSpecs.SearchResultOnTop["appId"].data_map = [2, 41, 0, 2]
    ElementSpecs.SearchResultOnTop["appId"].post_processor = (
        lambda u: re.search(r"id=([a-zA-Z0-9_.]+)", u).group(1)
        if u and "id=" in u
        else u
    )

CATEGORY_MAPPINGS = {
    "navigation": ["travel & local", "maps & navigation", "auto & vehicles"],
    "travel": ["travel & local", "navigation"],
    "photo & video": ["photography", "video players & editors"],
    "photography": ["photo & video"],
    "productivity": ["productivity", "business", "tools"],
    "business": ["business", "productivity"],
    "social networking": ["social", "communication"],
    "social": ["social networking", "communication"],
    "music": ["music & audio"],
    "entertainment": ["entertainment", "video players & editors"],
    "finance": ["finance"],
    "games": [
        "game",
        "action",
        "adventure",
        "arcade",
        "board",
        "card",
        "casino",
        "casual",
        "educational",
        "puzzle",
        "racing",
        "role playing",
        "simulation",
        "sports",
        "strategy",
        "trivia",
        "word",
    ],
    "utilities": ["tools"],
}


def check_category_match(
    ios_genres: List[str] | str | None, android_genre: Optional[str]
) -> bool:
    """Check whether iOS genres and Android genre match or belong to the same category group."""
    if not ios_genres or not android_genre:
        return False

    if isinstance(ios_genres, str):
        ios_genres = [ios_genres]

    and_genre_lower = android_genre.lower()
    for g in ios_genres:
        g_lower = g.lower()
        if g_lower == and_genre_lower or g_lower in and_genre_lower or and_genre_lower in g_lower:
            return True

        if g_lower in CATEGORY_MAPPINGS:
            for mapped in CATEGORY_MAPPINGS[g_lower]:
                if mapped in and_genre_lower:
                    return True

        if and_genre_lower in CATEGORY_MAPPINGS:
            for mapped in CATEGORY_MAPPINGS[and_genre_lower]:
                if mapped in g_lower:
                    return True

    return False


def fetch_apple_metadata(app_id: str, country: str = "us") -> Optional[Dict[str, Any]]:
    """Fetch app metadata from Apple's iTunes Lookup API."""
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
    """Search the Google Play Store for candidate apps matching the query."""
    if not query:
        return []

    try:
        raw_results = search(query, n_hits=n_hits, country=country)
        candidates = []
        for r in raw_results:
            pkg = r.get("appId")
            if not pkg:
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


def calculate_match_score(
    ios_meta: Dict[str, Any], candidate: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate confidence score between an iOS app and an Android candidate app using RapidFuzz.
    """
    ios_name = ios_meta.get("app_name") or ""
    ios_dev = ios_meta.get("developer") or ""
    android_name = candidate.get("app_name") or ""
    android_dev = candidate.get("developer") or ""

    ios_genres = ios_meta.get("genres") or []
    if not ios_genres and ios_meta.get("primary_genre"):
        ios_genres = [ios_meta["primary_genre"]]
    android_genre = candidate.get("genre")

    category_match = check_category_match(ios_genres, android_genre)

    metrics = calculate_confidence(
        source_name=ios_name,
        target_name=android_name,
        source_developer=ios_dev,
        target_developer=android_dev,
        category_match=category_match,
    )
    return metrics


def find_best_android_match(
    ios_meta: Dict[str, Any], country: str = "us", min_confidence: float = 0.50
) -> Optional[Tuple[Dict[str, Any], float, Dict[str, Any]]]:
    """
    Find the best matching Android app for the given iOS app metadata.
    Returns (best_candidate, confidence, metrics_breakdown) if confidence >= min_confidence.
    """
    app_name = ios_meta.get("app_name")
    if not app_name:
        return None

    # Query Play Store using normalized app title
    search_query = normalize(app_name) or app_name
    candidates = search_android_candidates(search_query, country=country, n_hits=10)

    if not candidates:
        return None

    scored_candidates = []
    for candidate in candidates:
        metrics = calculate_match_score(ios_meta, candidate)
        score = metrics["confidence"]
        scored_candidates.append((candidate, score, metrics))

    scored_candidates.sort(key=lambda x: x[1], reverse=True)
    best_candidate, best_score, best_metrics = scored_candidates[0]

    if best_score < min_confidence:
        return None

    return best_candidate, best_score, best_metrics
