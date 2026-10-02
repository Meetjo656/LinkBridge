import re
from typing import Any, Dict, Optional
from urllib.parse import urlparse

# Regex pattern for Apple App Store / iTunes store URLs
APP_STORE_REGEX = re.compile(
    r"^https?://(?:[a-zA-Z0-9-]+\.)?(?:apps|itunes)\.apple\.com/"
    r"(?:(?P<country>[a-zA-Z]{2})/)?app/"
    r"(?:(?P<app_name>[^/]+)/)?id(?P<app_id>\d+)",
    re.IGNORECASE,
)


def is_app_store_url(url: str) -> bool:
    """Check if the provided URL is a valid Apple App Store URL."""
    if not url:
        return False
    clean_url = url.strip()
    if not clean_url.startswith(("http://", "https://")):
        clean_url = f"https://{clean_url}"
    return bool(APP_STORE_REGEX.search(clean_url))


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

    # Normalize human-readable app name from slug
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


def resolve_link(url: str) -> Dict[str, Any]:
    """Resolve an incoming URL using the App Store parser."""
    parsed_info = parse_app_store_url(url)

    if not parsed_info:
        return {
            "type": "unknown",
            "source": "unknown",
            "status": "unsupported_url",
            "url": url,
            "error": "The provided URL is not a valid Apple App Store URL.",
        }

    return {
        "type": "app",
        "source": "ios",
        "platform": "app_store",
        "status": "success",
        "url": url,
        **parsed_info,
    }