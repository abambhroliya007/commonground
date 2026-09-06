from __future__ import annotations

import os
import random

from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)

from typing import (
    Any,
    Literal,
)

import requests

from dotenv import (
    load_dotenv,
)


load_dotenv()


ContentType = Literal[
    "movie",
    "show",
]


TMDB_BASE_URL = (
    "https://api.themoviedb.org/3"
)

TMDB_API_KEY = os.getenv(
    "TMDB_API_KEY"
)

TMDB_ACCESS_TOKEN = os.getenv(
    "TMDB_ACCESS_TOKEN"
)


# ---------------------------------------------------------
# MOVIE GENRES
# ---------------------------------------------------------

MOVIE_GENRE_MAP = {
    "action":
        28,

    "adventure":
        12,

    "animation":
        16,

    "comedy":
        35,

    "crime":
        80,

    "documentary":
        99,

    "drama":
        18,

    "family":
        10751,

    "fantasy":
        14,

    "history":
        36,

    "horror":
        27,

    "music":
        10402,

    "mystery":
        9648,

    "romance":
        10749,

    "science fiction":
        878,

    "sci-fi":
        878,

    "science-fiction":
        878,

    "thriller":
        53,

    "war":
        10752,

    "western":
        37,
}


# ---------------------------------------------------------
# TV GENRES
# ---------------------------------------------------------

TV_GENRE_MAP = {
    "action":
        10759,

    "adventure":
        10759,

    "action & adventure":
        10759,

    "animation":
        16,

    "comedy":
        35,

    "crime":
        80,

    "documentary":
        99,

    "drama":
        18,

    "family":
        10751,

    "kids":
        10762,

    "mystery":
        9648,

    "news":
        10763,

    "reality":
        10764,

    "science fiction":
        10765,

    "sci-fi":
        10765,

    "fantasy":
        10765,

    "sci-fi & fantasy":
        10765,

    "soap":
        10766,

    "talk":
        10767,

    "war":
        10768,

    "politics":
        10768,

    "war & politics":
        10768,

    "western":
        37,
}


MOVIE_GENRE_NAMES = {
    28:
        "Action",

    12:
        "Adventure",

    16:
        "Animation",

    35:
        "Comedy",

    80:
        "Crime",

    99:
        "Documentary",

    18:
        "Drama",

    10751:
        "Family",

    14:
        "Fantasy",

    36:
        "History",

    27:
        "Horror",

    10402:
        "Music",

    9648:
        "Mystery",

    10749:
        "Romance",

    878:
        "Science Fiction",

    53:
        "Thriller",

    10752:
        "War",

    37:
        "Western",
}


TV_GENRE_NAMES = {
    10759:
        "Action & Adventure",

    16:
        "Animation",

    35:
        "Comedy",

    80:
        "Crime",

    99:
        "Documentary",

    18:
        "Drama",

    10751:
        "Family",

    10762:
        "Kids",

    9648:
        "Mystery",

    10763:
        "News",

    10764:
        "Reality",

    10765:
        "Sci-Fi & Fantasy",

    10766:
        "Soap",

    10767:
        "Talk",

    10768:
        "War & Politics",

    37:
        "Western",
}


SORT_STRATEGIES = [
    "popularity.desc",
    "vote_average.desc",
    "vote_count.desc",
]


ERA_RANGES = [
    (
        1980,
        1999,
    ),

    (
        2000,
        2009,
    ),

    (
        2010,
        2019,
    ),

    (
        2020,
        2026,
    ),
]


# ---------------------------------------------------------
# AUTH
# ---------------------------------------------------------

def _headers() -> dict[
    str,
    str,
]:
    headers = {
        "accept":
            "application/json",
    }

    if (
        TMDB_ACCESS_TOKEN
    ):
        headers[
            "Authorization"
        ] = (
            f"Bearer "
            f"{TMDB_ACCESS_TOKEN}"
        )

    return headers


def _auth_params() -> dict[
    str,
    str,
]:
    if (
        TMDB_ACCESS_TOKEN
    ):
        return {}

    if (
        TMDB_API_KEY
    ):
        return {
            "api_key":
                TMDB_API_KEY
        }

    raise RuntimeError(
        "TMDB credentials are missing. "
        "Set TMDB_ACCESS_TOKEN or "
        "TMDB_API_KEY in backend/.env."
    )


