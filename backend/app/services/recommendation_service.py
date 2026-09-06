import json
from typing import Any

from openai import OpenAI

from app.core.config import settings
from app.core.prompts import (
    RANKING_SYSTEM_PROMPT,
)

from app.services.preference_service import (
    parse_group_preferences,
)

from app.services.scoring_service import (
    filter_candidates,
)

from app.services.tmdb_service import (
    get_candidate_movies,
)

from app.services.constraint_service import (
    semantic_constraint_filter,
)


client = OpenAI(
    api_key=settings.openai_api_key
)


# ---------------------------------------------------------
# SAFE CONVERSION HELPERS
# ---------------------------------------------------------

def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


def safe_int(
    value: Any,
    default: int = 0,
) -> int:
    try:
        return int(
            float(value)
        )

    except (
        TypeError,
        ValueError,
    ):
        return default


# ---------------------------------------------------------
# AGGREGATE SEARCH CONSTRAINTS
# ---------------------------------------------------------

def aggregate_search_constraints(
    preferences,
):
    preferred_genres = []
    avoid_genres = []
    runtime_limits = []

    for preference in preferences:
        preferred_genres.extend(
            preference.get(
                "preferred_genres",
                [],
            )
            or []
        )

        avoid_genres.extend(
            preference.get(
                "avoid_genres",
                [],
            )
            or []
        )

        max_runtime = (
            preference.get(
                "max_runtime"
            )
        )

        if max_runtime:
            parsed_runtime = (
                safe_int(
                    max_runtime,
                    0,
                )
            )

            if parsed_runtime > 0:
                runtime_limits.append(
                    parsed_runtime
                )

    preferred_genres = list(
        dict.fromkeys(
            preferred_genres
        )
    )

    avoid_genres = list(
        dict.fromkeys(
            avoid_genres
        )
    )

    max_runtime = (
        min(runtime_limits)
        if runtime_limits
        else None
    )

    return (
        preferred_genres,
        avoid_genres,
        max_runtime,
    )


# ---------------------------------------------------------
# FALLBACK GROUP INSIGHTS
# ---------------------------------------------------------

def build_fallback_group_insights(
    parsed_preferences: list[dict],
):
    shared_preferences = []
    hard_constraints = []

    seen_preferences = set()
    seen_constraints = set()

    for preference in parsed_preferences:

        for genre in (
            preference.get(
                "preferred_genres",
                [],
            )
            or []
        ):
            label = str(
                genre
            ).strip()

            if (
                label
                and label.lower()
                not in seen_preferences
            ):
                shared_preferences.append(
                    label
                )

                seen_preferences.add(
                    label.lower()
                )

        for mood in (
            preference.get(
                "moods",
                [],
            )
            or []
        ):
            label = str(
                mood
            ).strip()

            if (
                label
                and label.lower()
                not in seen_preferences
            ):
                shared_preferences.append(
                    label
                )

                seen_preferences.add(
                    label.lower()
                )

        for genre in (
            preference.get(
                "avoid_genres",
                [],
            )
            or []
        ):
            label = (
                f"No {genre}"
            )

            if (
                label.lower()
                not in seen_constraints
            ):
                hard_constraints.append(
                    label
                )

                seen_constraints.add(
                    label.lower()
                )

        max_runtime = (
            preference.get(
                "max_runtime"
            )
        )

        if max_runtime:
            runtime = safe_int(
                max_runtime,
                0,
            )

            if runtime > 0:
                label = (
                    f"Under {runtime} minutes"
                )

                if (
                    label.lower()
                    not in seen_constraints
                ):
                    hard_constraints.append(
                        label
                    )

                    seen_constraints.add(
                        label.lower()
                    )

        for constraint in (
            preference.get(
                "hard_constraints",
                [],
            )
            or []
        ):
            label = str(
                constraint
            ).strip()

            if (
                label
                and label.lower()
                not in seen_constraints
            ):
                hard_constraints.append(
                    label
                )

                seen_constraints.add(
                    label.lower()
                )

    return {
        "shared_preferences":
            shared_preferences[:6],

        "hard_constraints":
            hard_constraints[:6],
    }


# ---------------------------------------------------------
# DEDUPLICATE CANDIDATES
# ---------------------------------------------------------

