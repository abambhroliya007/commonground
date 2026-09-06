from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI

from app.core.config import settings


client = OpenAI(
    api_key=settings.openai_api_key
)


# ---------------------------------------------------------
# HARD-CONSTRAINT CLASSIFICATION
# ---------------------------------------------------------

# These are phrases that strongly indicate a real
# deal-breaker rather than a normal preference.
STRICT_MARKERS = (
    "absolutely no ",
    "absolutely not ",
    "must not ",
    "cannot ",
    "can't ",
    "never ",
    "no ",
    "exclude ",
    "avoid ",
    "nothing with ",
    "nothing involving ",
    "do not ",
    "don't ",
    "without ",
    "only ",
)


# Some parsed "hard constraints" are really just soft
# preferences and should NEVER eliminate candidates.
SOFT_PREFERENCE_PATTERNS = (
    "not too slow",
    "not slow",
    "not stupid",
    "not silly",
    "not boring",
    "not depressing",
    "not too depressing",
    "not too dark",
    "not extremely dark",
    "not bleak",
    "not too bleak",
    "not obvious",
    "something different",
    "different from",
    "probably haven't seen",
    "probably have not seen",
    "critically acclaimed",
    "highly rated",
    "good acting",
    "strong acting",
    "strong characters",
    "strong screenplay",
    "good story",
    "clever",
    "intelligent",
    "suspenseful",
    "fast paced",
    "fast-paced",
    "fairly fast",
    "entertaining",
    "visually interesting",
    "memorable world",
    "original",
    "originality",
    "lighter",
    "enjoyable",
)


# Constraints in these semantic categories are useful for
# AI validation because they are not always represented
# perfectly by TMDB metadata.
SEMANTIC_DEAL_BREAKER_TERMS = (
    "gore",
    "torture",
    "disturbing",
    "supernatural",
    "romance-focused",
    "romance focused",
    "romantic relationship",
    "broad comedy",
    "silly comedy",
    "musical",
    "superhero",
    "franchise sequel",
    "live action only",
    "live-action only",
    "animation",
    "animated",
    "extremely depressing",
    "relentlessly bleak",
    "extremely bleak",
)


def _normalize_text(
    value: Any,
) -> str:
    return (
        str(value or "")
        .strip()
        .lower()
    )


def _is_soft_preference(
    constraint: str,
) -> bool:
    normalized = (
        _normalize_text(
            constraint
        )
    )

    if not normalized:
        return True

    return any(
        phrase
        in normalized
        for phrase
        in SOFT_PREFERENCE_PATTERNS
    )


def _looks_explicit(
    constraint: str,
) -> bool:
    normalized = (
        _normalize_text(
            constraint
        )
    )

    return any(
        marker
        in normalized
        for marker
        in STRICT_MARKERS
    )


def _has_semantic_deal_breaker(
    constraint: str,
) -> bool:
    normalized = (
        _normalize_text(
            constraint
        )
    )

    return any(
        term
        in normalized
        for term
        in SEMANTIC_DEAL_BREAKER_TERMS
    )


def is_genuine_hard_constraint(
    constraint: str,
) -> bool:
    """
    Decide whether a parsed hard_constraint should
    actually be allowed to eliminate movies.

    This intentionally errs on the side of treating
    ambiguous language as a SOFT preference.

    Examples:

        "not too slow"
            -> False

        "something different"
            -> False

        "critically acclaimed"
            -> False

        "Absolutely no gore"
            -> True

        "No musicals"
            -> True

        "Avoid romance-focused movies"
            -> True
    """

    normalized = (
        _normalize_text(
            constraint
        )
    )

    if not normalized:
        return False

    # Known soft-language patterns win first.
    if _is_soft_preference(
        normalized
    ):
        return False

    # Strong semantic deal-breakers are allowed when the
    # wording is explicitly exclusionary.
    if (
        _has_semantic_deal_breaker(
            normalized
        )
        and _looks_explicit(
            normalized
        )
    ):
        return True

    # Other constraints need clear exclusion language.
    if _looks_explicit(
        normalized
    ):
        return True

    # Ambiguous AI-generated constraints should not become
    # elimination rules.
    return False


