from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.diversity_service import diversify_movies
from app.services.recommendation_service import generate_recommendations


# IMPORTANT:
# Do NOT add prefix="/api/v1" here.
# app/main.py should add that prefix when it includes this router.
router = APIRouter(
    tags=["recommendations"],
)


# ---------------------------------------------------------
# REQUEST MODELS
# ---------------------------------------------------------

class ParticipantRequest(BaseModel):
    name: str
    preference: str


class RecommendationRequest(BaseModel):
    participants: list[ParticipantRequest]

    # Movie IDs already shown during this frontend session.
    # The diversity system uses these to favor fresh results.
    exclude_movie_ids: list[int] = Field(
        default_factory=list
    )


# ---------------------------------------------------------
# RECOMMENDATION ENDPOINT
# ---------------------------------------------------------

@router.post("/recommend")
def recommend_movies(
    request: RecommendationRequest,
) -> dict[str, Any]:
    """
    Generate movie recommendations for a group and apply
    diversity-aware reranking.

    The main recommendation engine handles:
        - natural-language preference parsing
        - hard constraints
        - group compatibility
        - movie scoring

    The diversity layer then encourages:
        - different genres
        - different release eras
        - fresh movies across repeated runs
        - controlled variation
    """

    participants = [
        {
            "name": participant.name,
            "preference": participant.preference,
        }
        for participant in request.participants
    ]

    # -----------------------------------------------------
    # GENERATE BASE RECOMMENDATIONS
    # -----------------------------------------------------

    response = generate_recommendations(
        participants
    )

    # -----------------------------------------------------
    # NORMALIZE RESPONSE
    # -----------------------------------------------------

    # Pydantic v2 model
    if hasattr(response, "model_dump"):
        response_data = response.model_dump()

    # Plain dictionary
    elif isinstance(response, dict):
        response_data = response.copy()

    # Unexpected response type:
    # return it untouched rather than breaking the endpoint.
    else:
        return response

    # -----------------------------------------------------
    # APPLY DIVERSITY RERANKING
    # -----------------------------------------------------

    movies = response_data.get(
        "movies",
        [],
    )

    if movies:
        diversified_movies = diversify_movies(
            movies,
            excluded_movie_ids=request.exclude_movie_ids,
            limit=min(
                6,
                len(movies),
            ),
        )

        response_data["movies"] = diversified_movies

    return response_data