def deduplicate_candidates(
    candidates: list[dict],
) -> list[dict]:
    unique = []
    seen_ids = set()

    for movie in candidates:
        movie_id = movie.get(
            "id"
        )

        if not movie_id:
            continue

        normalized_id = safe_int(
            movie_id,
            0,
        )

        if not normalized_id:
            continue

        if normalized_id in seen_ids:
            continue

        seen_ids.add(
            normalized_id
        )

        unique.append(
            movie
        )

    return unique


# ---------------------------------------------------------
# CANDIDATE SEARCH
# ---------------------------------------------------------

def search_candidate_pool(
    *,
    preferred_genres: list[str],
    avoid_genres: list[str],
    max_runtime: int | None,
    limit: int,
) -> list[dict]:
    try:
        return (
            get_candidate_movies(
                preferred_genres=
                    preferred_genres,

                avoid_genres=
                    avoid_genres,

                max_runtime=
                    max_runtime,

                limit=limit,
            )
            or []
        )

    except Exception as exc:
        print(
            "[Recommendation search] "
            f"Candidate search failed: {exc}"
        )

        return []


# ---------------------------------------------------------
# VALIDATE CANDIDATES
# ---------------------------------------------------------

def validate_candidates(
    candidates: list[dict],
    parsed_preferences: list[dict],
) -> list[dict]:
    if not candidates:
        return []

    metadata_valid = (
        filter_candidates(
            candidates,
            parsed_preferences,
        )
        or []
    )

    print(
        "[Recommendation pipeline] "
        f"{len(candidates)} discovered -> "
        f"{len(metadata_valid)} metadata-valid"
    )

    if not metadata_valid:
        return []

    semantic_valid = (
        semantic_constraint_filter(
            movies=
                metadata_valid,

            parsed_preferences=
                parsed_preferences,
        )
        or []
    )

    print(
        "[Recommendation pipeline] "
        f"{len(metadata_valid)} metadata-valid -> "
        f"{len(semantic_valid)} semantic-valid"
    )

    return semantic_valid


# ---------------------------------------------------------
# MULTI-PASS RETRIEVAL
# ---------------------------------------------------------

def get_valid_candidate_pool(
    *,
    preferred_genres: list[str],
    avoid_genres: list[str],
    max_runtime: int | None,
    parsed_preferences: list[dict],
    desired_count: int = 10,
) -> list[dict]:
    accumulated_valid: list[
        dict
    ] = []

    accumulated_ids = set()

    def add_valid(
        movies: list[dict],
    ):
        for movie in movies:
            movie_id = safe_int(
                movie.get(
                    "id"
                ),
                0,
            )

            if not movie_id:
                continue

            if (
                movie_id
                in accumulated_ids
            ):
                continue

            accumulated_ids.add(
                movie_id
            )

            accumulated_valid.append(
                movie
            )

    # -----------------------------------------------------
    # PASS 1
    # -----------------------------------------------------

    print(
        "[Recommendation search] "
        "Pass 1: targeted search"
    )

    pass_one = (
        search_candidate_pool(
            preferred_genres=
                preferred_genres,

            avoid_genres=
                avoid_genres,

            max_runtime=
                max_runtime,

            limit=24,
        )
    )

    pass_one_valid = (
        validate_candidates(
            pass_one,
            parsed_preferences,
        )
    )

    add_valid(
        pass_one_valid
    )

    if (
        len(
            accumulated_valid
        )
        >= desired_count
    ):
        return accumulated_valid

    # -----------------------------------------------------
    # PASS 2
    # -----------------------------------------------------

    print(
        "[Recommendation search] "
        "Pass 2: expanded targeted search"
    )

    pass_two = (
        search_candidate_pool(
            preferred_genres=
                preferred_genres,

            avoid_genres=
                avoid_genres,

            max_runtime=
                max_runtime,

            limit=36,
        )
    )

    pass_two = [
        movie
        for movie
        in pass_two
        if safe_int(
            movie.get(
                "id"
            ),
            0,
        )
        not in accumulated_ids
    ]

    pass_two_valid = (
        validate_candidates(
            pass_two,
            parsed_preferences,
        )
    )

    add_valid(
        pass_two_valid
    )

    if (
        len(
            accumulated_valid
        )
        >= desired_count
    ):
        return accumulated_valid

    # -----------------------------------------------------
    # PASS 3
    # BROADER DISCOVERY, HARD CONSTRAINTS PRESERVED
    # -----------------------------------------------------

    print(
        "[Recommendation search] "
        "Pass 3: broad discovery with hard constraints preserved"
    )

    pass_three = (
        search_candidate_pool(
            preferred_genres=[],

            avoid_genres=
                avoid_genres,

            max_runtime=
                max_runtime,

            limit=40,
        )
    )

    pass_three = [
        movie
        for movie
        in pass_three
        if safe_int(
            movie.get(
                "id"
            ),
            0,
        )
        not in accumulated_ids
    ]

    pass_three_valid = (
        validate_candidates(
            pass_three,
            parsed_preferences,
        )
    )

    add_valid(
        pass_three_valid
    )

    return accumulated_valid


