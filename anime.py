import os
import random
import re

import requests

TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
TMDB_API_KEY = os.getenv("MOVIE_API")
TMDB_BASE = "https://api.themoviedb.org/3"
_cfg = None


# make a call to the TMDB API
def tmdb(path, **params):
    if not TMDB_API_KEY:
        return None
    params["api_key"] = TMDB_API_KEY
    r = requests.get(f"{TMDB_BASE}{path}", params=params, timeout=10)
    return r.json() if r.ok else None


def img_url(kind, prefer, file_path):
    global _cfg
    if not file_path:
        return None
    if _cfg is None:
        _cfg = tmdb("/configuration") or {}
    imgs = _cfg.get("images") or {}
    base = imgs.get("secure_base_url") or imgs.get("base_url")
    if not base:
        return None
    sizes = imgs.get(f"{kind}_sizes") or []
    size = prefer if prefer in sizes else ("original" if "original" in sizes else (sizes[-1] if sizes else "original"))
    return f"{base}{size}{file_path}"


def queries(title):
    t = title.strip()
    return [t] + ([re.sub(r"\s+2$", "", t)] if re.search(r"\s+2$", t) else [])


def pick(items):
    return random.choice(items).get("file_path") if items else None


MAL_CLIENT_ID = os.getenv("MAL_CLIENT_ID")


def get_mal_synonyms(name):
    r = requests.get(
        "https://api.myanimelist.net/v2/anime",
        params={"q": name, "limit": 1, "fields": "alternative_titles"},
        headers={"X-MAL-CLIENT-ID": MAL_CLIENT_ID},
        timeout=5
    )
    if r.status_code != 200:
        return []

    results = r.json().get("data") or []
    if not results:
        return []

    anime = results[0]["node"]
    alt = anime.get("alternative_titles", {})
    titles = [anime.get("title", "")]
    if alt.get("en"): titles.append(alt["en"])
    if alt.get("ja"): titles.append(alt["ja"])
    titles += alt.get("synonyms", [])

    return titles


def get_anime_screenshot(title):
    # try show
    for q in queries(title):
        for s in (tmdb("/search/tv", query=q, language="en-US", include_adult="true", page=1) or {}).get("results") or []:
            seasons = [s for s in (tmdb(f"/tv/{s['id']}", language="en-US") or {}).get("seasons") or []
                       if s.get("season_number") is not None and (s.get("episode_count") or 0) > 0]
            if not seasons:
                continue
            for _ in range(12):
                sn = random.choice(seasons)
                stills = (tmdb(f"/tv/{s['id']}/season/{sn['season_number']}/episode/{random.randint(1, sn['episode_count'])}/images") or {}).get("stills") or []
                url = img_url("still", "w780", pick(stills))
                if url:
                    return url
            break

    # try movie
    for q in queries(title):
        for m in (tmdb("/search/movie", query=q, language="en-US", include_adult="true", page=1) or {}).get("results") or []:
            imgs = tmdb(f"/movie/{m['id']}/images") or {}
            for kind, prefer in [("backdrop", "w780"), ("poster", "w500")]:
                url = img_url(kind, prefer, pick(imgs.get(f"{kind}s") or []))
                if url:
                    return url
            break

    return None

def get_anilist_list(username, media_type="ANIME"):
    query = '''
    query ($name: String, $type: MediaType) {
        MediaListCollection(userName: $name, type: $type) {
            lists {
                name
                entries {
                    score
                    progress
                    media {
                        title {
                            english
                            romaji
                        }
                        episodes
                        chapters
                    }
                }
            }
        }
    }
    '''

    variables = {'name': username, 'type': media_type}

    response = requests.post(
        'https://graphql.anilist.co',
        json={'query': query, 'variables': variables}
    )

    if response.status_code != 200:
        return None

    shows = {}
    data = response.json()
    data_lists = data['data']['MediaListCollection']['lists'][0]['entries']

    for entry in data_lists:
        media = entry['media']
        title = media['title']
        primary = title.get('english') or title.get('romaji')
        alt_titles = set()
        for t in title.values():
            if t:
                alt_titles.add(t)
        shows[primary] = list(alt_titles)

    return shows