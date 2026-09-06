from __future__ import annotations

from typing import Any


# ---------------------------------------------------------
# SAFE CONVERSION
# ---------------------------------------------------------

def _safe_float(
    value: Any,
    default: float | None = None,
) -> float | None:
    if value is None:
        return default

    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


def _safe_int(
    value: Any,
    default: int | None = None,
) -> int | None:
    number = _safe_float(
        value,
        None,
    )

    if number is None:
        return default

    try:
        return int(number)

    except (
        TypeError,
        ValueError,
        OverflowError,
    ):
        return default


def _normalize_string_list(
    value: Any,
) -> list[str]:
    if value is None:
        return []

    if isinstance(
        value,
        str,
    ):
        return [
            item.strip()
            for item
            in value.split(",")
            if item.strip()
        ]

    if isinstance(
        value,
        list,
    ):
        output: list[str] = []

        for item in value:
            if isinstance(
                item,
                str,
            ):
                cleaned = (
                    item
                    .strip()
                )

                if cleaned:
                    output.append(
                        cleaned
                    )

            elif isinstance(
                item,
                dict,
            ):
                name = item.get(
                    "name"
                )

                if isinstance(
                    name,
                    str,
                ):
                    cleaned = (
                        name
                        .strip()
                    )

                    if cleaned:
                        output.append(
                            cleaned
                        )

        return output

    return []


# ---------------------------------------------------------
# MOVIE HELPERS
# ---------------------------------------------------------

def _movie_genres(
    movie: dict[str, Any],
) -> set[str]:
    return {
        genre.lower()
        for genre
        in _normalize_string_list(
            movie.get(
                "genres"
            )
        )
    }


def _movie_runtime(
    movie: dict[str, Any],
) -> float | None:
    return _safe_float(
        movie.get(
            "runtime"
        )
    )


def _movie_year(
    movie: dict[str, Any],
) -> int | None:
    explicit = _safe_int(
        movie.get(
            "release_year"
        )
    )

    if explicit:
        return explicit

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
        return _safe_int(
            release_date[:4]
        )

    return None


# ---------------------------------------------------------
# ONE PARTICIPANT'S TRUE METADATA CONSTRAINTS
# ---------------------------------------------------------

def _violates_one_preference(
    movie: dict[str, Any],
    preference: dict[str, Any],
) -> bool:
    """
    Apply ONLY objectively machine-checkable
    hard constraints.

    Important:
    Do NOT filter on:
        minimum rating
        critically acclaimed
        strong characters
        mood
        pacing
        quality
        originality
        "not depressing"

    Those belong in ranking.
    """

    # -----------------------------------------------------
    # MAX RUNTIME
    # -----------------------------------------------------

    max_runtime = _safe_float(
        preference.get(
            "max_runtime"
        )
    )

    runtime = _movie_runtime(
        movie
    )

    if (
        max_runtime is not None
        and runtime is not None
        and runtime > max_runtime
    ):
        return True

    # -----------------------------------------------------
    # MIN RUNTIME
    # -----------------------------------------------------

    min_runtime = _safe_float(
        preference.get(
            "min_runtime"
        )
    )

    if (
        min_runtime is not None
        and runtime is not None
        and runtime < min_runtime
    ):
        return True

    # -----------------------------------------------------
    # EXPLICIT GENRE EXCLUSIONS
    # -----------------------------------------------------

    avoided_genres = {
        genre.lower()
        for genre
        in _normalize_string_list(
            preference.get(
                "avoid_genres"
            )
        )
    }

    movie_genres = (
        _movie_genres(
            movie
        )
    )

    if (
        avoided_genres
        and movie_genres
        & avoided_genres
    ):
        return True

    # -----------------------------------------------------
    # EXPLICIT RELEASE-YEAR BOUNDS
    # -----------------------------------------------------
    #
    # Only use these if your parser actually produces them.
    # They are safe because they are objective metadata.

    min_year = _safe_int(
        preference.get(
            "release_year_min"
        )
    )

    max_year = _safe_int(
        preference.get(
            "release_year_max"
        )
    )

    movie_year = _movie_year(
        movie
    )

    if movie_year is not None:
        if (
            min_year is not None
            and movie_year < min_year
        ):
            return True

        if (
            max_year is not None
            and movie_year > max_year
        ):
            return True

    return False


# ---------------------------------------------------------
# HARD-CONSTRAINT CHECK
# ---------------------------------------------------------

def violates_hard_constraints(
    movie: dict[str, Any],
    preferences: (
        list[dict[str, Any]]
        | dict[str, Any]
    ),
) -> bool:
    """
    A movie is rejected if it violates any participant's
    objectively machine-checkable hard constraint.
    """

    if isinstance(
        preferences,
        dict,
    ):
        preference_list = [
            preferences
        ]

    elif isinstance(
        preferences,
        list,
    ):
        preference_list = [
            preference
            for preference
            in preferences
            if isinstance(
                preference,
                dict,
            )
        ]

    else:
        return False

    for preference in (
        preference_list
    ):
        if _violates_one_preference(
            movie,
            preference,
        ):
            return True

    return False


# ---------------------------------------------------------
# FILTER CANDIDATES
# ---------------------------------------------------------

def filter_candidates(
    candidates: list[
        dict[str, Any]
    ],
    preferences: (
        list[dict[str, Any]]
        | dict[str, Any]
    ),
) -> list[
    dict[str, Any]
]:
    """
    Deterministic filtering stage.

    This intentionally performs only objective filtering.

    Soft preferences are left for the recommendation
    ranking model.
    """

    if not candidates:
        return []

    filtered: list[
        dict[str, Any]
    ] = []

    for movie in candidates:

        try:
            violation = (
                violates_hard_constraints(
                    movie,
                    preferences,
                )
            )

        except Exception as exc:
            print(
                "[Metadata filter] "
                f"Could not validate "
                f"{movie.get('title', 'Unknown')}: "
                f"{exc}"
            )

            # Fail open.
            violation = False

        if violation:
            print(
                "[Metadata filter] "
                f"Rejected "
                f"{movie.get('title', 'Unknown')}"
            )

            continue

        filtered.append(
            movie
        )

    print(
        "[Metadata filter] "
        f"{len(candidates)} candidates -> "
        f"{len(filtered)} survivors"
    )

    return filtered