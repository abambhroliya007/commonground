import json

from typing import (
    Any,
    Literal,
)

from openai import (
    OpenAI,
)

from app.core.config import (
    settings,
)

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
    api_key=
        settings.openai_api_key
)


ContentType = Literal[
    "movie",
    "show",
]


# ---------------------------------------------------------
# SAFE CONVERSIONS
# ---------------------------------------------------------

def safe_float(
    value:
        Any,

    default:
        float = 0.0,
) -> float:

    try:
        return float(
            value
        )

    except (
        TypeError,
        ValueError,
    ):
        return default


def safe_int(
    value:
        Any,

    default:
        int = 0,
) -> int:

    try:
        return int(
            float(
                value
            )
        )

    except (
        TypeError,
        ValueError,
    ):
        return default


# ---------------------------------------------------------
# SEARCH CONSTRAINTS
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

        runtime = (
            preference.get(
                "max_runtime"
            )
        )

        if runtime:
            value = (
                safe_int(
                    runtime,
                    0,
                )
            )

            if value > 0:
                runtime_limits.append(
                    value
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
        min(
            runtime_limits
        )

        if runtime_limits

        else None
    )

    return (
        preferred_genres,
        avoid_genres,
        max_runtime,
    )


# ---------------------------------------------------------
# FALLBACK INSIGHTS
# ---------------------------------------------------------

def build_fallback_group_insights(
    parsed_preferences:
        list[dict],
):
    shared_preferences = []

    hard_constraints = []

    seen_preferences = set()

    seen_constraints = set()

    for preference in (
        parsed_preferences
    ):

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


        runtime = (
            preference.get(
                "max_runtime"
            )
        )

        if runtime:
            runtime_value = (
                safe_int(
                    runtime,
                    0,
                )
            )

            if (
                runtime_value >
                0
            ):
                label = (
                    f"Under "
                    f"{runtime_value} minutes"
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
            shared_preferences[
                :6
            ],

        "hard_constraints":
            hard_constraints[
                :6
            ],
    }


# ---------------------------------------------------------
# DEDUPE
# ---------------------------------------------------------

def deduplicate_candidates(
    candidates:
        list[dict],
) -> list[dict]:

    unique = []

    seen_ids = set()

    for item in (
        candidates
    ):
        item_id = (
            safe_int(
                item.get(
                    "id"
                ),
                0,
            )
        )

        if (
            not item_id
        ):
            continue

        if (
            item_id
            in seen_ids
        ):
            continue

        seen_ids.add(
            item_id
        )

        unique.append(
            item
        )

    return unique


# ---------------------------------------------------------
# SEARCH
# ---------------------------------------------------------

def search_candidate_pool(
    *,

    content_type:
        ContentType,

    preferred_genres:
        list[str],

    avoid_genres:
        list[str],

    max_runtime:
        int
        | None,

    limit:
        int,
) -> list[dict]:

    try:
        return (
            get_candidate_movies(
                content_type=
                    content_type,

                preferred_genres=
                    preferred_genres,

                avoid_genres=
                    avoid_genres,

                max_runtime=
                    max_runtime,

                limit=
                    limit,
            )

            or []
        )

    except Exception as exc:
        print(
            "[Recommendation search] "
            f"Candidate search failed: "
            f"{exc}"
        )

        return []


# ---------------------------------------------------------
# VALIDATION
# ---------------------------------------------------------

def validate_candidates(
    candidates:
        list[dict],

    parsed_preferences:
        list[dict],
) -> list[dict]:

    if (
        not candidates
    ):
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

    if (
        not metadata_valid
    ):
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
# MULTI-PASS SEARCH
# ---------------------------------------------------------