# ---------------------------------------------------------
# BALANCED LLM PAYLOAD
# ---------------------------------------------------------

def build_balanced_llm_payload(
    candidates: list[dict],
    preferred_genres: list[str],
    limit: int = 16,
):
    if len(candidates) <= limit:
        return candidates

    selected = []
    selected_ids = set()

    for movie in candidates[:6]:
        selected.append(
            movie
        )

        selected_ids.add(
            safe_int(
                movie.get(
                    "id"
                ),
                0,
            )
        )

    for genre in preferred_genres:
        genre_lower = str(
            genre
        ).lower()

        for movie in candidates:
            movie_id = safe_int(
                movie.get(
                    "id"
                ),
                0,
            )

            if (
                not movie_id
                or movie_id
                in selected_ids
            ):
                continue

            movie_genres = [
                str(
                    movie_genre
                ).lower()
                for movie_genre
                in movie.get(
                    "genres",
                    [],
                )
            ]

            if (
                genre_lower
                in movie_genres
            ):
                selected.append(
                    movie
                )

                selected_ids.add(
                    movie_id
                )

                break

        if len(selected) >= limit:
            break

    if len(selected) < limit:
        for movie in candidates:
            movie_id = safe_int(
                movie.get(
                    "id"
                ),
                0,
            )

            if (
                not movie_id
                or movie_id
                in selected_ids
            ):
                continue

            selected.append(
                movie
            )

            selected_ids.add(
                movie_id
            )

            if len(selected) >= limit:
                break

    return selected[:limit]


# ---------------------------------------------------------
# CLEAN CANDIDATE FOR LLM
# ---------------------------------------------------------

def clean_candidate_for_llm(
    movie: dict,
):
    return {
        "id":
            movie.get(
                "id"
            ),

        "title":
            movie.get(
                "title"
            ),

        "overview":
            movie.get(
                "overview",
                "",
            ),

        "release_date":
            movie.get(
                "release_date"
            ),

        "vote_average":
            movie.get(
                "vote_average",
                0,
            ),

        "vote_count":
            movie.get(
                "vote_count",
                0,
            ),

        "runtime":
            movie.get(
                "runtime"
            ),

        "genres":
            movie.get(
                "genres",
                [],
            ),

        "candidate_sources":
            movie.get(
                "candidate_sources",
                [],
            ),

        "constraint_validation":
            movie.get(
                "constraint_validation"
            ),
    }


# ---------------------------------------------------------
# FINAL DIVERSITY GUARD
# ---------------------------------------------------------

def enforce_final_diversity(
    ranked_movies: list[dict],
    preferred_genres: list[str],
    limit: int = 6,
):
    animation_requested = any(
        str(
            genre
        ).lower()
        == "animation"
        for genre
        in preferred_genres
    )

    animation_cap = (
        limit
        if animation_requested
        else 2
    )

    selected = []
    selected_ids = set()

    animation_count = 0

    for movie in ranked_movies:
        movie_id = safe_int(
            movie.get(
                "id"
            ),
            0,
        )

        if (
            not movie_id
            or movie_id
            in selected_ids
        ):
            continue

        movie_genres = [
            str(
                genre
            ).lower()
            for genre
            in movie.get(
                "genres",
                [],
            )
        ]

        is_animation = (
            "animation"
            in movie_genres
        )

        if (
            is_animation
            and animation_count
            >= animation_cap
        ):
            continue

        selected.append(
            movie
        )

        selected_ids.add(
            movie_id
        )

        if is_animation:
            animation_count += 1

        if len(selected) >= limit:
            break

    if len(selected) < limit:
        for movie in ranked_movies:
            movie_id = safe_int(
                movie.get(
                    "id"
                ),
                0,
            )

            if (
                not movie_id
                or movie_id
                in selected_ids
            ):
                continue

            movie_genres = [
                str(
                    genre
                ).lower()
                for genre
                in movie.get(
                    "genres",
                    [],
                )
            ]

            if (
                "animation"
                in movie_genres
                and not animation_requested
            ):
                continue

            selected.append(
                movie
            )

            selected_ids.add(
                movie_id
            )

            if len(selected) >= limit:
                break

    return selected[:limit]


