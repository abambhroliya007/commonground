# 🎬 CommonGround

### Different tastes. One watch.

CommonGround is an AI-powered **group entertainment recommendation engine** designed to solve a familiar problem:

> Everyone wants to watch something — nobody can agree on what.

Instead of endlessly scrolling through streaming services, each person describes what they feel like watching in natural language. CommonGround interprets those preferences, separates preferences from deal-breakers, searches real entertainment data, and recommends the movies or TV shows that best fit the group as a whole.

---

## ✨ What CommonGround Does

Traditional recommendation systems usually optimize for one person.

CommonGround approaches recommendation as a **multi-user consensus problem**.

Start by choosing what kind of room you want:

```text
Movie  |  Show
```

Then everyone describes what they feel like watching.

For example:

```text
You:
Something suspenseful but not depressing.

Friend 1:
Funny, under two hours, and no horror.

Friend 2:
Something critically acclaimed with strong characters.
```

CommonGround then:

1. Interprets each viewer's natural-language preferences
2. Separates soft preferences from true deal-breakers
3. Builds a shared group profile
4. Searches real movie or TV candidates
5. Applies deterministic hard constraints
6. Validates nuanced semantic constraints
7. Evaluates candidates against the entire group
8. Ranks recommendations by group compatibility
9. Diversifies results by genre and release era
10. Avoids repeatedly showing the same recommendations

---

# 🎞️ Movie + TV Rooms

CommonGround supports two recommendation modes.

### Movie Room

Designed for choosing a single movie for movie night.

The engine considers information such as:

- Genre
- Runtime
- Release year
- Rating
- Story description
- Tone
- Group preferences
- Hard constraints

### Show Room

Designed for finding a TV series the group can get into together.

TV candidates are normalized into the same recommendation pipeline while retaining show-specific information such as:

- First air date
- Episode runtime
- Number of seasons
- Number of episodes
- Genres
- Rating
- Overview

This allows both modes to use the same underlying group-consensus architecture rather than maintaining two disconnected recommendation engines.

---

# 🧠 Recommendation Engine

CommonGround is more than a prompt wrapped around an LLM.

The backend uses a multi-stage recommendation pipeline:

```text
                Viewer Preferences
                        │
                        ▼
              Natural Language Parsing
                        │
                        ▼
             Individual Taste Profiles
                        │
                        ▼
            Hard vs. Soft Classification
                        │
                        ▼
                Group Aggregation
                        │
                        ▼
                 Room Selection
                  ┌─────┴─────┐
                  ▼           ▼
               MOVIE         SHOW
                  │           │
                  ▼           ▼
            TMDB Movies    TMDB TV
                  └─────┬─────┘
                        ▼
             Candidate Normalization
                        │
                        ▼
          Deterministic Constraint Filter
                        │
                        ▼
            Semantic Constraint Check
                        │
                        ▼
              AI Group-Fit Ranking
                        │
                        ▼
            Diversity / Novelty Layer
                        │
                        ▼
              Final Recommendations
```

---

# 🎯 Hard Constraints vs. Soft Preferences

One of the central design problems in CommonGround is understanding the difference between:

> what someone **would like**

and:

> what someone **will not accept**.

For example:

```text
"Something funny"
```

is a preference.

But:

```text
"Absolutely no horror."
```

is a deal-breaker.

Likewise:

```text
"Something critically acclaimed"
```

should influence ranking.

It should **not** automatically eliminate every movie below an arbitrary numerical rating.

CommonGround therefore separates the two concepts.

### Hard constraints

Examples include:

```text
No horror
Under 120 minutes
No musicals
No animation
```

These can eliminate candidates.

### Soft preferences

Examples include:

```text
Suspenseful
Funny
Strong characters
Critically acclaimed
Not too depressing
Something different
Good story
```

These influence ranking without unnecessarily destroying the candidate pool.

This distinction became an important part of the recommendation architecture because treating every preference as mandatory quickly creates impossible intersections for groups with different tastes.

---

# 🔎 Multi-Pass Candidate Retrieval

A group can sometimes have a narrow combination of preferences.

Instead of immediately returning zero recommendations, CommonGround uses a multi-pass retrieval strategy.

```text
PASS 1
Targeted candidate search
        │
        ▼
Enough valid candidates?
        │
       NO
        ▼
PASS 2
Expanded targeted search
        │
        ▼
Enough valid candidates?
        │
       NO
        ▼
PASS 3
Broader discovery
while preserving true
hard constraints
```

The system can broaden **soft discovery criteria** while keeping genuine deal-breakers intact.

For example, broadening genre discovery does not mean ignoring:

