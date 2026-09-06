"""
Dynamic Route Parameter Normalizer for JASUSS Autonomous Discovery Engine.
Converts dynamic path segments (UUIDs, IDs, tokens) into parameterized route templates.
"""
import re
from urllib.parse import urlparse


UUID_REGEX = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
INTEGER_ID_REGEX = re.compile(r"^\d+$")
HEX_TOKEN_REGEX = re.compile(r"^[0-9a-fA-F]{16,}$")


def extract_route_template(url: str) -> str:
    """
    Extracts canonical route pattern from full URL.
    Examples:
        https://example.com/users/123/profile -> /users/:id/profile
        https://example.com/scans/550e8400-e29b-41d4-a716-446655440000 -> /scans/:uuid
    """
    parsed = urlparse(url)
    path = parsed.path or "/"
    if not path.startswith("/"):
        path = "/" + path

    segments = path.split("/")
    normalized_segments = []

    for seg in segments:
        if not seg:
            continue
        if UUID_REGEX.match(seg):
            normalized_segments.append(":uuid")
        elif INTEGER_ID_REGEX.match(seg):
            normalized_segments.append(":id")
        elif HEX_TOKEN_REGEX.match(seg):
            normalized_segments.append(":token")
        else:
            normalized_segments.append(seg)

    route = "/" + "/".join(normalized_segments)
    return route if route != "/" else "/"
