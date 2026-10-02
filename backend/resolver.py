from urllib.parse import urlparse


def resolve_link(url: str):

    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    if "apps.apple.com" in domain:
        return {
            "type": "app",
            "source": "ios",
            "status": "needs_conversion",
            "url": url
        }

    if "play.google.com" in domain:
        return {
            "type": "app",
            "source": "android",
            "status": "needs_conversion",
            "url": url
        }

    return {
        "type": "unknown",
        "source": "universal",
        "status": "no_conversion_needed",
        "url": url
    }