# ---------------------------------------------------------
# COLLECT REAL HARD CONSTRAINTS
# ---------------------------------------------------------

def collect_hard_constraints(
    parsed_preferences: list[dict],
) -> list[str]:
    """
    Build a clean list containing only genuine
    semantic deal-breakers.

    IMPORTANT:

    Genre exclusions and runtime limits are already
    enforced deterministically by scoring_service.py
    and TMDB filtering.

    We therefore don't need to ask the LLM validator
    to repeatedly validate those simple fields.

    The semantic validator should focus on things like:

        no excessive gore
        no torture
        no musicals
        no disturbing supernatural content
        avoid romance-focused movies
        avoid broad comedy

    It should NOT enforce:

        clever
        good story
        not too slow
        critically acclaimed
        something different
    """

    constraints: list[str] = []
    seen: set[str] = set()

    for preference in (
        parsed_preferences
        or []
    ):
        if not isinstance(
            preference,
            dict,
        ):
            continue

        raw_constraints = (
            preference.get(
                "hard_constraints",
                [],
            )
            or []
        )

        if not isinstance(
            raw_constraints,
            list,
        ):
            raw_constraints = [
                raw_constraints
            ]

        for constraint in (
            raw_constraints
        ):
            label = str(
                constraint
                or ""
            ).strip()

            if not label:
                continue

            if not is_genuine_hard_constraint(
                label
            ):
                print(
                    "[Constraint classifier] "
                    f"Treating as SOFT preference: "
                    f"{label}"
                )

                continue

            key = (
                label.lower()
            )

            if key in seen:
                continue

            constraints.append(
                label
            )

            seen.add(
                key
            )

    return constraints


# ---------------------------------------------------------
# JSON CLEANING
# ---------------------------------------------------------

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

    return (
        text.strip()
    )


# ---------------------------------------------------------
# SAFE JSON PARSING
# ---------------------------------------------------------

def _parse_validator_json(
    text: str,
) -> dict:
    cleaned = (
        clean_json_text(
            text
        )
    )

    if not cleaned:
        return {
            "allowed": True,
            "violations": [],
            "reason":
                (
                    "Validator returned no result; "
                    "candidate allowed by fallback."
                ),
        }

    try:
        parsed = json.loads(
            cleaned
        )

    except json.JSONDecodeError:
        # Occasionally an LLM may put text around JSON.
        # Try extracting the first JSON object.
        match = re.search(
            r"\{.*\}",
            cleaned,
            flags=re.DOTALL,
        )

        if not match:
            raise

        parsed = json.loads(
            match.group(0)
        )

    if not isinstance(
        parsed,
        dict,
    ):
        return {
            "allowed": True,
            "violations": [],
            "reason":
                (
                    "Validator returned an unexpected "
                    "format; candidate allowed."
                ),
        }

    return parsed


# ---------------------------------------------------------
# VALIDATE ONE MOVIE
# ---------------------------------------------------------