```text
Absolutely no horror.
```

---

# 🎯 Group-Fit Intelligence

CommonGround does not select something simply because it matches the most keywords.

Each candidate is evaluated as a potential **group compromise**.

Recommendations can include:

- Overall group-fit score
- Individual viewer fit scores
- Explanation of why the recommendation works
- Runtime or episode runtime
- Genres
- Release year
- TMDB rating
- Poster artwork
- Show metadata when applicable

The goal is to make recommendations explainable instead of simply returning titles.

---

# 🌈 Diversity-Aware Recommendations

A recommendation system can technically produce relevant results while still feeling repetitive.

CommonGround includes a diversity-aware reranking layer designed to reduce that problem.

### Genre diversity

Instead of repeatedly returning nearly identical candidates, CommonGround can explore adjacent matches when they remain compatible with the group's tastes.

For example:

```text
Mystery + Thriller
Crime + Drama
Science Fiction + Mystery
Adventure + Drama
Comedy + Crime
```

### Timeline diversity

Candidate discovery explores multiple release eras instead of only recent popular content.

```text
1980–1999
2000–2009
2010–2019
2020+
```

### Session novelty

CommonGround tracks recommendations already shown during the current session.

Running the same room again can therefore surface fresh alternatives rather than repeatedly presenting the same universal winner.

Previously shown recommendations are deprioritized or excluded when enough fresh candidates are available.

---

# ⚡ Performance

Candidate discovery may require information from multiple external sources and movie/show detail endpoints.

CommonGround retrieves TMDB candidate details concurrently using Python's:

```python
ThreadPoolExecutor
```

This reduces the cost of retrieving detailed metadata sequentially.

The candidate pipeline balances:

```text
Recommendation quality
        +
Constraint safety
        +
Candidate diversity
        +
API efficiency
        +
Response time
```

---

# 🎨 Product Experience

CommonGround uses a custom **warm cinematic design system**.

The interface includes:

- Movie / Show room selector
- Responsive viewer cards
- Natural-language preference inputs
- Warm beige participant surfaces
- Espresso and charcoal environment
- Amber cinematic accents
- Premium recommendation analysis state
- Group-fit visualization
- Ranked recommendation cards
- Poster artwork
- Individual viewer compatibility
- Alternative recommendations
- Session-aware recommendation novelty
- Responsive navigation

The goal is for CommonGround to feel like a consumer entertainment product rather than a generic AI dashboard.

---

# 📸 CommonGround

![CommonGround Home](screenshots/home.png)

CommonGround lets everyone describe what they feel like watching naturally, then finds the strongest overlap across the entire group.

Additional screenshots:

```text
screenshots/
├── home.png
├── analyzing.png
├── results.png
└── show-room.png
```

Once added:

```markdown
![CommonGround Analysis](screenshots/analyzing.png)

![CommonGround Results](screenshots/results.png)

![CommonGround Show Room](screenshots/show-room.png)
```

---

# 🏗️ Architecture

CommonGround uses a separated frontend/backend architecture.

```text
┌──────────────────────────────────────┐
│               Next.js                │
│                                      │
│        CommonGround Frontend         │
│                                      │
│      React • TypeScript • UI         │
└──────────────────┬───────────────────┘
                   │
                   │ HTTP / JSON
                   ▼
┌──────────────────────────────────────┐
│               FastAPI                │
│                                      │
│       Recommendation Backend         │
│                                      │
│ Preference Parsing                   │
│ Constraint Classification            │
│ Candidate Retrieval                  │
│ Group-Fit Ranking                    │
│ Diversity / Novelty                  │
└──────────────┬──────────────┬────────┘
               │              │
               ▼              ▼
          ┌─────────┐    ┌──────────┐
          │ OpenAI  │    │   TMDB   │
          │   API   │    │ Movie/TV │
          └─────────┘    └──────────┘
```

---

# 🛠️ Tech Stack

### Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS

### Backend

- Python
- FastAPI
- Pydantic
- Uvicorn

### AI

- OpenAI API
- Natural-language preference extraction
- Hard/soft preference classification
- Semantic constraint validation
- Multi-user compatibility ranking
- Explainable recommendations

### Entertainment Data

- TMDB API
- Movie discovery
- TV discovery
- Genres
- Runtime / episode runtime
- Ratings
- Posters
- Release information
- Season and episode metadata

### Engineering

- REST API architecture
- Concurrent external API requests
- Multi-pass candidate retrieval
- Environment-based secret management
- Diversity-aware reranking
- Session-level recommendation novelty
- Defensive API response handling

---

# 📁 Project Structure

