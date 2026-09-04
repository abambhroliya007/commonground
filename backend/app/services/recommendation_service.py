import json

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
        )

        avoid_genres.extend(
            preference.get(
                "avoid_genres",
                [],
            )
        )

        if preference.get(
            "max_runtime"
        ):
            runtime_limits.append(
                preference[
                    "max_runtime"
                ]
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


def build_fallback_group_insights(
    parsed_preferences: list[dict],
):
    shared_preferences = []
    hard_constraints = []

    seen_preferences = set()
    seen_constraints = set()

    for preference in parsed_preferences:
        for genre in preference.get(
            "preferred_genres",
            [],
        ):
            label = genre.strip()

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

        for mood in preference.get(
            "moods",
            [],
        ):
            label = mood.strip()

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

        for genre in preference.get(
            "avoid_genres",
            [],
        ):
            label = f"No {genre}"

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

        max_runtime = preference.get(
            "max_runtime"
        )

        if max_runtime:
            label = (
                f"Under "
                f"{max_runtime} minutes"
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

        for constraint in preference.get(
            "hard_constraints",
            [],
        ):
            label = constraint.strip()

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


def build_balanced_llm_payload(
    candidates: list[dict],
    preferred_genres: list[str],
    limit: int = 18,
):
    if len(candidates) <= limit:
        return candidates

    selected = []
    selected_ids = set()

    for movie in candidates[:8]:
        selected.append(movie)

        selected_ids.add(
            movie["id"]
        )

    for genre in preferred_genres:
        for movie in candidates:
            if (
                movie["id"]
                in selected_ids
            ):
                continue

            if (
                genre
                in movie.get(
                    "genres",
                    [],
                )
            ):
                selected.append(
                    movie
                )

                selected_ids.add(
                    movie["id"]
                )

                break

        if len(selected) >= limit:
            break

    if len(selected) < limit:
        for movie in candidates:
            if (
                movie["id"]
                in selected_ids
            ):
                continue

            selected.append(
                movie
            )

            selected_ids.add(
                movie["id"]
            )

            if len(selected) >= limit:
                break

    return selected[:limit]


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


def enforce_final_diversity(
    ranked_movies: list[dict],
    preferred_genres: list[str],
    limit: int = 6,
):
    animation_requested = (
        "Animation"
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
        is_animation = (
            "Animation"
            in movie.get(
                "genres",
                [],
            )
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
            movie["id"]
        )

        if is_animation:
            animation_count += 1

        if len(selected) >= limit:
            break

    if len(selected) < limit:
        for movie in ranked_movies:
            if (
                movie["id"]
                in selected_ids
            ):
                continue

            if (
                "Animation"
                in movie.get(
                    "genres",
                    [],
                )
                and not animation_requested
            ):
                continue

            selected.append(
                movie
            )

            selected_ids.add(
                movie["id"]
            )

            if len(selected) >= limit:
                break

    return selected[:limit]


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
    ) = aggregate_search_constraints(
        parsed_preferences
    )

    candidates = get_candidate_movies(
        preferred_genres=
            preferred_genres,

        avoid_genres=
            avoid_genres,

        max_runtime=
            max_runtime,

        limit=24,
    )

    # First layer:
    # deterministic metadata-based filtering.
    candidates = filter_candidates(
        candidates,
        parsed_preferences,
    )

    # Second layer:
    # semantic hard-constraint validation.
    candidates = semantic_constraint_filter(
        movies=
            candidates,

        parsed_preferences=
            parsed_preferences,
    )

    fallback_insights = (
        build_fallback_group_insights(
            parsed_preferences
        )
    )

    if not candidates:
        return {
            "summary":
                "No movies satisfied every hard constraint.",

            "group_profile":
                "Try relaxing one or more hard constraints.",

            "group_mood":
                "The group has several strong preferences that currently conflict.",

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

    balanced_candidates = (
        build_balanced_llm_payload(
            candidates=
                candidates,

            preferred_genres=
                preferred_genres,

            limit=18,
        )
    )

    candidate_payload = [
        clean_candidate_for_llm(
            movie
        )
        for movie
        in balanced_candidates
    ]

    animation_requested = (
        "Animation"
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
          "name": "Ayush",
          "score": 96,
          "reason":
            "Why this fits Ayush"
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

- Scores must always be between
  0 and 100.

- Candidates have already passed
  semantic hard-constraint validation.

- Do not reintroduce any conflict with
  the group's hard constraints.

- Hard constraints are mandatory.

- Soft preferences should influence
  ranking but should not behave like
  absolute bans.

- Respect nuanced language.

Examples:

"avoid broad comedy"
does NOT mean
"ban all Comedy".

"avoid romance-focused movies"
does NOT mean
"ban all Romance".

"nothing too dark"
does NOT automatically mean
"ban all thrillers".

- If Animation was NOT explicitly
  requested, do not allow animated
  movies to dominate the final list.

- Prefer meaningfully different but
  still relevant interpretations of
  the group's shared taste.

- Balance satisfaction across
  participants rather than optimizing
  for only one person.

- Group score should reflect both
  overall fit and fairness across
  participants.

- Do not invent movie facts not
  contained in the supplied candidate
  data.

- Return valid JSON only.
"""

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

    raw_text = (
        response.output_text
        or ""
    ).strip()

    if not raw_text:
        raise ValueError(
            "Ranking model returned an empty response."
        )

    try:
        ranking = json.loads(
            raw_text
        )

    except json.JSONDecodeError:
        cleaned_text = raw_text

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

        ranking = json.loads(
            cleaned_text.strip()
        )

    candidate_lookup = {
        movie["id"]:
            movie
        for movie
        in candidates
    }

    movies = []

    for ranked in ranking.get(
        "movies",
        [],
    ):
        movie = (
            candidate_lookup.get(
                ranked.get(
                    "id"
                )
            )
        )

        if not movie:
            continue

        participant_fits = []

        for fit in ranked.get(
            "participant_fits",
            [],
        ):
            participant_fits.append(
                {
                    "name":
                        fit.get(
                            "name",
                            "Viewer",
                        ),

                    "score":
                        min(
                            100,
                            max(
                                0,
                                fit.get(
                                    "score",
                                    0,
                                ),
                            ),
                        ),

                    "reason":
                        fit.get(
                            "reason",
                            "",
                        ),
                }
            )

        group_score = min(
            100,
            max(
                0,
                ranked.get(
                    "group_score",
                    0,
                ),
            ),
        )

        movies.append(
            {
                **movie,

                "group_score":
                    group_score,

                "explanation":
                    ranked.get(
                        "explanation",
                        "",
                    ),

                "participant_fits":
                    participant_fits,
            }
        )

    # Make backend ranking authoritative.
    movies = sorted(
        movies,
        key=lambda movie:
            movie.get(
                "group_score",
                0,
            ),
        reverse=True,
    )

    # Final diversity guard.
    movies = enforce_final_diversity(
        ranked_movies=
            movies,

        preferred_genres=
            preferred_genres,

        limit=6,
    )

    shared_preferences = (
        ranking.get(
            "shared_preferences"
        )
        or fallback_insights[
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

    return {
        "summary":
            ranking.get(
                "summary",
                "A balanced group recommendation.",
            ),

        "group_profile":
            ranking.get(
                "group_profile",
                "",
            ),

        "group_mood":
            ranking.get(
                "group_mood",
                "A balanced movie night for everyone.",
            ),

        "shared_preferences":
            shared_preferences[:6],

        "hard_constraints":
            hard_constraints[:6],

        "movies":
            movies[:6],
    }