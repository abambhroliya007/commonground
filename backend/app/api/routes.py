from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.diversity_service import diversify_movies
from app.services.recommendation_service import generate_recommendations


router = APIRouter(
    tags=["recommendations"],
)


ContentType = Literal[
    "movie",
    "show",
]


# ---------------------------------------------------------
# REQUEST MODELS
# ---------------------------------------------------------

class ParticipantRequest(BaseModel):
    name: str
    preference: str


class RecommendationRequest(BaseModel):
    participants: list[ParticipantRequest]

    content_type: ContentType = "movie"

    # Existing name retained for frontend compatibility.
    # These IDs represent the selected content type.
    exclude_movie_ids: list[int] = Field(
        default_factory=list
    )


# ---------------------------------------------------------
# EMPTY RESPONSE
# ---------------------------------------------------------

def _empty_response(
    content_type: ContentType,
) -> dict[str, Any]:
    return {
        "summary": "",
        "group_profile": "",
        "group_mood": "",
        "content_type": content_type,
        "shared_preferences": [],
        "hard_constraints": [],
        "movies": [],
    }


# ---------------------------------------------------------
# RECOMMENDATION ENDPOINT
# ---------------------------------------------------------

@router.post("/recommend")
def recommend_movies(
    request: RecommendationRequest,
) -> dict[str, Any]:

    participants = [
        {
            "name": participant.name,
            "preference": participant.preference,
        }
        for participant in request.participants
    ]

    # -----------------------------------------------------
    # GENERATE RECOMMENDATIONS
    # -----------------------------------------------------

    response = generate_recommendations(
        participants=participants,
        content_type=request.content_type,
    )

    # -----------------------------------------------------
    # NORMALIZE RESPONSE
    # -----------------------------------------------------

    if hasattr(response, "model_dump"):
        response_data = response.model_dump()

    elif isinstance(response, dict):
        response_data = response.copy()

    else:
        print(
            "[API] Unexpected recommendation response type:",
            type(response),
        )

        return _empty_response(
            request.content_type
        )

    response_data["content_type"] = (
        request.content_type
    )

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

    # -----------------------------------------------------
    # NORMALIZE RESULTS
    # -----------------------------------------------------

    raw_movies = (
        response_data.get("movies")
        or []
    )

    if not isinstance(
        raw_movies,
        list,
    ):
        raw_movies = []

    print(
        "[API] Recommendation service returned "
        f"{len(raw_movies)} "
        f"{request.content_type} results."
    )

    if not raw_movies:
        response_data["movies"] = []

        return response_data

    # -----------------------------------------------------
    # SESSION DIVERSITY
    # -----------------------------------------------------

    try:
        diversified = diversify_movies(
            raw_movies,
            excluded_movie_ids=(
                request.exclude_movie_ids
            ),
            limit=min(
                6,
                len(raw_movies),
            ),
        )

    except Exception as exc:
        print(
            "[API diversity] Failed:",
            exc,
        )

        diversified = []

    # Diversity should never erase a legitimate
    # recommendation result.
    if not diversified:
        print(
            "[API diversity] No fresh results. "
            "Falling back to base recommendations."
        )

        diversified = raw_movies[:6]

    # -----------------------------------------------------
    # FILL MISSING SLOTS
    # -----------------------------------------------------

    target_count = min(
        6,
        len(raw_movies),
    )

    if len(diversified) < target_count:

        selected_ids = {
            movie.get("id")
            for movie in diversified
            if movie.get("id") is not None
        }

        for movie in raw_movies:

            if (
                len(diversified)
                >= target_count
            ):
                break

            movie_id = movie.get(
                "id"
            )

            if movie_id in selected_ids:
                continue

            diversified.append(
                movie
            )

            if movie_id is not None:
                selected_ids.add(
                    movie_id
                )

    # -----------------------------------------------------
    # FINAL RESPONSE
    # -----------------------------------------------------

    response_data["movies"] = (
        diversified[:6]
    )

    print(
        "[API] Final response contains "
        f"{len(response_data['movies'])} "
        f"{request.content_type} results."
    )

    return response_data