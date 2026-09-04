def violates_hard_constraints(
    movie: dict,
    preferences: list[dict],
) -> bool:

    movie_genres = set(movie.get("genres", []))
    runtime = movie.get("runtime")

    for preference in preferences:

        avoided = set(
            preference.get("avoid_genres", [])
        )

        if movie_genres.intersection(avoided):
            return True

        max_runtime = preference.get("max_runtime")

        if (
            max_runtime
            and runtime
            and runtime > max_runtime
        ):
            return True

        minimum_rating = preference.get("minimum_rating")

        if (
            minimum_rating
            and movie.get("vote_average", 0) < minimum_rating
        ):
            return True

    return False


def filter_candidates(
    movies: list[dict],
    preferences: list[dict],
):

    return [
        movie
        for movie in movies
        if not violates_hard_constraints(
            movie,
            preferences,
        )
    ]