def get_valid_candidate_pool(
    *,

    content_type:
        ContentType,

    preferred_genres:
        list[str],

    avoid_genres:
        list[str],

    max_runtime:
        int
        | None,

    parsed_preferences:
        list[dict],

    desired_count:
        int = 10,
) -> list[dict]:

    valid = []

    seen_ids = set()


    def add_movies(
        movies:
            list[dict],
    ):
        for movie in movies:

            movie_id = (
                safe_int(
                    movie.get(
                        "id"
                    ),
                    0,
                )
            )

            if (
                not movie_id
            ):
                continue

            if (
                movie_id
                in seen_ids
            ):
                continue

            seen_ids.add(
                movie_id
            )

            valid.append(
                movie
            )


    # PASS 1

    print(
        "[Recommendation search] "
        "Pass 1: targeted search"
    )

    pass_one = (
        search_candidate_pool(
            content_type=
                content_type,

            preferred_genres=
                preferred_genres,

            avoid_genres=
                avoid_genres,

            max_runtime=
                max_runtime,

            limit=
                24,
        )
    )

    add_movies(
        validate_candidates(
            pass_one,

            parsed_preferences,
        )
    )

    if (
        len(
            valid
        ) >=
        desired_count
    ):
        return valid


    # PASS 2

    print(
        "[Recommendation search] "
        "Pass 2: expanded targeted search"
    )

    pass_two = (
        search_candidate_pool(
            content_type=
                content_type,

            preferred_genres=
                preferred_genres,

            avoid_genres=
                avoid_genres,

            max_runtime=
                max_runtime,

            limit=
                36,
        )
    )

    pass_two = [
        item

        for item
        in pass_two

        if safe_int(
            item.get(
                "id"
            ),
            0,
        )
        not in seen_ids
    ]

    add_movies(
        validate_candidates(
            pass_two,

            parsed_preferences,
        )
    )

    if (
        len(
            valid
        ) >=
        desired_count
    ):
        return valid


    # PASS 3

    print(
        "[Recommendation search] "
        "Pass 3: broad discovery with "
        "hard constraints preserved"
    )

    pass_three = (
        search_candidate_pool(
            content_type=
                content_type,

            preferred_genres=
                [],

            avoid_genres=
                avoid_genres,

            max_runtime=
                max_runtime,

            limit=
                40,
        )
    )

    pass_three = [
        item

        for item
        in pass_three

        if safe_int(
            item.get(
                "id"
            ),
            0,
        )
        not in seen_ids
    ]

    add_movies(
        validate_candidates(
            pass_three,

            parsed_preferences,
        )
    )

    return valid


# ---------------------------------------------------------
# BALANCED PAYLOAD
# ---------------------------------------------------------

