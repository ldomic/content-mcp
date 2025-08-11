from typing import Any, Optional
import httpx
import logging

from mcp.server.fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("anime")
logger = logging.getLogger('anime')
# Constants
NWS_API_BASE = "https://api.jikan.moe/v4/"

async def make_jikan_request(url: str) -> dict[str, Any] | None:
    """Make a request to the NWS API with proper error handling."""

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception:
            return None

def format_genre(data):
    return f"""
    ID: {data["mal_id"]},
    Name: {data["name"]}.
    Count: {data["count"]}
    """

def get_english_title(data):
    if data["title_english"]:
        return data["title_english"]
    if data["titles"]:
        english_title = [x["title"] for x in data["titles"] if x["type"] == "English"]
        default_title = [x["title"] for x in data["titles"] if x["type"] == "Default"]
        if len(english_title) > 0:
            return english_title[0]
        if len(default_title) > 0:
            return default_title[0]
        return data["titles"][0]["title"]
    return data["title"] if data["title"] else "Couldn't find title"


def format_anime(data):
    title = get_english_title(data)
    return f"""
    Title: {title},
    Episodes: {data["episodes"]},
    Status: {data["status"]}
    Score: {data["score"]}
    """

@mcp.tool()
async def get_anime_genre() -> str:
    """Get the available anime genres"""
    url = f"{NWS_API_BASE}genres/anime"

    response = await make_jikan_request(url)
    if not response or "data" not in response:
        return "Unable to fetch anime genres."
    try:
        genres = [format_genre(genre) for genre in response["data"]]
        return "\n---\n".join(genres)
    except Exception as e:
        logger.error(e)
        return "Couldn't find genres"


@mcp.tool()
async def get_anime(title: Optional[str], genre: Optional[int], is_good: Optional[bool], content_type: str = 'tv') -> str:
    """Find anime based on title or genre (which can be found from get_anime_genre).

    Args:
        title: Title of an anime
        content_type:
            Enum - "tv" "movie" "ova" "special" "ona" "music" "cm" "pv" "tv_special"
            Assume I always want to watch TV series unless I specifically ask for
            other types, then use one of the enum options
        genre: Genre of an anime (ID from get_anime_genre)
        is_good: A wish to search for anime based on score
    """
    url = f"{NWS_API_BASE}anime?"
    if title:
        url = url + f"q={title}"
    if genre:
        url = url + f"genres={genre}"
    if is_good:
        url = url + f"&order_by=score"
    url = url + f"&type={content_type}"
    if not title and not genre:
        return "Title or genre not selected"
    logger.info(url)
    response = await make_jikan_request(url)
    if not response or "data" not in response:
        return "Unable to fetch anime or anime not found."

    if not response["data"]:
        return "Anime not found."

    animes = [format_anime(anime) for anime in response["data"]]
    return "\n---\n".join(animes)

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')