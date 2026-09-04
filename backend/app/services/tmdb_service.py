from __future__ import annotations

import os
import random
from concurrent.futures import (
    ThreadPoolExecutor,
    as_completed,
)
from typing import Any

import requests
from dotenv import load_dotenv


load_dotenv()


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
# GENRES
# ---------------------------------------------------------

GENRE_MAP = {
    "action": 28,
    "adventure": 12,
    "animation": 16,
    "comedy": 35,
    "crime": 80,
    "documentary": 99,
    "drama": 18,
    "family": 10751,
    "fantasy": 14,
    "history": 36,
    "horror": 27,
    "music": 10402,
    "mystery": 9648,
    "romance": 10749,
    "science fiction": 878,
    "sci-fi": 878,
    "science-fiction": 878,
    "tv movie": 10770,
    "thriller": 53,
    "war": 10752,
    "western": 37,
}


GENRE_ID_TO_NAME = {
    genre_id:
        genre_name.title()
    for (
        genre_name,
        genre_id,
    )
    in GENRE_MAP.items()
}

GENRE_ID_TO_NAME[878] = (
    "Science Fiction"
)


# ---------------------------------------------------------
# DISCOVERY CONFIGURATION
# ---------------------------------------------------------

SORT_STRATEGIES = [
    "popularity.desc",
    "vote_average.desc",
    "vote_count.desc",
]