# ---------------------------------------------------------
# SAFE JSON PARSING
# ---------------------------------------------------------

def parse_ranking_response(
    raw_text: str,
) -> dict:
    raw_text = (
        raw_text
        or ""
    ).strip()

    if not raw_text:
        return {}

    try:
        parsed = json.loads(
            raw_text
        )

        if isinstance(
            parsed,
            dict,
        ):
            return parsed

    except json.JSONDecodeError:
        pass

    cleaned_text = (
        raw_text.strip()
    )

    if cleaned_text.startswith(
        "```json"
    ):
        cleaned_text = (
            cleaned_text[
                len("```json"):
            ]
        )

    elif cleaned_text.startswith(
        "```"
    ):
        cleaned_text = (
            cleaned_text[
                len("```"):
            ]
        )

    if cleaned_text.endswith(
        "```"
    ):
        cleaned_text = (
            cleaned_text[:-3]
        )

    try:
        parsed = json.loads(
            cleaned_text.strip()
        )

        if isinstance(
            parsed,
            dict,
        ):
            return parsed

    except json.JSONDecodeError:
        pass

    print(
        "[Recommendation ranking] "
        "Could not parse ranking JSON."
    )

    return {}


# ---------------------------------------------------------
# GENERATE RECOMMENDATIONS
# ---------------------------------------------------------

