import json

from openai import OpenAI

from app.core.config import settings
from app.core.prompts import (
    PREFERENCE_SYSTEM_PROMPT,
)


client = OpenAI(
    api_key=settings.openai_api_key
)


def clean_json_text(
    text: str,
) -> str:
    """
    Remove common Markdown JSON fences
    before attempting to parse.
    """

    text = text.strip()

    if text.startswith("```json"):
        text = text[
            len("```json"):
        ]

    elif text.startswith("```"):
        text = text[
            len("```"):
        ]

    if text.endswith("```"):
        text = text[:-3]

    return text.strip()


def build_fallback_preference(
    name: str,
    preference: str,
) -> dict:
    """
    Safe fallback so one bad model response
    does not crash the whole recommendation
    request.
    """

    return {
        "name": name,

        "preferred_genres": [],

        "avoid_genres": [],

        "moods": [
            preference
        ],

        "keywords": [],

        "max_runtime": None,

        "minimum_rating": None,

        "hard_constraints": [],
    }


def parse_participant_preference(
    name: str,
    preference: str,
) -> dict:
    prompt = f"""
Participant:
{name}

Preference:
{preference}

Return ONLY valid JSON.

Do not use Markdown.
Do not wrap the response in code fences.
Do not include commentary before or after the JSON.

Return exactly this structure:

{{
  "name": "{name}",
  "preferred_genres": [],
  "avoid_genres": [],
  "moods": [],
  "keywords": [],
  "max_runtime": null,
  "minimum_rating": null,
  "hard_constraints": []
}}

Use common movie genre names such as:

Action
Adventure
Animation
Comedy
Crime
Documentary
Drama
Family
Fantasy
History
Horror
Music
Mystery
Romance
Science Fiction
Thriller
War
Western

IMPORTANT INTERPRETATION RULES:

1. Only use avoid_genres for explicit
   whole-genre exclusions.

Examples:

"Absolutely no horror"
-> avoid_genres: ["Horror"]

"No horror"
-> avoid_genres: ["Horror"]

"I don't want romance"
-> avoid_genres: ["Romance"]

"No comedy"
-> avoid_genres: ["Comedy"]


2. Preserve nuanced dislikes.

"No broad comedy"
-> DO NOT put Comedy in avoid_genres.
-> Put "avoid broad comedy" in
   hard_constraints.

"Nothing too silly"
-> DO NOT ban Comedy.
-> Preserve it as a tone preference.

"Not romance-focused"
-> DO NOT automatically ban Romance.
-> Put "avoid romance-focused movies"
   in hard_constraints.

"Nothing too dark"
-> DO NOT automatically ban Horror.
-> Put "avoid overly dark tone"
   in hard_constraints.


3. Runtime interpretation.

"Under 2 hours"
-> max_runtime: 120

"Under two hours"
-> max_runtime: 120

"Preferably under two hours"
-> max_runtime may still be 120 if
   clearly important, but preserve the
   softer language when appropriate.


4. Genre interpretation.

"Funny"
-> Comedy may be preferred.

"Suspenseful"
-> Thriller or Mystery may be preferred.

"Sci-fi"
-> Science Fiction may be preferred.

"Fantasy"
-> Fantasy may be preferred.


5. Preserve tone and semantic information
   inside moods, keywords, and
   hard_constraints.


6. Never invent a restriction that the
   participant did not express.


7. A modifier does not automatically create
   a full genre ban.

"No broad comedy"
is NOT equivalent to
"No comedy".

"Not romance-focused"
is NOT equivalent to
"No romance".

Return valid JSON only.
"""

    try:
        response = client.responses.create(
            model=
                settings.openai_model,

            instructions=
                PREFERENCE_SYSTEM_PROMPT,

            input=
                prompt,
        )

        raw_text = (
            response.output_text
            or ""
        )

        cleaned_text = clean_json_text(
            raw_text
        )

        if not cleaned_text:
            print(
                f"[Preference parser] Empty OpenAI response for {name}"
            )

            return (
                build_fallback_preference(
                    name,
                    preference,
                )
            )

        try:
            parsed = json.loads(
                cleaned_text
            )

        except json.JSONDecodeError:
            print(
                f"[Preference parser] Invalid JSON for {name}:"
            )

            print(
                repr(cleaned_text)
            )

            return (
                build_fallback_preference(
                    name,
                    preference,
                )
            )

        # Ensure the required structure exists.

        parsed.setdefault(
            "name",
            name,
        )

        parsed.setdefault(
            "preferred_genres",
            [],
        )

        parsed.setdefault(
            "avoid_genres",
            [],
        )

        parsed.setdefault(
            "moods",
            [],
        )

        parsed.setdefault(
            "keywords",
            [],
        )

        parsed.setdefault(
            "max_runtime",
            None,
        )

        parsed.setdefault(
            "minimum_rating",
            None,
        )

        parsed.setdefault(
            "hard_constraints",
            [],
        )

        return parsed

    except Exception as error:
        print(
            f"[Preference parser] OpenAI request failed for {name}: {error}"
        )

        return (
            build_fallback_preference(
                name,
                preference,
            )
        )


def parse_group_preferences(
    participants: list[dict],
) -> list[dict]:
    parsed_preferences = []

    for participant in participants:
        result = (
            parse_participant_preference(
                name=
                    participant["name"],

                preference=
                    participant[
                        "preference"
                    ],
            )
        )

        parsed_preferences.append(
            result
        )

    return parsed_preferences