def build_balanced_llm_payload(
    candidates:
        list[dict],

    preferred_genres:
        list[str],

    limit:
        int = 16,
):

    if (
        len(
            candidates
        ) <=
        limit
    ):
        return candidates

    selected = []

    selected_ids = set()


    for movie in (
        candidates[:6]
    ):
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


    for genre in (
        preferred_genres
    ):
        target_genre = (
            str(
                genre
            )
            .lower()
        )

        for movie in (
            candidates
        ):
            movie_id = (
                safe_int(
                    movie.get(
                        "id"
                    ),
                    0,
                )
            )

            if (
                not movie_id
                or movie_id
                in selected_ids
            ):
                continue

            movie_genres = [
                str(
                    g
                ).lower()

                for g in (
                    movie.get(
                        "genres",
                        [],
                    )
                    or []
                )
            ]

            if (
                target_genre
                in movie_genres
            ):
                selected.append(
                    movie
                )

                selected_ids.add(
                    movie_id
                )

                break

        if (
            len(
                selected
            ) >=
            limit
        ):
            break


    if (
        len(
            selected
        ) <
        limit
    ):
        for movie in (
            candidates
        ):
            movie_id = (
                safe_int(
                    movie.get(
                        "id"
                    ),
                    0,
                )
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

            if (
                len(
                    selected
                ) >=
                limit
            ):
                break


    return selected[
        :limit
    ]


# ---------------------------------------------------------
# CLEAN CANDIDATES
# ---------------------------------------------------------

def clean_candidate_for_llm(
    item:
        dict,
):

    return {
        "id":
            item.get(
                "id"
            ),

        "title":
            item.get(
                "title"
            ),

        "content_type":
            item.get(
                "content_type"
            ),

        "overview":
            item.get(
                "overview",
                "",
            ),

        "release_date":
            item.get(
                "release_date"
            ),

        "vote_average":
            item.get(
                "vote_average",
                0,
            ),

        "vote_count":
            item.get(
                "vote_count",
                0,
            ),

        "runtime":
            item.get(
                "runtime"
            ),

        "genres":
            item.get(
                "genres",
                [],
            ),

        "number_of_seasons":
            item.get(
                "number_of_seasons"
            ),

        "number_of_episodes":
            item.get(
                "number_of_episodes"
            ),

        "constraint_validation":
            item.get(
                "constraint_validation"
            ),
    }


# ---------------------------------------------------------
# FINAL DIVERSITY
# ---------------------------------------------------------

def enforce_final_diversity(
    ranked_movies:
        list[dict],

    preferred_genres:
        list[str],

    limit:
        int = 6,
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
        else
        2
    )

    selected = []

    selected_ids = set()

    animation_count = 0


    for movie in (
        ranked_movies
    ):

        movie_id = (
            safe_int(
                movie.get(
                    "id"
                ),
                0,
            )
        )

        if (
            not movie_id
            or movie_id
            in selected_ids
        ):
            continue

        genres = [
            str(
                genre
            ).lower()

            for genre
            in (
                movie.get(
                    "genres",
                    [],
                )
                or []
            )
        ]

        is_animation = (
            "animation"
            in genres
        )

        if (
            is_animation
            and animation_count >=
            animation_cap
        ):
            continue

        selected.append(
            movie
        )

        selected_ids.add(
            movie_id
        )

        if (
            is_animation
        ):
            animation_count += (
                1
            )

        if (
            len(
                selected
            ) >=
            limit
        ):
            break


    if (
        len(
            selected
        ) <
        limit
    ):
        for movie in (
            ranked_movies
        ):

            movie_id = (
                safe_int(
                    movie.get(
                        "id"
                    ),
                    0,
                )
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

            if (
                len(
                    selected
                ) >=
                limit
            ):
                break


    return selected[
        :limit
    ]


# ---------------------------------------------------------
# JSON PARSER
# ---------------------------------------------------------

def parse_ranking_response(
    raw_text:
        str,
) -> dict:

    raw_text = (
        raw_text
        or ""
    ).strip()

    if (
        not raw_text
    ):
        return {}

    try:
        parsed = (
            json.loads(
                raw_text
            )
        )

        if isinstance(
            parsed,
            dict,
        ):
            return parsed

    except (
        json.JSONDecodeError
    ):
        pass


    cleaned = (
        raw_text
    )

    if (
        cleaned.startswith(
            "```json"
        )
    ):
        cleaned = cleaned[
            len(
                "```json"
            ):
        ]

    elif (
        cleaned.startswith(
            "```"
        )
    ):
        cleaned = cleaned[
            len(
                "```"
            ):
        ]

    if (
        cleaned.endswith(
            "```"
        )
    ):
        cleaned = (
            cleaned[:-3]
        )


    try:
        parsed = (
            json.loads(
                cleaned.strip()
            )
        )

        if isinstance(
            parsed,
            dict,
        ):
            return parsed

    except (
        json.JSONDecodeError
    ):
        pass


    print(
        "[Recommendation ranking] "
        "Unable to parse JSON."
    )

    return {}


# ---------------------------------------------------------
# GENERATE
# ---------------------------------------------------------

def generate_recommendations(
    participants:
        list[dict],

    content_type:
        ContentType = "movie",
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


    candidates = (
        get_valid_candidate_pool(
            content_type=
                content_type,

            preferred_genres=
                preferred_genres,

            avoid_genres=
                avoid_genres,

            max_runtime=
                max_runtime,

            parsed_preferences=
                parsed_preferences,

            desired_count=
                10,
        )
    )

    candidates = (
        deduplicate_candidates(
            candidates
        )
    )

    print(
        "[Recommendation pipeline] "
        f"{len(candidates)} total valid "
        f"{content_type} candidates."
    )


    if (
        not candidates
    ):
        return {
            "summary":
                "No strong match found.",

            "group_profile":
                (
                    "CommonGround could not "
                    "find enough candidates "
                    "that safely satisfy the "
                    "group's deal-breakers."
                ),

            "group_mood":
                (
                    "The group's restrictions "
                    "currently create a narrow match."
                ),

            "content_type":
                content_type,

            "shared_preferences":
                fallback_insights[
                    "shared_preferences"
                ],

            "hard_constraints":
                fallback_insights[
                    "hard_constraints"
                ],

            "movies":
                [],
        }


    balanced_candidates = (
        build_balanced_llm_payload(
            candidates,

            preferred_genres,

            limit=
                16,
        )
    )


    candidate_payload = [
        clean_candidate_for_llm(
            item
        )

        for item
        in balanced_candidates
    ]


    content_label = (
        "movie"
        if content_type ==
        "movie"
        else
        "TV show"
    )


    prompt = f"""
You are ranking candidates for CommonGround,
a multi-person entertainment recommendation
system.

The requested content type is:

{content_label}

Participants and parsed preferences:

{json.dumps(parsed_preferences, indent=2)}

Preferred genres:

{json.dumps(preferred_genres, indent=2)}

Hard genre exclusions:

{json.dumps(avoid_genres, indent=2)}

Validated {content_label} candidates:

{json.dumps(candidate_payload, indent=2)}

Rank the strongest options for the ENTIRE group.

Return JSON exactly like:

{{
  "summary":
    "Short headline describing the ideal group choice",

  "group_profile":
    "Short description of the group's shared taste",

  "group_mood":
    "Consumer-facing description of tonight's mood",

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

      "group_score": 91,

      "explanation":
        "Why this works for the whole group",

      "participant_fits": [
        {{
          "name":
            "Viewer",

          "score":
            90,

          "reason":
            "Why it fits this participant"
        }}
      ]
    }}
  ]
}}

IMPORTANT:

- Recommend ONLY {content_label}s.

- Only use IDs from the supplied candidate list.

- Return 6 results if at least 6 valid candidates exist.

- Hard constraints are mandatory.

- Soft preferences affect ranking but must NOT behave like bans.

- A candidate does not need to perfectly satisfy every soft preference.

- Balance satisfaction fairly across participants.

- Prefer useful variety in genre, era, and tone.

- Do not let one universally acclaimed candidate dominate every search.

- "Critically acclaimed" is a preference, not automatically a minimum numerical rating.

- "Not depressing" is usually a soft tonal preference.

- "Funny" does not require every recommendation to be a comedy.

- Avoid inflated scores.

- Scores over 95 should be rare.

- Do not invent facts outside the candidate metadata.

- Return valid JSON only.
"""


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
            f"Request failed: "
            f"{exc}"
        )

        ranking = {}


    candidate_lookup = {
        safe_int(
            candidate.get(
                "id"
            ),
            0,
        ):
            candidate

        for candidate
        in candidates

        if safe_int(
            candidate.get(
                "id"
            ),
            0,
        )
    }


    ranked_items = (
        ranking.get(
            "movies",
            [],
        )
        or []
    )

    if (
        not isinstance(
            ranked_items,
            list,
        )
    ):
        ranked_items = []


    movies = []


    print(
        "[Recommendation ranking] "
        f"Model returned "
        f"{len(ranked_items)} ranked results."
    )


    for ranked in (
        ranked_items
    ):

        if (
            not isinstance(
                ranked,
                dict,
            )
        ):
            continue


        ranked_id = (
            safe_int(
                ranked.get(
                    "id"
                ),
                0,
            )
        )

        movie = (
            candidate_lookup.get(
                ranked_id
            )
        )

        if (
            not movie
        ):
            continue


        participant_fits = []


        raw_fits = (
            ranked.get(
                "participant_fits",
                [],
            )
            or []
        )


        if (
            not isinstance(
                raw_fits,
                list,
            )
        ):
            raw_fits = []


        for fit in (
            raw_fits
        ):

            if (
                not isinstance(
                    fit,
                    dict,
                )
            ):
                continue

            score = (
                safe_float(
                    fit.get(
                        "score"
                    ),
                    0,
                )
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
                                    score
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


        group_score = (
            safe_float(
                ranked.get(
                    "group_score"
                ),
                0,
            )
        )


        movies.append(
            {
                **movie,

                "group_score":
                    min(
                        100,

                        max(
                            0,

                            round(
                                group_score
                            ),
                        ),
                    ),

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


    target_count = (
        min(
            6,

            len(
                candidates
            ),
        )
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
    }


    # FALLBACK

    if (
        len(
            movies
        ) <
        target_count
    ):
        print(
            "[Recommendation fallback] "
            f"Filling "
            f"{target_count - len(movies)} "
            f"missing results."
        )


        fallback_candidates = sorted(
            candidates,

            key=lambda item: (
                safe_float(
                    item.get(
                        "vote_average"
                    ),
                    0,
                ),

                safe_float(
                    item.get(
                        "vote_count"
                    ),
                    0,
                ),
            ),

            reverse=True,
        )


        for candidate in (
            fallback_candidates
        ):

            if (
                len(
                    movies
                ) >=
                target_count
            ):
                break


            candidate_id = (
                safe_int(
                    candidate.get(
                        "id"
                    ),
                    0,
                )
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
                            f"This {content_label} "
                            "satisfies the group's "
                            "hard constraints and "
                            "remains a strong "
                            "alternative."
                        ),

                    "participant_fits":
                        [],
                }
            )


            used_ids.add(
                candidate_id
            )


    movies = sorted(
        movies,

        key=lambda item:
            safe_float(
                item.get(
                    "group_score"
                ),
                0,
            ),

        reverse=True,
    )


    movies = (
        enforce_final_diversity(
            movies,

            preferred_genres,

            limit=
                6,
        )
    )


    print(
        "[Recommendation final] "
        f"Returning "
        f"{len(movies)} "
        f"{content_type} results."
    )


    shared_preferences = (
        ranking.get(
            "shared_preferences"
        )

        or fallback_insights[
            "shared_preferences"
        ]
    )


    if (
        not isinstance(
            shared_preferences,
            list,
        )
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


    if (
        not isinstance(
            hard_constraints,
            list,
        )
    ):
        hard_constraints = (
            fallback_insights[
                "hard_constraints"
            ]
        )


    return {
        "summary":
            ranking.get(
                "summary"
            )
            or
            (
                "A balanced group "
                f"{content_label} recommendation."
            ),

        "group_profile":
            ranking.get(
                "group_profile"
            )
            or "",

        "group_mood":
            ranking.get(
                "group_mood"
            )
            or
            (
                "A strong watch for "
                "the whole group."
            ),

        "content_type":
            content_type,

        "shared_preferences":
            shared_preferences[
                :6
            ],

        "hard_constraints":
            hard_constraints[
                :6
            ],

        "movies":
            movies[
                :6
            ],
    }