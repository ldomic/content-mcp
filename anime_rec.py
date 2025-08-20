from typing import Any, List, Optional
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

def format_character(data):
    return f"""
    ID: {data["character"]["mal_id"]}
    Name: {data["character"]["name"]}
    Role: {data["role"]}
    """

def format_episode(data):
    return f"""
    ID: {data["mal_id"]}
    Title: {data["title"]}
    Filler/recap: {data["filler"] or data["recap"]}
    Aired: {data["aired"][:10]}
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


def format_anime(data, starts_at):
    title = get_english_title(data)
    response = f"""
    Title: {title},
    ID: {data["mal_id"]},
    Episodes: {data["episodes"]},
    Status: {data["status"]}
    Score: {data["score"]}
    """
    if starts_at:
        response += f"""
            Season: {data['season']}
            Year: {data['year']}
        """
    return response

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
async def get_anime(
        title: Optional[str],
        genre: Optional[int],
        is_good: Optional[bool],
        starts_at: Optional[str],
        status: Optional[str],
        content_type: str = 'tv'
    ) -> str:
    """Find anime based on title or genre (which can be found from get_anime_genre).

    Args:
        title: Title of an anime
        content_type:
            Enum - "tv" "movie" "ova" "special" "ona" "music" "cm" "pv" "tv_special"
            Assume I always want to watch TV series unless I specifically ask for
            other types, then use one of the enum options
        genre: Genre of an anime (ID from get_anime_genre)
        starts_at: String in 'YYYY-mm-dd' form which allows to filter anime by their start date or can be used to get season and year data
        status: Enum: "airing" "complete" "upcoming" - available statuses
        is_good: A wish to search for anime based on score
    """
    url = f"{NWS_API_BASE}anime?"
    if title:
        url = url + f"q={title}"
    if genre:
        url = url + f"genres={genre}"
    if is_good:
        url = url + f"&order_by=score"
    if starts_at:
        url = url + f"&starts_at={starts_at}"
    if status:
        url = url + f"&status={status}"
    url = url + f"&type={content_type}"
    if not title and not genre:
        return "Title or genre not selected"
    logger.info(url)
    response = await make_jikan_request(url)
    if not response or "data" not in response:
        return "Unable to fetch anime or anime not found."

    if not response["data"]:
        return "Anime not found."

    animes = [format_anime(anime, starts_at) for anime in response["data"]]
    return "\n---\n".join(animes)


@mcp.tool()
async def get_anime_characters(id: Optional[int], name: Optional[str]) -> str:
    url = f"{NWS_API_BASE}anime/{id}/characters"
    response = await make_jikan_request(url)
    if not response or "data" not in response:
        return "Unable to fetch anime or anime not found."

    characters = [format_character(char) for char in response["data"]]
    return "\n---\n".join(characters)


@mcp.tool()
async def get_anime_details(id: int, characters: bool, synopsis: bool) -> str:
    """
    Use this tool to get more details about a specific anime
    the user has expressed an interest into - requires a specific ID

    :param id: MAL ID which can be retrieved from get_anime
    :param characters: Flag to use if user is interested in characters for
    this anime
    :param synopsis: Only retrieve synopsis if it is required to answer a question or continue conversation
    :return:
    """

    url = f"{NWS_API_BASE}anime/{id}/full"

    response = await make_jikan_request(url)
    if not response or "data" not in response:
        return "Unable to fetch anime or anime not found."

    if characters:
        character_list = get_anime_characters(id=id)
    if not response["data"]:
        return f"Data couldn't be fetched for anime with ID {id}"
    data = response["data"]

    anime_description = f"""
    Episodes: {data["episodes"]}
    Streaming: {", ".join([x['name'] for x in data["streaming"]])}
    """
    if synopsis:
        anime_description += f"""
    Synopsis: {data["synopsis"]}
    """

    return anime_description

@mcp.tool()
async def get_episodes(id:int,num_episodes: int = 10, sort: str = "asc"):
    """
    Returns information about the episodes for an anime, user can request
    a certain amount of episodes.
    if user requests total number of episodes this can be derived from the
    highest ID of the episode on the last page - request just 1 record sorted desc

    ID: MAL ID of the anime (can be retrieved from get_anime)
    num_episodes: How many episodes to retrieve
    """
    url = f"{NWS_API_BASE}anime/{id}/episodes"

    response = await call_jikan(url)
    if not response["data"]:
        return response

    last_page = response["pagination"]["last_visible_page"]
    episodes_from_page0 = response["data"]

    last_visited_page = 0
    episodes = []
    while num_episodes != len(episodes):
        if response["pagination"]["has_next_page"]:
            if sort == "desc":
                if last_visited_page == 1:
                    episodes.extend(episodes_from_page0)
                    break
                url = url + f"?page={last_page if last_visited_page == 0 else last_visited_page-1}"
            else:
                url = url + f"?page={last_visited_page + 1}"

            response = await call_jikan(url)
            if not response["data"]:
                return response + "; issue with pagination"
            episodes.extend(response["data"])
        else:
            episodes.extend(response["data"])
            break

    if sort == "desc":
        episodes = sorted(episodes, key=lambda x: x["mal_id"], reverse=True)

    episodes = [format_episode(epi) for epi in episodes[:num_episodes]]
    return "\n---\n".join(episodes)

@mcp.tool()
async def get_episode(anime_id: int, id: int) -> str:
    """Get the synopsis of a particular episode
    anime_id is MAL ID which can be retrieved from get_anime or it is also
    used as one of the params for get_episodes tool.
    ID is MAL ID which can be retrieved from get_episodes tool.
    """
    url = f"{NWS_API_BASE}anime/{anime_id}/episodes/{id}"

    response = await call_jikan(url)
    if not response["data"]:
        return response

    return f"""
    Synopsis: {response["data"]["synopsis"]}
    """

async def call_jikan(url):
    response = await make_jikan_request(url)
    if not response or "data" not in response:
        return "Unable to fetch anime or anime not found."

    if not response["data"]:
        return f"Data couldn't be fetched for anime"
    return response

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')