ERA_RANGES = [
    (1980, 1999),
    (2000, 2009),
    (2010, 2019),
    (2020, 2026),
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

    if TMDB_ACCESS_TOKEN:
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
    if TMDB_ACCESS_TOKEN:
        return {}

    if TMDB_API_KEY:
        return {
            "api_key":
                TMDB_API_KEY,
        }

    raise RuntimeError(
        "TMDB credentials are missing. "
        "Set TMDB_ACCESS_TOKEN or "
        "TMDB_API_KEY in backend/.env."
    )


# ---------------------------------------------------------
# BASE REQUEST
# ---------------------------------------------------------

def _get(
    path: str,
    *,
    params: dict[
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

    response = requests.get(
        f"{TMDB_BASE_URL}{path}",
        params=request_params,
        headers=_headers(),
        timeout=10,
    )

    response.raise_for_status()

    return response.json()


# ---------------------------------------------------------
# GENRE HELPERS
# ---------------------------------------------------------

def genre_names_to_ids(
    genres: list[str]
    | None,
) -> list[int]:
    if not genres:
        return []

    ids: list[int] = []

    for genre in genres:
        normalized = (
            genre
            .strip()
            .lower()
        )

        genre_id = (
            GENRE_MAP.get(
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
    ids: list[int]
    | None,
) -> list[str]:
    if not ids:
        return []

    return [
        GENRE_ID_TO_NAME.get(
            genre_id,
            f"Genre {genre_id}",
        )
        for genre_id
        in ids
    ]


# ---------------------------------------------------------
# DISCOVERY
# ---------------------------------------------------------

def discover_movies(
    *,
    preferred_genres: list[str]
    | None = None,
    avoid_genres: list[str]
    | None = None,
    max_runtime: int
    | None = None,
    page: int
    | None = None,
    sort_by: str
    | None = None,
    release_year_min: int
    | None = None,
    release_year_max: int
    | None = None,
) -> list[
    dict[
        str,
        Any,
    ]
]:
    preferred_ids = (
        genre_names_to_ids(
            preferred_genres
        )
    )

    avoid_ids = (
        genre_names_to_ids(
            avoid_genres
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

        "include_video":
            "false",

        "sort_by":
            (
                sort_by
                or random.choice(
                    SORT_STRATEGIES
                )
            ),

        # Enough votes to avoid junk,
        # but low enough to include
        # older and less obvious films.
        "vote_count.gte":
            100,

        "page":
            (
                page
                or random.randint(
                    1,
                    3,
                )
            ),
    }

    if preferred_ids:
        # "|" means OR.
        #
        # Example:
        # mystery OR sci-fi OR thriller
        #
        # This gives us more genre variety
        # than requiring every genre at once.
        params[
            "with_genres"
        ] = "|".join(
            str(
                genre_id
            )
            for genre_id
            in preferred_ids
        )

    if avoid_ids:
        params[
            "without_genres"
        ] = ",".join(
            str(
                genre_id
            )
            for genre_id
            in avoid_ids
        )

    if max_runtime:
        params[
            "with_runtime.lte"
        ] = max_runtime

    if release_year_min:
        params[
            "primary_release_date.gte"
        ] = (
            f"{release_year_min}"
            "-01-01"
        )

    if release_year_max:
        params[
            "primary_release_date.lte"
        ] = (
            f"{release_year_max}"
            "-12-31"
        )

    data = _get(
        "/discover/movie",
        params=params,
    )

    return data.get(
        "results",
        [],
    )


# ---------------------------------------------------------
# DETAILS
# ---------------------------------------------------------

def get_movie_details(
    movie_id: int,
) -> dict[
    str,
    Any,
]:
    return _get(
        f"/movie/{movie_id}",
        params={
            "language":
                "en-US",
        },
    )


# ---------------------------------------------------------
# NORMALIZATION
# ---------------------------------------------------------

def _normalize_movie(
    raw: dict[
        str,
        Any,
    ],
) -> dict[
    str,
    Any,
]:
    movie_id = raw.get(
        "id"
    )

    if not movie_id:
        return raw

    try:
        details = (
            get_movie_details(
                int(
                    movie_id
                )
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

    # -----------------------------------------------------
    # GENRES
    # -----------------------------------------------------

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
                )
            )
        )

    # -----------------------------------------------------
    # RELEASE YEAR
    # -----------------------------------------------------

    release_date = (
        merged.get(
            "release_date"
        )
        or ""
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
            release_year = int(
                release_date[
                    :4
                ]
            )

        except ValueError:
            release_year = None

    return {
        **merged,

        "genres":
            genres,

        "release_year":
            release_year,

        "runtime":
            merged.get(
                "runtime"
            ),
    }


# ---------------------------------------------------------
# DEDUPLICATION
# ---------------------------------------------------------

def _deduplicate_movies(
    movies: list[
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
    unique: list[
        dict[
            str,
            Any,
        ]
    ] = []

    seen_ids: set[int] = (
        set()
    )

    for movie in movies:
        movie_id = movie.get(
            "id"
        )

        if not movie_id:
            continue

        try:
            normalized_id = int(
                movie_id
            )

        except (
            TypeError,
            ValueError,
        ):
            continue

        if (
            normalized_id
            in seen_ids
        ):
            continue

        seen_ids.add(
            normalized_id
        )

        unique.append(
            movie
        )

    return unique


# ---------------------------------------------------------
# FAST CONCURRENT DETAIL FETCH
# ---------------------------------------------------------

def _fetch_movie_details_concurrently(
    movies: list[
        dict[
            str,
            Any,
        ]
    ],
    *,
    max_workers: int = 8,
) -> list[
    dict[
        str,
        Any,
    ]
]:
    if not movies:
        return []

    normalized: list[
        dict[
            str,
            Any,
        ]
    ] = []

    with ThreadPoolExecutor(
        max_workers=max_workers
    ) as executor:
        future_map = {
            executor.submit(
                _normalize_movie,
                movie,
            ):
                movie

            for movie
            in movies
        }

        for future in as_completed(
            future_map
        ):
            try:
                normalized.append(
                    future.result()
                )

            except Exception:
                # One broken TMDB movie
                # should not fail the
                # entire recommendation.
                continue

    return normalized


# ---------------------------------------------------------
# CANDIDATE POOL
# ---------------------------------------------------------

def get_candidate_movies(
    *,
    preferred_genres: list[str]
    | None = None,
    avoid_genres: list[str]
    | None = None,
    max_runtime: int
    | None = None,
    limit: int = 28,
) -> list[
    dict[
        str,
        Any,
    ]
]:
    """
    Build a diverse but fast candidate pool.

    Goals:
        - maintain genre diversity
        - maintain timeline diversity
        - change results between runs
        - avoid excessive TMDB requests
        - keep response time reasonable

    Typical output:
        ~20-28 enriched movie candidates
    """

    raw_candidates: list[
        dict[
            str,
            Any,
        ]
    ] = []

    # -----------------------------------------------------
    # 1. GENERAL DISCOVERY
    # -----------------------------------------------------

    strategies = (
        SORT_STRATEGIES.copy()
    )

    random.shuffle(
        strategies
    )

    # Only TWO general searches.
    #
    # Previous version did more,
    # which increased latency.
    for sort_by in strategies[:2]:
        try:
            movies = (
                discover_movies(
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
                movies[:14]
            )

        except (
            requests.RequestException
        ):
            continue

    # -----------------------------------------------------
    # 2. TIMELINE DIVERSITY
    # -----------------------------------------------------

    era_ranges = (
        ERA_RANGES.copy()
    )

    random.shuffle(
        era_ranges
    )

    # Use THREE out of four era buckets.
    #
    # This creates year variety but saves
    # one whole TMDB request each run.
    for (
        start_year,
        end_year,
    ) in era_ranges[:3]:
        try:
            movies = (
                discover_movies(
                    preferred_genres=
                        preferred_genres,

                    avoid_genres=
                        avoid_genres,

                    max_runtime=
                        max_runtime,

                    page=1,

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
                movies
            )

            # Only keep a few from
            # each decade bucket.
            raw_candidates.extend(
                movies[:5]
            )

        except (
            requests.RequestException
        ):
            continue

    # -----------------------------------------------------
    # 3. DEDUPLICATE
    # -----------------------------------------------------

    unique = (
        _deduplicate_movies(
            raw_candidates
        )
    )

    # Randomize before trimming so
    # repeated prompts do not always
    # feed the exact same movies
    # downstream.
    random.shuffle(
        unique
    )

    # -----------------------------------------------------
    # 4. QUALITY-AWARE PRESELECTION
    # -----------------------------------------------------

    # We still want some popular /
    # well-rated movies represented.
    #
    # Half are chosen randomly.
    # Half favor quality.
    quality_sorted = sorted(
        unique,
        key=lambda movie: (
            float(
                movie.get(
                    "vote_average",
                    0,
                )
                or 0
            )
            * 0.65
        )
        + (
            min(
                float(
                    movie.get(
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

    quality_target = (
        max(
            8,
            limit // 2,
        )
    )

    selected: list[
        dict[
            str,
            Any,
        ]
    ] = []

    selected_ids: set[int] = (
        set()
    )

    # -----------------------------------------------------
    # QUALITY HALF
    # -----------------------------------------------------

    for movie in quality_sorted[
        :quality_target
    ]:
        movie_id = movie.get(
            "id"
        )

        if not movie_id:
            continue

        movie_id = int(
            movie_id
        )

        if (
            movie_id
            in selected_ids
        ):
            continue

        selected_ids.add(
            movie_id
        )

        selected.append(
            movie
        )

    # -----------------------------------------------------
    # RANDOM / DIVERSE HALF
    # -----------------------------------------------------

    shuffled_unique = (
        unique.copy()
    )

    random.shuffle(
        shuffled_unique
    )

    for movie in shuffled_unique:
        if (
            len(
                selected
            )
            >= limit
        ):
            break

        movie_id = movie.get(
            "id"
        )

        if not movie_id:
            continue

        movie_id = int(
            movie_id
        )

        if (
            movie_id
            in selected_ids
        ):
            continue

        selected_ids.add(
            movie_id
        )

        selected.append(
            movie
        )

    # -----------------------------------------------------
    # 5. FETCH DETAILS IN PARALLEL
    # -----------------------------------------------------

    normalized = (
        _fetch_movie_details_concurrently(
            selected,
            max_workers=8,
        )
    )

    # -----------------------------------------------------
    # 6. FINAL SHUFFLE
    # -----------------------------------------------------

    # Recommendation service handles
    # the actual scoring.
    #
    # We do not want ordering from TMDB
    # to accidentally bias it.
    random.shuffle(
        normalized
    )

    return normalized