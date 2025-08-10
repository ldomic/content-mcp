from typing import Any
import httpx

from main import mcp

# Constants
NWS_API_BASE = "https://api.jikan.moe/v4/anime"

async def make_jikan_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper error handling."""

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None


def format_anime(data):
    title = data["titles"][0]["title"] if data["titles"] else "Couldn't find title"
    return f"""
    Title: {title},
    Episodes: {data["episodes"]},
    Status: {data["status"]}
    """

@mcp.tool()
async def get_anime(title: str) -> str:
    """Find anime based on title.

    Args:
        title: Title of an anime
    """
    url = f"{NWS_API_BASE}?q={title}"
    response = await make_jikan_request(url)

    if not response or "data" not in response:
        return "Unable to fetch anime or anime not found."

    if not response["data"]:
        return "Anime not found."

    animes = [format_anime(anime) for anime in response["data"]]
    return "\n---\n".join(animes)
