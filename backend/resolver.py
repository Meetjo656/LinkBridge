import re
from typing import Any, Dict, Optional
from database import find_android_equivalent, find_ios_equivalent

# Regex patterns for App Store and Play Store URLs
APP_STORE_REGEX = re.compile(
    r"^https?://(?:[a-zA-Z0-9-]+\.)?(?:apps|itunes)\.apple\.com/"
    r"(?:(?P<country>[a-zA-Z]{2})/)?app/"
    r"(?:(?P<app_name>[^/]+)/)?id(?P<app_id>\d+)",
    re.IGNORECASE,
)

PLAY_STORE_REGEX = re.compile(
    r"(?:https?://)?(?:play\.google\.com/store/apps/details\?|market://details\?)"
    r"(?:[^&]*&)*id=(?P<package>[a-zA-Z0-9_.]+)",
    re.IGNORECASE,
)


def parse_app_store_url(url: str) -> Optional[Dict[str, Any]]:
    """Parse an Apple App Store URL and extract relevant metadata."""
    if not url:
        return None

    clean_url = url.strip()
    if not clean_url.startswith(("http://", "https://")):
        clean_url = f"https://{clean_url}"

    match = APP_STORE_REGEX.search(clean_url)
    if not match:
        return None

    groups = match.groupdict()
    app_id = groups.get("app_id")
    country = groups.get("country")
    app_name = groups.get("app_name")

    if country:
        country = country.lower()

    formatted_name = (
        app_name.replace("-", " ").title() if app_name else None
    )

    canonical_path = f"{country}/" if country else ""
    canonical_url = f"https://apps.apple.com/{canonical_path}app/id{app_id}"

    return {
        "app_id": app_id,
        "app_name": app_name,
        "formatted_name": formatted_name,
        "country": country,
        "canonical_url": canonical_url,
    }


def parse_play_store_url(url: str) -> Optional[Dict[str, Any]]:
    """Parse a Google Play Store URL and extract the package name."""
    if not url:
        return None

    clean_url = url.strip()
    match = PLAY_STORE_REGEX.search(clean_url)
    if not match:
        return None

    package = match.group("package")
    canonical_url = f"https://play.google.com/store/apps/details?id={package}"

    return {
        "package": package,
        "canonical_url": canonical_url,
    }


def resolve_link(url: str) -> Dict[str, Any]:
    """
    Deterministic resolution using the verified app_mappings database:
    1. App Store URL -> Play Store equivalent
    2. Play Store URL -> App Store equivalent
    3. Non-app links (YouTube, Spotify, regular websites) -> unsupported
    """
    if not url:
        return {
            "status": "unsupported",
            "reason": "empty_url",
        }

    clean_url = url.strip()

    # 1. Check for Apple App Store URL
    app_store_data = parse_app_store_url(clean_url)
    if app_store_data:
        ios_app_id = app_store_data["app_id"]
        mapping = find_android_equivalent(ios_app_id)
        if mapping:
            play_url = f"https://play.google.com/store/apps/details?id={mapping.android_package}"
            ios_url = app_store_data["canonical_url"]
            return {
                "status": "matched",
                "source": "ios",
                "target": "android",
                "url": play_url,
                "ios_url": ios_url,
                "android_url": play_url,
                "app_name": mapping.ios_name,
            }
        return {
            "status": "unsupported",
            "reason": "no_verified_mapping",
        }

    # 2. Check for Google Play Store URL
    play_store_data = parse_play_store_url(clean_url)
    if play_store_data:
        package = play_store_data["package"]
        mapping = find_ios_equivalent(package)
        if mapping:
            ios_url = f"https://apps.apple.com/app/id{mapping.ios_app_id}"
            play_url = play_store_data["canonical_url"]
            return {
                "status": "matched",
                "source": "android",
                "target": "ios",
                "url": ios_url,
                "ios_url": ios_url,
                "android_url": play_url,
                "app_name": mapping.android_name,
            }
        return {
            "status": "unsupported",
            "reason": "no_verified_mapping",
        }

    # 3. Everything else (Spotify, YouTube, Netflix, standard websites) -> left unchanged
    return {
        "status": "unsupported",
        "reason": "not_an_app_link",
    }