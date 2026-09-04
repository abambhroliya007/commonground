import json

from openai import OpenAI

from app.core.config import settings


client = OpenAI(
    api_key=settings.openai_api_key
)


def collect_hard_constraints(
    parsed_preferences: list[dict],
) -> list[str]:
    """
    Build a clean list of hard constraints
    across all participants.
    """

    constraints = []

    seen = set()

    for preference in parsed_preferences:
        # Explicit genre exclusions
        for genre in preference.get(
            "avoid_genres",
            [],
        ):
            label = f"No {genre}"

            key = label.lower()

            if key not in seen:
                constraints.append(label)
                seen.add(key)

        # Explicit semantic constraints
        for constraint in preference.get(
            "hard_constraints",
            [],
        ):
            label = constraint.strip()

            if not label:
                continue

            key = label.lower()

            if key not in seen:
                constraints.append(label)
                seen.add(key)

        # Runtime
        max_runtime = preference.get(
            "max_runtime"
        )

        if max_runtime:
            label = (
                f"Maximum runtime "
                f"{max_runtime} minutes"
            )

            key = label.lower()

            if key not in seen:
                constraints.append(label)
                seen.add(key)

    return constraints


def clean_json_text(
    text: str,
) -> str:
    text = (
        text
        .strip()
    )

    if text.startswith(
        "```json"
    ):
        text = text[
            len("```json"):
        ]

    elif text.startswith(
        "```"
    ):
        text = text[
            len("```"):
        ]

    if text.endswith(
        "```"
    ):
        text = text[:-3]

    return text.strip()


def validate_candidate_against_constraints(
    movie: dict,
    constraints: list[str],
) -> dict:
    """
    Ask the model whether a candidate
    semantically violates any genuine
    hard constraint.

    Returns:
    {
        "allowed": bool,
        "violations": [...],
        "reason": "..."
    }
    """

    if not constraints:
        return {
            "allowed": True,
            "violations": [],
            "reason":
                "No hard constraints to validate.",
        }

    movie_payload = {
        "title":
            movie.get(
                "title"
            ),

        "overview":
            movie.get(
                "overview",
                "",
            ),

        "genres":
            movie.get(
                "genres",
                [],
            ),

        "runtime":
            movie.get(
                "runtime"
            ),

        "vote_average":
            movie.get(
                "vote_average",
                0,
            ),
    }

    prompt = f"""
You are a semantic constraint validator
for a group movie recommendation system.

The user has expressed hard constraints.

Your job is to determine whether this
candidate clearly violates any of them.

Hard constraints:

{json.dumps(constraints, indent=2)}

Candidate movie:

{json.dumps(movie_payload, indent=2)}

Important rules:

1. Only reject a movie when there is a
   clear conflict with a hard constraint.

2. Do not reject based on weak ambiguity.

3. Explicit genre exclusions are strict.

Examples:

Constraint:
"No Horror"

Movie:
A supernatural ghost story with frightening
themes, even if Horror is not listed in the
genre metadata.

Result:
Reject.

Constraint:
"Avoid overly dark tone"

Movie:
A serious thriller that is dark but not
extreme.

Result:
Usually allow unless the description clearly
indicates a very bleak, disturbing, or
oppressive tone.

Constraint:
"Avoid romance-focused movies"

Movie:
A thriller containing a minor romantic
subplot.

Result:
Allow.

Constraint:
"Avoid romance-focused movies"

Movie:
The central story is a romantic relationship.

Result:
Reject.

Constraint:
"Avoid broad comedy"

Movie:
A serious drama with occasional humor.

Result:
Allow.

Constraint:
"Maximum runtime 120 minutes"

Movie runtime:
135

Result:
Reject.

4. Do not invent facts not supported by the
   movie metadata provided.

5. If uncertain, prefer allowing the movie
   rather than rejecting it.

Return ONLY valid JSON:

{{
  "allowed": true,
  "violations": [],
  "reason": "Short explanation"
}}
"""

    try:
        response = (
            client.responses.create(
                model=
                    settings.openai_model,

                input=
                    prompt,
            )
        )

        raw_text = (
            response.output_text
            or ""
        )

        cleaned = clean_json_text(
            raw_text
        )

        if not cleaned:
            return {
                "allowed": True,
                "violations": [],
                "reason":
                    "Validator returned no result; candidate allowed by fallback.",
            }

        parsed = json.loads(
            cleaned
        )

        allowed = bool(
            parsed.get(
                "allowed",
                True,
            )
        )

        violations = (
            parsed.get(
                "violations",
                [],
            )
            or []
        )

        reason = (
            parsed.get(
                "reason",
                "",
            )
            or ""
        )

        return {
            "allowed":
                allowed,

            "violations":
                violations,

            "reason":
                reason,
        }

    except Exception as error:
        print(
            "[Constraint validator] "
            f"Validation failed for "
            f"{movie.get('title')}: "
            f"{error}"
        )

        # Fail open.
        # A validator problem should not
        # crash the whole recommendation.
        return {
            "allowed": True,
            "violations": [],
            "reason":
                "Validation failed; candidate allowed by fallback.",
        }


def semantic_constraint_filter(
    movies: list[dict],
    parsed_preferences: list[dict],
) -> list[dict]:
    """
    Filter a candidate list using semantic
    hard-constraint validation.

    The movie is kept unless the validator
    identifies a clear conflict.
    """

    constraints = collect_hard_constraints(
        parsed_preferences
    )

    if not constraints:
        return movies

    filtered = []

    for movie in movies:
        result = (
            validate_candidate_against_constraints(
                movie=
                    movie,

                constraints=
                    constraints,
            )
        )

        movie[
            "constraint_validation"
        ] = result

        if result[
            "allowed"
        ]:
            filtered.append(
                movie
            )

        else:
            print(
                "[Constraint validator] "
                f"Rejected "
                f"{movie.get('title')}: "
                f"{result.get('reason')}"
            )

    return filtered