# ---------------------------------------------------------
# REQUEST
# ---------------------------------------------------------

def _get(
    path: str,

    *,

    params:
        dict[
            str,
            Any,
        ]
        | None = None,
) -> dict[
    str,
    Any,
]:

    request_params = {
        **_auth_params(),

        **(
            params
            or {}
        ),
    }

    response = (
        requests.get(
            f"{TMDB_BASE_URL}{path}",

            params=
                request_params,

            headers=
                _headers(),

            timeout=
                10,
        )
    )

    response.raise_for_status()

    return response.json()


# ---------------------------------------------------------
# GENRES
# ---------------------------------------------------------

def genre_names_to_ids(
    genres:
        list[str]
        | None,

    content_type:
        ContentType,
) -> list[int]:

    if not genres:
        return []

    genre_map = (
        MOVIE_GENRE_MAP
        if content_type ==
        "movie"
        else
        TV_GENRE_MAP
    )

    ids = []

    for genre in genres:
        normalized = (
            str(
                genre
            )
            .strip()
            .lower()
        )

        genre_id = (
            genre_map.get(
                normalized
            )
        )

        if (
            genre_id
            and genre_id
            not in ids
        ):
            ids.append(
                genre_id
            )

    return ids


def genre_ids_to_names(
    ids:
        list[int]
        | None,

    content_type:
        ContentType,
) -> list[str]:

    if not ids:
        return []

    genre_map = (
        MOVIE_GENRE_NAMES
        if content_type ==
        "movie"
        else
        TV_GENRE_NAMES
    )

    return [
        genre_map.get(
            genre_id,
            f"Genre {genre_id}",
        )

        for genre_id
        in ids
    ]


# ---------------------------------------------------------
# DISCOVERY
# ---------------------------------------------------------

def discover_content(
    *,

    content_type:
        ContentType,

    preferred_genres:
        list[str]
        | None = None,

    avoid_genres:
        list[str]
        | None = None,

    max_runtime:
        int
        | None = None,

    page:
        int
        | None = None,

    sort_by:
        str
        | None = None,

    release_year_min:
        int
        | None = None,

    release_year_max:
        int
        | None = None,
) -> list[
    dict[
        str,
        Any,
    ]
]:

    preferred_ids = (
        genre_names_to_ids(
            preferred_genres,

            content_type,
        )
    )

    avoid_ids = (
        genre_names_to_ids(
            avoid_genres,

            content_type,
        )
    )

    params: dict[
        str,
        Any,
    ] = {
        "language":
            "en-US",

        "include_adult":
            "false",

        "sort_by":
            sort_by
            or random.choice(
                SORT_STRATEGIES
            ),

        "vote_count.gte":
            100,

        "page":
            page
            or random.randint(
                1,
                3,
            ),
    }

    if (
        content_type ==
        "movie"
    ):
        params[
            "include_video"
        ] = "false"

    if (
        preferred_ids
    ):
        params[
            "with_genres"
        ] = "|".join(
            str(
                genre_id
            )

            for genre_id
            in preferred_ids
        )

    if (
        avoid_ids
    ):
        params[
            "without_genres"
        ] = ",".join(
            str(
                genre_id
            )

            for genre_id
            in avoid_ids
        )

    if (
        max_runtime
    ):
        params[
            "with_runtime.lte"
        ] = max_runtime

    if (
        content_type ==
        "movie"
    ):
        min_date_key = (
            "primary_release_date.gte"
        )

        max_date_key = (
            "primary_release_date.lte"
        )

        endpoint = (
            "/discover/movie"
        )

    else:
        min_date_key = (
            "first_air_date.gte"
        )

        max_date_key = (
            "first_air_date.lte"
        )

        endpoint = (
            "/discover/tv"
        )

    if (
        release_year_min
    ):
        params[
            min_date_key
        ] = (
            f"{release_year_min}"
            "-01-01"
        )

    if (
        release_year_max
    ):
        params[
            max_date_key
        ] = (
            f"{release_year_max}"
            "-12-31"
        )

    data = _get(
        endpoint,

        params=
            params,
    )

    return (
        data.get(
            "results",
            [],
        )
        or []
    )


# ---------------------------------------------------------
# DETAILS
# ---------------------------------------------------------