def validate_candidate_against_constraints(
    movie: dict,
    constraints: list[str],
) -> dict:
    """
    Ask the model whether a candidate clearly violates
    one of the remaining semantic deal-breakers.

    IMPORTANT:
    This validator does NOT decide whether the movie is
    a good recommendation.

    It only decides whether the movie is disqualified.

    Preference matching happens later in the ranking
    system.
    """

    if not constraints:
        return {
            "allowed": True,
            "violations": [],
            "reason":
                "No semantic hard constraints to validate.",
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
You are the FINAL DISQUALIFICATION CHECK
for a group movie recommendation system.

Your job is NOT to determine whether the movie
is a good recommendation.

Your job is ONLY to determine whether the movie
CLEARLY violates one of the explicit deal-breakers
listed below.

Explicit semantic deal-breakers:

{json.dumps(constraints, indent=2)}

Candidate movie:

{json.dumps(movie_payload, indent=2)}

CRITICAL RULE:

ALLOW THE MOVIE UNLESS THE SUPPLIED METADATA
CLEARLY DEMONSTRATES A DEAL-BREAKER VIOLATION.

Do NOT require the movie to satisfy everyone's
preferences.

Do NOT evaluate whether it is:

- clever enough
- funny enough
- suspenseful enough
- interesting enough
- critically acclaimed enough
- fast-paced enough
- original enough
- unexpected enough
- visually impressive enough
- something the users probably haven't seen

Those are ranking preferences, NOT reasons
for rejection.

Only evaluate the explicit deal-breakers supplied.

Examples:

Constraint:
"No excessive gore"

Movie:
An action thriller with violence but no indication
of graphic gore in the supplied metadata.

Result:
ALLOW.

Reason:
Violence alone does not prove excessive gore.

---

Constraint:
"No excessive gore"

Movie metadata:
A graphic splatter film centered on brutal,
gory killings.

Result:
REJECT.

---

Constraint:
"Avoid romance-focused movies"

Movie:
A mystery involving a married detective.

Result:
ALLOW.

A relationship appearing in the movie does not
make romance the central story.

---

Constraint:
"Avoid romance-focused movies"

Movie:
The supplied overview clearly describes the central
plot as two people falling in love.

Result:
REJECT.

---

Constraint:
"Avoid broad comedy"

Movie:
A thriller with occasional comedic moments.

Result:
ALLOW.

---

Constraint:
"No musicals"

Movie genres:
Drama, Music

Overview:
A musician investigates a mystery.

Result:
ALLOW unless the supplied metadata clearly shows
the movie is actually a musical.

Music is not automatically Musical.

---

Constraint:
"No disturbing supernatural stuff"

Movie:
A science-fiction movie involving aliens.

Result:
ALLOW.

Science fiction is not automatically supernatural.

---

Constraint:
"No disturbing supernatural stuff"

Movie:
A terrifying demonic-possession story.

Result:
REJECT.

---

If the supplied metadata is ambiguous or incomplete:

ALLOW.

Never invent facts about the movie.

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

        parsed = (
            _parse_validator_json(
                raw_text
            )
        )

        raw_allowed = (
            parsed.get(
                "allowed",
                True,
            )
        )

        # Avoid bool("false") == True.
        if isinstance(
            raw_allowed,
            str,
        ):
            allowed = (
                raw_allowed
                .strip()
                .lower()
                not in {
                    "false",
                    "no",
                    "0",
                    "reject",
                    "rejected",
                }
            )

        else:
            allowed = bool(
                raw_allowed
            )

        violations = (
            parsed.get(
                "violations",
                [],
            )
            or []
        )

        if not isinstance(
            violations,
            list,
        ):
            violations = [
                str(
                    violations
                )
            ]

        reason = str(
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

        # FAIL OPEN.
        #
        # Recommendation quality may degrade slightly if
        # validation fails, but the system should never
        # eliminate valid movies or crash due to the
        # semantic checker.
        return {
            "allowed": True,

            "violations": [],

            "reason":
                (
                    "Semantic validation failed; "
                    "candidate allowed by fallback."
                ),
        }


# ---------------------------------------------------------
# SEMANTIC FILTER
# ---------------------------------------------------------

def semantic_constraint_filter(
    movies: list[dict],
    parsed_preferences: list[dict],
) -> list[dict]:
    """
    Apply semantic validation ONLY to genuine
    deal-breakers.

    If no genuine semantic constraints exist,
    movies pass directly to ranking.
    """

    if not movies:
        return []

    constraints = (
        collect_hard_constraints(
            parsed_preferences
        )
    )

    print(
        "[Constraint validator] "
        f"Semantic constraints: "
        f"{constraints}"
    )

    if not constraints:
        print(
            "[Constraint validator] "
            "No semantic deal-breakers. "
            "Skipping semantic validation."
        )

        return movies

    filtered: list[
        dict
    ] = []

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

        if result.get(
            "allowed",
            True,
        ):
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

    print(
        "[Constraint validator] "
        f"{len(movies)} entered semantic validation -> "
        f"{len(filtered)} survived."
    )

    return filtered