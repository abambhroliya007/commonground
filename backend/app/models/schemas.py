from pydantic import BaseModel, Field


class ParticipantInput(BaseModel):
    name: str
    preference: str


class RecommendationRequest(BaseModel):
    participants: list[ParticipantInput]


class ParsedPreference(BaseModel):
    name: str
    preferred_genres: list[str] = []
    avoid_genres: list[str] = []
    moods: list[str] = []
    keywords: list[str] = []
    max_runtime: int | None = None
    minimum_rating: float | None = None
    hard_constraints: list[str] = []


class MovieCandidate(BaseModel):
    id: int
    title: str
    overview: str
    poster_path: str | None = None
    release_date: str | None = None
    vote_average: float = 0
    runtime: int | None = None
    genres: list[str] = []


class ParticipantFit(BaseModel):
    name: str
    score: int
    reason: str


class RankedMovie(BaseModel):
    id: int
    title: str
    overview: str
    poster_path: str | None = None
    release_date: str | None = None
    vote_average: float
    runtime: int | None = None
    genres: list[str] = []

    group_score: int = Field(
        ge=0,
        le=100,
    )

    explanation: str

    participant_fits: list[
        ParticipantFit
    ]


class RecommendationResponse(BaseModel):
    summary: str

    group_profile: str

    group_mood: str

    shared_preferences: list[str]

    hard_constraints: list[str]

    movies: list[RankedMovie]