def get_content_details(
    content_id:
        int,

    content_type:
        ContentType,
) -> dict[
    str,
    Any,
]:

    endpoint = (
        f"/movie/{content_id}"
        if content_type ==
        "movie"
        else
        f"/tv/{content_id}"
    )

    return _get(
        endpoint,

        params={
            "language":
                "en-US",
        },
    )


# ---------------------------------------------------------
# NORMALIZE
# ---------------------------------------------------------

def _normalize_content(
    raw:
        dict[
            str,
            Any,
        ],

    content_type:
        ContentType,
) -> dict[
    str,
    Any,
]:

    content_id = (
        raw.get(
            "id"
        )
    )

    if (
        not content_id
    ):
        return raw

    try:
        details = (
            get_content_details(
                int(
                    content_id
                ),

                content_type,
            )
        )

    except (
        requests.RequestException,
        ValueError,
    ):
        details = {}

    merged = {
        **raw,
        **details,
    }


    # GENRES

    if (
        isinstance(
            merged.get(
                "genres"
            ),
            list,
        )
        and merged.get(
            "genres"
        )
        and isinstance(
            merged[
                "genres"
            ][0],
            dict,
        )
    ):
        genres = [
            genre.get(
                "name",
                "",
            )

            for genre
            in merged[
                "genres"
            ]

            if genre.get(
                "name"
            )
        ]

    else:
        genres = (
            genre_ids_to_names(
                raw.get(
                    "genre_ids",
                    [],
                ),

                content_type,
            )
        )


    # MOVIE

    if (
        content_type ==
        "movie"
    ):
        title = (
            merged.get(
                "title"
            )
            or merged.get(
                "original_title"
            )
            or "Untitled"
        )

        release_date = (
            merged.get(
                "release_date"
            )
            or ""
        )

        runtime = (
            merged.get(
                "runtime"
            )
        )

        number_of_seasons = (
            None
        )

        number_of_episodes = (
            None
        )


    # SHOW

    else:
        title = (
            merged.get(
                "name"
            )
            or merged.get(
                "original_name"
            )
            or "Untitled"
        )

        release_date = (
            merged.get(
                "first_air_date"
            )
            or ""
        )

        episode_runtime = (
            merged.get(
                "episode_run_time"
            )
            or []
        )

        runtime = (
            episode_runtime[0]
            if (
                isinstance(
                    episode_runtime,
                    list,
                )
                and episode_runtime
            )
            else
            None
        )

        number_of_seasons = (
            merged.get(
                "number_of_seasons"
            )
        )

        number_of_episodes = (
            merged.get(
                "number_of_episodes"
            )
        )


    release_year = None

    if (
        isinstance(
            release_date,
            str,
        )
        and len(
            release_date
        ) >= 4
    ):
        try:
            release_year = (
                int(
                    release_date[
                        :4
                    ]
                )
            )

        except ValueError:
            release_year = (
                None
            )


    return {
        **merged,

        "id":
            int(
                content_id
            ),

        "title":
            title,

        "content_type":
            content_type,

        "release_date":
            release_date,

        "release_year":
            release_year,

        "runtime":
            runtime,

        "genres":
            genres,

        "poster_path":
            merged.get(
                "poster_path"
            ),

        "overview":
            merged.get(
                "overview",
                "",
            ),

        "vote_average":
            merged.get(
                "vote_average",
                0,
            ),

        "vote_count":
            merged.get(
                "vote_count",
                0,
            ),

        "number_of_seasons":
            number_of_seasons,

        "number_of_episodes":
            number_of_episodes,
    }


# ---------------------------------------------------------
# DEDUPLICATE
# ---------------------------------------------------------

