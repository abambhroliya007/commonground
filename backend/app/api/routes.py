from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.diversity_service import (
    diversify_movies,
)

from app.services.recommendation_service import (
    generate_recommendations,
)


router = APIRouter(
    tags=["recommendations"],
)


# ---------------------------------------------------------
# REQUEST MODELS
# ---------------------------------------------------------

class ParticipantRequest(
    BaseModel
):
    name: str
    preference: str


class RecommendationRequest(
    BaseModel
):
    participants: list[
        ParticipantRequest
    ]

    exclude_movie_ids: list[
        int
    ] = Field(
        default_factory=list
    )


# ---------------------------------------------------------
# EMPTY RESPONSE
# ---------------------------------------------------------

def _empty_response() -> dict[
    str,
    Any,
]:
    return {
        "summary": "",
        "group_profile": "",
        "group_mood": "",
        "shared_preferences": [],
        "hard_constraints": [],
        "movies": [],
    }


# ---------------------------------------------------------
# RECOMMEND ENDPOINT
# ---------------------------------------------------------

@router.post(
    "/recommend"
)
def recommend_movies(
    request:
        RecommendationRequest,
) -> dict[str, Any]:

    participants = [
        {
            "name":
                participant.name,

            "preference":
                participant.preference,
        }
        for participant
        in request.participants
    ]

    # -----------------------------------------------------
    # BASE RECOMMENDATIONS
    # -----------------------------------------------------

    response = (
        generate_recommendations(
            participants
        )
    )

    # -----------------------------------------------------
    # NORMALIZE RESPONSE
    # -----------------------------------------------------

    if hasattr(
        response,
        "model_dump",
    ):
        response_data = (
            response.model_dump()
        )

    elif isinstance(
        response,
        dict,
    ):
        response_data = (
            response.copy()
        )

    else:
        print(
            "[API] Unexpected "
            "recommendation response type:",
            type(response),
        )

        return _empty_response()

    response_data.setdefault(
        "summary",
        "",
    )

    response_data.setdefault(
        "group_profile",
        "",
    )

    response_data.setdefault(
        "group_mood",
        "",
    )

    response_data.setdefault(
        "shared_preferences",
        [],
    )

    response_data.setdefault(
        "hard_constraints",
        [],
    )

    raw_movies = (
        response_data.get(
            "movies"
        )
        or []
    )

    if not isinstance(
        raw_movies,
        list,
    ):
        raw_movies = []

    print(
        "[API] Recommendation service "
        f"returned {len(raw_movies)} movies."
    )

    # -----------------------------------------------------
    # NOTHING FROM RECOMMENDATION ENGINE
    # -----------------------------------------------------

    if not raw_movies:
        response_data[
            "movies"
        ] = []

        return response_data

    # -----------------------------------------------------
    # SESSION DIVERSITY
    # -----------------------------------------------------

    try:
        diversified_movies = (
            diversify_movies(
                raw_movies,

                excluded_movie_ids=
                    request.exclude_movie_ids,

                limit=min(
                    6,
                    len(raw_movies),
                ),
            )
        )

    except Exception as exc:
        print(
            "[API diversity] "
            f"Diversity failed: {exc}"
        )

        diversified_movies = []

    # -----------------------------------------------------
    # CRITICAL FAILSAFE
    #
    # Diversity is allowed to REORDER / prefer fresh
    # movies, but it must NEVER destroy a legitimate
    # recommendation response.
    # -----------------------------------------------------

    if not diversified_movies:
        print(
            "[API diversity] "
            "Diversity produced zero movies. "
            "Falling back to base recommendations."
        )

        diversified_movies = (
            raw_movies[:6]
        )

    # -----------------------------------------------------
    # IF DIVERSITY RETURNS TOO FEW,
    # FILL WITH UNUSED BASE MOVIES
    # -----------------------------------------------------

    if (
        len(diversified_movies)
        < min(
            6,
            len(raw_movies),
        )
    ):
        selected_ids = {
            movie.get("id")
            for movie
            in diversified_movies
            if movie.get("id")
            is not None
        }

        for movie in raw_movies:
            if (
                len(
                    diversified_movies
                )
                >= min(
                    6,
                    len(raw_movies),
                )
            ):
                break

            movie_id = (
                movie.get(
                    "id"
                )
            )

            if (
                movie_id
                in selected_ids
            ):
                continue

            diversified_movies.append(
                movie
            )

            if movie_id is not None:
                selected_ids.add(
                    movie_id
                )

    response_data[
        "movies"
    ] = diversified_movies[:6]

    print(
        "[API] Final response contains "
        f"{len(response_data['movies'])} movies."
    )

    return response_data