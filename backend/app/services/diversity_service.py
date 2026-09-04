from __future__ import annotations

import math
import random
from collections import Counter
from typing import Any


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------

DEFAULT_RESULT_COUNT = 6

# How much variety matters compared with raw group score.
# Keep these relatively small so a 95% match does not lose
# to a mediocre movie purely because it is different.
GENRE_DIVERSITY_WEIGHT = 7.0
ERA_DIVERSITY_WEIGHT = 6.0
NOVELTY_WEIGHT = 8.0

# Small random variation among otherwise strong candidates.
RANDOMNESS_WEIGHT = 4.5

# Movies within this many points of the strongest candidate
# are treated as being in a similarly strong neighborhood.
QUALITY_WINDOW = 16


# ---------------------------------------------------------
# BASIC HELPERS
# ---------------------------------------------------------

def _safe_int(
    value: Any,
    default: int = 0,
) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _movie_id(movie: dict[str, Any]) -> int:
    return _safe_int(
        movie.get("id"),
        0,
    )


def _group_score(
    movie: dict[str, Any],
) -> float:
    return _safe_float(
        movie.get(
            "group_score",
            movie.get(
                "score",
                0,
            ),
        ),
        0.0,
    )


def _release_year(
    movie: dict[str, Any],
) -> int | None:
    year = movie.get(
        "release_year"
    )

    if year:
        parsed = _safe_int(
            year,
            0,
        )

        if parsed > 1800:
            return parsed

    release_date = movie.get(
        "release_date"
    )

    if (
        isinstance(
            release_date,
            str,
        )
        and len(
            release_date
        ) >= 4
    ):
        parsed = _safe_int(
            release_date[:4],
            0,
        )

        if parsed > 1800:
            return parsed

    return None


def _genres(
    movie: dict[str, Any],
) -> set[str]:
    raw_genres = movie.get(
        "genres",
        [],
    )

    names: set[str] = set()

    if isinstance(
        raw_genres,
        list,
    ):
        for genre in raw_genres:
            if isinstance(
                genre,
                str,
            ):
                cleaned = (
                    genre
                    .strip()
                    .lower()
                )

                if cleaned:
                    names.add(
                        cleaned
                    )

            elif isinstance(
                genre,
                dict,
            ):
                name = genre.get(
                    "name"
                )

                if isinstance(
                    name,
                    str,
                ):
                    cleaned = (
                        name
                        .strip()
                        .lower()
                    )

                    if cleaned:
                        names.add(
                            cleaned
                        )

    return names


# ---------------------------------------------------------
# ERA HANDLING
# ---------------------------------------------------------

def get_era(
    movie: dict[str, Any],
) -> str:
    year = _release_year(
        movie
    )

    if year is None:
        return "unknown"

    if year < 1990:
        return "classic"

    if year < 2000:
        return "90s"

    if year < 2010:
        return "2000s"

    if year < 2020:
        return "2010s"

    return "2020s"


# ---------------------------------------------------------
# GENRE SIMILARITY
# ---------------------------------------------------------

def genre_similarity(
    first: dict[str, Any],
    second: dict[str, Any],
) -> float:
    first_genres = _genres(
        first
    )

    second_genres = _genres(
        second
    )

    if (
        not first_genres
        or not second_genres
    ):
        return 0.0

    intersection = len(
        first_genres
        & second_genres
    )

    union = len(
        first_genres
        | second_genres
    )

    if union == 0:
        return 0.0

    return (
        intersection
        / union
    )


# ---------------------------------------------------------
# DIVERSITY BONUSES
# ---------------------------------------------------------

def _genre_diversity_bonus(
    movie: dict[str, Any],
    selected: list[
        dict[str, Any]
    ],
) -> float:
    if not selected:
        return (
            GENRE_DIVERSITY_WEIGHT
            * 0.5
        )

    similarities = [
        genre_similarity(
            movie,
            other,
        )
        for other
        in selected
    ]

    highest_similarity = max(
        similarities,
        default=0.0,
    )

    # Completely different genres:
    # bonus approaches full weight.
    #
    # Identical genre sets:
    # bonus approaches zero.
    return (
        1.0
        - highest_similarity
    ) * GENRE_DIVERSITY_WEIGHT