def _deduplicate(
    items:
        list[
            dict[
                str,
                Any,
            ]
        ],
) -> list[
    dict[
        str,
        Any,
    ]
]:

    unique = []

    seen_ids = set()

    for item in items:
        content_id = (
            item.get(
                "id"
            )
        )

        if (
            not content_id
        ):
            continue

        try:
            content_id = (
                int(
                    content_id
                )
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

        if (
            content_id
            in seen_ids
        ):
            continue

        seen_ids.add(
            content_id
        )

        unique.append(
            item
        )

    return unique


# ---------------------------------------------------------
# PARALLEL DETAILS
# ---------------------------------------------------------

def _fetch_details(
    items:
        list[
            dict[
                str,
                Any,
            ]
        ],

    content_type:
        ContentType,

    max_workers:
        int = 8,
) -> list[
    dict[
        str,
        Any,
    ]
]:

    if not items:
        return []

    normalized = []

    with ThreadPoolExecutor(
        max_workers=
            max_workers
    ) as executor:

        futures = {
            executor.submit(
                _normalize_content,

                item,

                content_type,
            ):
                item

            for item
            in items
        }

        for future in (
            as_completed(
                futures
            )
        ):
            try:
                normalized.append(
                    future.result()
                )

            except Exception as exc:
                print(
                    "[TMDB details] "
                    f"Failed: {exc}"
                )

    return normalized


# ---------------------------------------------------------
# PUBLIC CANDIDATE SEARCH
# ---------------------------------------------------------

def get_candidate_movies(
    *,

    content_type:
        ContentType = "movie",

    preferred_genres:
        list[str]
        | None = None,

    avoid_genres:
        list[str]
        | None = None,

    max_runtime:
        int
        | None = None,

    limit:
        int = 28,
) -> list[
    dict[
        str,
        Any,
    ]
]:

    raw_candidates = []

    strategies = (
        SORT_STRATEGIES.copy()
    )

    random.shuffle(
        strategies
    )


    # GENERAL SEARCH

    for sort_by in (
        strategies[:2]
    ):
        try:
            results = (
                discover_content(
                    content_type=
                        content_type,

                    preferred_genres=
                        preferred_genres,

                    avoid_genres=
                        avoid_genres,

                    max_runtime=
                        max_runtime,

                    page=
                        random.randint(
                            1,
                            3,
                        ),

                    sort_by=
                        sort_by,
                )
            )

            raw_candidates.extend(
                results[:14]
            )

        except requests.RequestException as exc:
            print(
                "[TMDB discovery] "
                f"General search failed: {exc}"
            )


    # ERA SEARCH

    eras = (
        ERA_RANGES.copy()
    )

    random.shuffle(
        eras
    )

    for (
        start_year,
        end_year,
    ) in (
        eras[:3]
    ):
        try:
            results = (
                discover_content(
                    content_type=
                        content_type,

                    preferred_genres=
                        preferred_genres,

                    avoid_genres=
                        avoid_genres,

                    max_runtime=
                        max_runtime,

                    page=
                        1,

                    sort_by=
                        random.choice(
                            [
                                "vote_average.desc",
                                "popularity.desc",
                            ]
                        ),

                    release_year_min=
                        start_year,

                    release_year_max=
                        end_year,
                )
            )

            random.shuffle(
                results
            )

            raw_candidates.extend(
                results[:5]
            )

        except requests.RequestException as exc:
            print(
                "[TMDB discovery] "
                f"Era search failed: {exc}"
            )


    unique = (
        _deduplicate(
            raw_candidates
        )
    )

    random.shuffle(
        unique
    )


    # QUALITY ORDER

    quality_sorted = (
        sorted(
            unique,

            key=lambda item: (
                float(
                    item.get(
                        "vote_average",
                        0,
                    )
                    or 0
                )
                * 0.65
            )
            +
            (
                min(
                    float(
                        item.get(
                            "vote_count",
                            0,
                        )
                        or 0
                    ),

                    5000,
                )
                / 5000
                * 3.5
            ),

            reverse=True,
        )
    )


    quality_target = (
        max(
            8,

            limit // 2,
        )
    )

    selected = []

    selected_ids = set()


    for item in (
        quality_sorted[
            :quality_target
        ]
    ):
        item_id = (
            item.get(
                "id"
            )
        )

        if (
            not item_id
        ):
            continue

        item_id = int(
            item_id
        )

        if (
            item_id
            in selected_ids
        ):
            continue

        selected_ids.add(
            item_id
        )

        selected.append(
            item
        )


    shuffled = (
        unique.copy()
    )

    random.shuffle(
        shuffled
    )

    for item in shuffled:
        if (
            len(
                selected
            ) >=
            limit
        ):
            break

        item_id = (
            item.get(
                "id"
            )
        )

        if (
            not item_id
        ):
            continue

        item_id = (
            int(
                item_id
            )
        )

        if (
            item_id
            in selected_ids
        ):
            continue

        selected_ids.add(
            item_id
        )

        selected.append(
            item
        )


    normalized = (
        _fetch_details(
            selected,

            content_type,
        )
    )

    random.shuffle(
        normalized
    )

    return normalized