def generate_recommendations(
    participants: list[dict],
):
    parsed_preferences = (
        parse_group_preferences(
            participants
        )
    )

    (
        preferred_genres,
        avoid_genres,
        max_runtime,
    ) = (
        aggregate_search_constraints(
            parsed_preferences
        )
    )

    fallback_insights = (
        build_fallback_group_insights(
            parsed_preferences
        )
    )

    # -----------------------------------------------------
    # RETRIEVE VALID CANDIDATES
    # -----------------------------------------------------

    candidates = (
        get_valid_candidate_pool(
            preferred_genres=
                preferred_genres,

            avoid_genres=
                avoid_genres,

            max_runtime=
                max_runtime,

            parsed_preferences=
                parsed_preferences,

            desired_count=10,
        )
    )

    candidates = (
        deduplicate_candidates(
            candidates
        )
    )

    print(
        "[Recommendation pipeline] "
        f"{len(candidates)} total valid candidates "
        "after multi-pass search."
    )

    if not candidates:
        return {
            "summary":
                "No movies satisfied every hard constraint.",

            "group_profile":
                (
                    "CommonGround searched multiple "
                    "candidate pools but could not find "
                    "a movie that safely satisfied every "
                    "hard constraint."
                ),

            "group_mood":
                (
                    "The group's true deal-breakers "
                    "currently create a very narrow match."
                ),

            "shared_preferences":
                fallback_insights[
                    "shared_preferences"
                ],

            "hard_constraints":
                fallback_insights[
                    "hard_constraints"
                ],

            "movies": [],
        }

    # -----------------------------------------------------
    # BUILD RANKING PAYLOAD
    # -----------------------------------------------------

    balanced_candidates = (
        build_balanced_llm_payload(
            candidates=
                candidates,

            preferred_genres=
                preferred_genres,

            limit=16,
        )
    )

    candidate_payload = [
        clean_candidate_for_llm(
            movie
        )
        for movie
        in balanced_candidates
    ]

    animation_requested = any(
        str(
            genre
        ).lower()
        == "animation"
        for genre
        in preferred_genres
    )

    prompt = f"""
Participants and parsed preferences:

{json.dumps(parsed_preferences, indent=2)}

Preferred genres:

{json.dumps(preferred_genres, indent=2)}

Hard genre exclusions:

{json.dumps(avoid_genres, indent=2)}

Animation explicitly requested:

{animation_requested}

Real movie candidates that already passed
metadata filtering and semantic hard-constraint
validation:

{json.dumps(candidate_payload, indent=2)}

Your job is to recommend the best movies
for the entire group.

Return JSON exactly like:

{{
  "summary":
    "Short headline describing the group's ideal movie",

  "group_profile":
    "Short description of the group's shared taste",

  "group_mood":
    "Short consumer-facing description of tonight's mood",

  "shared_preferences": [
    "Mystery",
    "Strong characters"
  ],

  "hard_constraints": [
    "No Horror"
  ],

  "movies": [
    {{
      "id": 123,

      "group_score": 94,

      "explanation":
        "Why this works for the whole group",

      "participant_fits": [
        {{
          "name": "Viewer",

          "score": 96,

          "reason":
            "Why this fits this viewer"
        }}
      ]
    }}
  ]
}}

IMPORTANT RULES:

- Only use movie IDs from the supplied
  candidate list.

- Return 6 movies if at least
  6 valid candidates exist.

- If fewer than 6 candidates exist,
  return every legitimate candidate.

- Scores must always be between
  0 and 100.

- Hard constraints are mandatory.

- Soft preferences influence ranking,
  but should never behave like absolute bans.

- A movie does not have to satisfy every soft
  preference perfectly to be a strong compromise.

- Balance satisfaction across participants.

- Prefer meaningful variety in genre,
  tone, and release era when several candidates
  have similar compatibility.

- "Critically acclaimed" is a ranking preference,
  not automatically a numerical cutoff.

- "Not depressing" is a soft tonal preference
  unless explicitly stated as an absolute ban.

- "Funny" does not mean every recommendation
  must be a Comedy.

- "Something different" does not mean
  mainstream movies are automatically invalid.

- If Animation was NOT explicitly requested,
  do not allow animated movies to dominate.

- Do not invent facts outside the supplied
  candidate data.

- Return valid JSON only.
"""

    # -----------------------------------------------------
    # OPENAI RANKING
    # -----------------------------------------------------

    try:
        response = (
            client.responses.create(
                model=
                    settings.openai_model,

                instructions=
                    RANKING_SYSTEM_PROMPT,

                input=
                    prompt,
            )
        )

        ranking = (
            parse_ranking_response(
                response.output_text
                or ""
            )
        )

    except Exception as exc:
        print(
            "[Recommendation ranking] "
            f"Ranking request failed: {exc}"
        )

        ranking = {}

    # -----------------------------------------------------
    # REBUILD REAL MOVIES FROM MODEL IDS
    # -----------------------------------------------------

    candidate_lookup = {
        safe_int(
            movie["id"],
            0,
        ):
            movie
        for movie
        in candidates
        if safe_int(
            movie.get(
                "id"
            ),
            0,
        )
    }

    movies = []

    ranked_movies = (
        ranking.get(
            "movies",
            []
        )
        or []
    )

    if not isinstance(
        ranked_movies,
        list,
    ):
        ranked_movies = []

    print(
        "[Recommendation ranking] "
        f"Model returned {len(ranked_movies)} ranked movies."
    )

    for ranked in ranked_movies:
        if not isinstance(
            ranked,
            dict,
        ):
            continue

        ranked_id = safe_int(
            ranked.get(
                "id"
            ),
            0,
        )

        if not ranked_id:
            continue

        movie = (
            candidate_lookup.get(
                ranked_id
            )
        )

        if not movie:
            print(
                "[Recommendation ranking] "
                f"Unknown candidate ID "
                f"{ranked_id}; skipping."
            )

            continue

        participant_fits = []

        raw_fits = (
            ranked.get(
                "participant_fits",
                [],
            )
            or []
        )

        if not isinstance(
            raw_fits,
            list,
        ):
            raw_fits = []

        for fit in raw_fits:
            if not isinstance(
                fit,
                dict,
            ):
                continue

            fit_score = safe_float(
                fit.get(
                    "score"
                ),
                0.0,
            )

            participant_fits.append(
                {
                    "name":
                        str(
                            fit.get(
                                "name",
                                "Viewer",
                            )
                        ),

                    "score":
                        min(
                            100,
                            max(
                                0,
                                round(
                                    fit_score
                                ),
                            ),
                        ),

                    "reason":
                        str(
                            fit.get(
                                "reason",
                                "",
                            )
                        ),
                }
            )

        group_score = safe_float(
            ranked.get(
                "group_score"
            ),
            0.0,
        )

        group_score = min(
            100,
            max(
                0,
                round(
                    group_score
                ),
            ),
        )

        movies.append(
            {
                **movie,

                "group_score":
                    group_score,

                "explanation":
                    str(
                        ranked.get(
                            "explanation",
                            "",
                        )
                    ),

                "participant_fits":
                    participant_fits,
            }
        )

    print(
        "[Recommendation ranking] "
        f"{len(movies)} ranked movies successfully "
        "matched back to candidates."
    )

    # -----------------------------------------------------
    # GUARANTEED FALLBACK
    # -----------------------------------------------------

    target_count = min(
        6,
        len(candidates),
    )

    used_ids = {
        safe_int(
            movie.get(
                "id"
            ),
            0,
        )
        for movie
        in movies
        if safe_int(
            movie.get(
                "id"
            ),
            0,
        )
    }

    if len(movies) < target_count:
        print(
            "[Recommendation fallback] "
            f"Need {target_count} movies but ranking "
            f"produced {len(movies)}. "
            "Filling from validated candidates."
        )

        fallback_candidates = sorted(
            candidates,
            key=lambda candidate: (
                safe_float(
                    candidate.get(
                        "vote_average"
                    ),
                    0.0,
                ),
                safe_float(
                    candidate.get(
                        "vote_count"
                    ),
                    0.0,
                ),
            ),
            reverse=True,
        )

        for candidate in fallback_candidates:
            if len(movies) >= target_count:
                break

            candidate_id = safe_int(
                candidate.get(
                    "id"
                ),
                0,
            )

            if (
                not candidate_id
                or candidate_id
                in used_ids
            ):
                continue

            movies.append(
                {
                    **candidate,

                    "group_score":
                        72,

                    "explanation":
                        (
                            "This movie passed the group's "
                            "hard constraints and remains a "
                            "strong alternative based on the "
                            "group's shared preferences."
                        ),

                    "participant_fits":
                        [],
                }
            )

            used_ids.add(
                candidate_id
            )

    # -----------------------------------------------------
    # AUTHORITATIVE SORT
    # -----------------------------------------------------

    movies = sorted(
        movies,
        key=lambda movie:
            safe_float(
                movie.get(
                    "group_score"
                ),
                0.0,
            ),
        reverse=True,
    )

    print(
        "[Recommendation fallback] "
        f"{len(movies)} movies available before diversity."
    )

    # -----------------------------------------------------
    # FINAL DIVERSITY
    # -----------------------------------------------------

    movies = (
        enforce_final_diversity(
            ranked_movies=
                movies,

            preferred_genres=
                preferred_genres,

            limit=6,
        )
    )

    print(
        "[Recommendation final] "
        f"Returning {len(movies)} movies."
    )

    # -----------------------------------------------------
    # FINAL INSIGHTS
    # -----------------------------------------------------

    shared_preferences = (
        ranking.get(
            "shared_preferences"
        )
        or fallback_insights[
            "shared_preferences"
        ]
    )

    if not isinstance(
        shared_preferences,
        list,
    ):
        shared_preferences = (
            fallback_insights[
                "shared_preferences"
            ]
        )

    hard_constraints = (
        ranking.get(
            "hard_constraints"
        )
        or fallback_insights[
            "hard_constraints"
        ]
    )

    if not isinstance(
        hard_constraints,
        list,
    ):
        hard_constraints = (
            fallback_insights[
                "hard_constraints"
            ]
        )

    summary = (
        ranking.get(
            "summary"
        )
        or
        "A balanced group recommendation."
    )

    group_profile = (
        ranking.get(
            "group_profile"
        )
        or
        "CommonGround found several movies that satisfy the group's key constraints while balancing everyone's preferences."
    )

    group_mood = (
        ranking.get(
            "group_mood"
        )
        or
        "A balanced movie night for everyone."
    )

    return {
        "summary":
            summary,

        "group_profile":
            group_profile,

        "group_mood":
            group_mood,

        "shared_preferences":
            shared_preferences[:6],

        "hard_constraints":
            hard_constraints[:6],

        "movies":
            movies[:6],
    }