def _era_diversity_bonus(
    movie: dict[str, Any],
    selected: list[
        dict[str, Any]
    ],
) -> float:
    if not selected:
        return (
            ERA_DIVERSITY_WEIGHT
            * 0.35
        )

    movie_era = get_era(
        movie
    )

    if movie_era == "unknown":
        return 0.0

    selected_eras = [
        get_era(
            other
        )
        for other
        in selected
    ]

    counts = Counter(
        selected_eras
    )

    if (
        movie_era
        not in counts
    ):
        return ERA_DIVERSITY_WEIGHT

    # Repeated eras remain allowed,
    # but get less of a bonus.
    repeated_count = counts[
        movie_era
    ]

    return (
        ERA_DIVERSITY_WEIGHT
        / (
            repeated_count
            + 2
        )
    )


def _novelty_bonus(
    movie: dict[str, Any],
    excluded_movie_ids: set[int],
) -> float:
    movie_id = _movie_id(
        movie
    )

    if (
        movie_id
        and movie_id
        in excluded_movie_ids
    ):
        return -NOVELTY_WEIGHT

    return (
        NOVELTY_WEIGHT
        * 0.25
    )


# ---------------------------------------------------------
# QUALITY GUARDRAIL
# ---------------------------------------------------------

def _quality_factor(
    movie: dict[str, Any],
    strongest_score: float,
) -> float:
    score = _group_score(
        movie
    )

    distance = (
        strongest_score
        - score
    )

    if distance <= 0:
        return 1.0

    if (
        distance
        >= QUALITY_WINDOW
    ):
        return 0.25

    return max(
        0.25,
        1.0
        - (
            distance
            / (
                QUALITY_WINDOW
                * 1.25
            )
        ),
    )


# ---------------------------------------------------------
# CONTROLLED RANDOMNESS
# ---------------------------------------------------------

def _random_bonus() -> float:
    # Triangular distribution keeps most random
    # values near the middle instead of producing
    # wild swings.
    return random.triangular(
        0.0,
        RANDOMNESS_WEIGHT,
        RANDOMNESS_WEIGHT
        * 0.55,
    )


# ---------------------------------------------------------
# MAIN DIVERSIFICATION
# ---------------------------------------------------------

def diversify_movies(
    movies: list[
        dict[str, Any]
    ],
    *,
    excluded_movie_ids: list[int]
    | None = None,
    limit: int = DEFAULT_RESULT_COUNT,
) -> list[
    dict[str, Any]
]:
    """
    Diversity-aware reranker.

    Priority order:
    1. Strong group compatibility
    2. Avoid recently shown movies
    3. Genre diversity
    4. Era diversity
    5. Controlled randomness

    It does NOT bypass whatever hard-constraint
    filtering happened earlier in the pipeline.
    """

    if not movies:
        return []

    excluded = {
        _safe_int(
            movie_id
        )
        for movie_id
        in (
            excluded_movie_ids
            or []
        )
        if _safe_int(
            movie_id
        )
    }

    # Remove accidental duplicates.
    unique_movies: list[
        dict[str, Any]
    ] = []

    seen_ids: set[int] = set()

    for movie in movies:
        movie_id = _movie_id(
            movie
        )

        if (
            movie_id
            and movie_id
            in seen_ids
        ):
            continue

        if movie_id:
            seen_ids.add(
                movie_id
            )

        unique_movies.append(
            movie
        )

    if not unique_movies:
        return []

    unique_movies.sort(
        key=_group_score,
        reverse=True,
    )

    strongest_score = (
        _group_score(
            unique_movies[0]
        )
    )

    selected: list[
        dict[str, Any]
    ] = []

    remaining = (
        unique_movies.copy()
    )

    while (
        remaining
        and len(
            selected
        ) < limit
    ):
        best_movie = None
        best_value = (
            -math.inf
        )

        for movie in remaining:
            raw_score = (
                _group_score(
                    movie
                )
            )

            quality = (
                _quality_factor(
                    movie,
                    strongest_score,
                )
            )

            genre_bonus = (
                _genre_diversity_bonus(
                    movie,
                    selected,
                )
            )

            era_bonus = (
                _era_diversity_bonus(
                    movie,
                    selected,
                )
            )

            novelty_bonus = (
                _novelty_bonus(
                    movie,
                    excluded,
                )
            )

            random_bonus = (
                _random_bonus()
            )

            diversity_total = (
                genre_bonus
                + era_bonus
                + novelty_bonus
                + random_bonus
            )

            # Diversity matters most when quality
            # is already reasonably close.
            final_value = (
                raw_score
                + (
                    diversity_total
                    * quality
                )
            )

            if (
                final_value
                > best_value
            ):
                best_value = (
                    final_value
                )

                best_movie = movie

        if best_movie is None:
            break

        selected.append(
            best_movie
        )

        remaining.remove(
            best_movie
        )

    return selected