```text
commonground/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes.py
│   │   │
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── prompts.py
│   │   │
│   │   ├── services/
│   │   │   ├── constraint_service.py
│   │   │   ├── diversity_service.py
│   │   │   ├── preference_service.py
│   │   │   ├── recommendation_service.py
│   │   │   ├── scoring_service.py
│   │   │   └── tmdb_service.py
│   │   │
│   │   └── main.py
│   │
│   └── requirements.txt
│
├── frontend/
│   ├── app/
│   │   ├── components/
│   │   │   ├── Header.tsx
│   │   │   ├── MovieCard.tsx
│   │   │   ├── ParticipantCard.tsx
│   │   │   └── ResultsView.tsx
│   │   │
│   │   ├── lib/
│   │   │   └── api.ts
│   │   │
│   │   ├── globals.css
│   │   └── page.tsx
│   │
│   └── package.json
│
├── screenshots/
│   └── home.png
│
├── .gitignore
└── README.md
```

---

# 🚀 Running CommonGround Locally

## Prerequisites

You will need:

- Python 3
- Node.js
- npm
- OpenAI API credentials
- TMDB API credentials

---

## 1. Clone

```bash
git clone <your-repository-url>
cd commonground
```

---

## 2. Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create:

```text
backend/.env
```

Add your credentials:

```env
OPENAI_API_KEY=your_openai_api_key
TMDB_ACCESS_TOKEN=your_tmdb_access_token
```

Never commit this file.

---

## 3. Start the Backend

```bash
python -m uvicorn app.main:app --reload
```

Backend:

```text
http://127.0.0.1:8000
```

FastAPI documentation:

```text
http://127.0.0.1:8000/docs
```

---

## 4. Frontend Setup

Open another terminal:

```bash
cd frontend
npm install
```

Optional:

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

Start Next.js:

```bash
npm run dev
```

Then open:

```text
http://localhost:3000
```

---

# 🧪 Example Movie Room

### You

```text
Something suspenseful but not depressing.
```

### Friend 1

```text
Funny, under two hours, and no horror.
```

### Friend 2

```text
Something critically acclaimed with strong characters.
```

CommonGround should identify the group's overlap while keeping `no horror` and the runtime restriction separate from softer preferences such as humor, acclaim, and tone.

---

# 📺 Example Show Room

### You

```text
Crime or mystery with a really good story.
```

### Friend 1

```text
Something exciting, but nothing scary.
```

### Friend 2

```text
Strong characters and preferably not a show with ten seasons.
```

Switch the room to:

```text
Show
```

and CommonGround searches TV candidates instead of movies while using the same group-consensus pipeline.

---

# 🔐 Security

Secrets are stored using environment variables rather than browser-side application code.

Ignored development files should include:

```text
.env
.env.*
.venv/
node_modules/
.next/
```

OpenAI and TMDB credentials remain on the backend.

---

# 🧭 Engineering Lessons

Several edge cases shaped CommonGround's architecture.

### Over-filtering

Early versions treated too many natural-language preferences as mandatory constraints.

For a group, this can quickly create:

```text
24 candidates
      ↓
preference filtering
      ↓
0 candidates
```

The system was redesigned to separate deterministic constraints, semantic deal-breakers, and ranking preferences.

### Recommendation repetition

Highly compatible universal candidates could repeatedly dominate results.

A session-level novelty layer was introduced to encourage fresh recommendations without sacrificing relevance.

### Empty candidate pools

CommonGround now uses multi-pass retrieval and defensive fallbacks so diversity or ranking stages do not unnecessarily erase legitimate validated candidates.

### AI output reliability

Numeric and structured AI outputs are normalized before deterministic comparisons, and malformed or incomplete ranking output is handled defensively.

These problems turned CommonGround from a simple recommendation prototype into a more structured recommendation system.

---

# 🗺️ Roadmap

Potential future improvements:

- Streaming-provider availability
- Streaming-service filtering
- Persistent movie/show rooms
- Shareable group links
- User accounts
- Saved taste profiles
- Recommendation history
- Collaborative voting
- Season-count preferences
- Episode-length preferences
- Watchlists
- Improved latency
- Personalized recommendation memory
- Mobile-first experience

---

# 💡 Why I Built It

Choosing something to watch with multiple people sounds simple until everyone has different preferences.

Most recommendation systems answer:

> **What would this person like?**

CommonGround asks:

> **What is the strongest choice for this group?**

The project combines natural-language understanding, multi-user recommendation, external entertainment data, constraint handling, ranking, diversity, and full-stack product engineering into one system.

---

<p align="center">
  <strong>CommonGround</strong><br />
  Different tastes. One watch.
</p>