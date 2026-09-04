# 🎬 CommonGround

### Different tastes. One movie.

CommonGround is an AI-powered group movie recommendation engine designed to solve a familiar problem:

> Everyone wants to watch something — nobody can agree on what.

Instead of endlessly scrolling through streaming services, each person describes what they feel like watching in natural language. CommonGround interprets those preferences, identifies shared interests and deal-breakers, searches real movie data, and recommends movies that best fit the group as a whole.

---

## ✨ What CommonGround Does

Traditional recommendation systems usually optimize for one person.

CommonGround approaches recommendation as a **multi-user consensus problem**.

Each viewer can describe their preferences naturally:

```text
Viewer 1:
Something clever and suspenseful, but not super dark.
Sci-fi, mystery, crime, or a little comedy is fine.

Viewer 2:
Nothing scary, nothing too slow, and preferably under two hours.

Viewer 3:
Strong characters, a good story, and something different
from the usual obvious picks.
```

CommonGround then:

1. Interprets each viewer's natural-language preferences
2. Separates preferences from hard constraints
3. Builds a shared group profile
4. Searches real movie candidates
5. Evaluates each movie against every viewer
6. Balances individual satisfaction
7. Diversifies recommendations by genre and release era
8. Produces a ranked group recommendation

---

# 🧠 Recommendation Engine

CommonGround is more than a prompt wrapped around an LLM.

The backend uses a multi-stage recommendation pipeline.

```text
Viewer Preferences
        │
        ▼
Natural Language Parsing
        │
        ▼
Individual Preference Profiles
        │
        ▼
Group Preference Aggregation
        │
        ▼
Hard Constraint Detection
        │
        ▼
TMDB Candidate Discovery
        │
        ▼
Candidate Filtering
        │
        ▼
AI Group-Fit Evaluation
        │
        ▼
Compatibility Scoring
        │
        ▼
Diversity-Aware Reranking
        │
        ▼
Final Recommendations
```

---

## 🎯 Group-Fit Intelligence

A movie is not selected simply because it matches the most keywords.

CommonGround evaluates how well each candidate works for **every member of the group**.

Each recommendation includes:

- Overall group-fit score
- Individual viewer fit scores
- Explanation of why the movie works
- Group-balance assessment
- Runtime
- Genres
- Release year
- TMDB rating

This makes the recommendation explainable instead of simply returning a list of movie titles.

---

## 🚫 Hard Constraints

CommonGround distinguishes between preferences and deal-breakers.

For example:

```text
"I'd prefer something funny"
```

is treated differently from:

```text
"Absolutely no horror."
```

Potential hard constraints include:

- No horror
- No animation
- No romance
- Runtime limits
- Live-action only
- Genre exclusions

These constraints are protected during candidate selection so a movie cannot rank highly simply by satisfying other preferences while violating an important deal-breaker.

---

## 🌈 Diversity-Aware Recommendations

Recommendation systems can easily become repetitive.

CommonGround includes a diversity-aware reranking layer that rewards useful variation across:

### Genre

Instead of returning several nearly identical thrillers, the system can explore adjacent matches such as:

```text
Mystery + Thriller
Science Fiction + Mystery
Crime + Drama
Comedy + Science Fiction
```

when those genres remain compatible with the group's preferences.

### Timeline

Candidate discovery intentionally explores multiple release eras rather than only recent popular movies.

```text
1980–1999
2000–2009
2010–2019
2020+
```

### Repeat Runs

CommonGround remembers movie IDs already shown during the current session.

Running the same preferences again can therefore surface fresh recommendations instead of simply returning the exact same list.

Controlled randomness is applied only among legitimate candidates so variety does not come at the expense of recommendation quality.

---

# ⚡ Performance

CommonGround's movie discovery layer uses concurrent TMDB requests to reduce recommendation latency.

Instead of retrieving detailed movie information sequentially, candidate details are fetched concurrently using Python's:

```python
ThreadPoolExecutor
```

The candidate pipeline balances:

```text
Recommendation quality
        +
Candidate diversity
        +
API efficiency
        +
Response time
```

---

# 🎨 Interface

CommonGround uses a custom warm cinematic design system built specifically for the product.

The interface includes:

- Responsive viewer cards
- Natural-language preference inputs
- Cinematic dark UI
- Warm amber and espresso color system
- Animated recommendation analysis state
- Group-fit visualization
- Ranked recommendation cards
- Movie posters
- Individual viewer compatibility
- Alternative recommendations
- Interactive recommendation actions

The goal was to make the application feel like a polished consumer product rather than a generic AI dashboard.

---

# 📸 Screenshots

> Screenshots coming soon.

Recommended repository structure:

```text
screenshots/
├── home.png
├── analyzing.png
└── results.png
```

Once screenshots are added, they can be displayed here:

```markdown
![CommonGround Home](screenshots/home.png)

![CommonGround Recommendation Results](screenshots/results.png)
```

---

# 🏗️ Architecture

CommonGround uses a separated frontend/backend architecture.

```text
┌─────────────────────────────────────┐
│              Next.js                │
│                                     │
│        CommonGround Frontend        │
│                                     │
│   React • TypeScript • Tailwind     │
└──────────────────┬──────────────────┘
                   │
                   │ HTTP / JSON
                   │
                   ▼
┌─────────────────────────────────────┐
│              FastAPI                │
│                                     │
│      Recommendation Backend         │
│                                     │
│ Preference Parsing                  │
│ Group Consensus                     │
│ Candidate Ranking                   │
│ Diversity Engine                    │
└──────────────┬──────────────┬───────┘
               │              │
               ▼              ▼
          ┌─────────┐    ┌─────────┐
          │ OpenAI  │    │  TMDB   │
          │   API   │    │   API   │
          └─────────┘    └─────────┘
```

---

# 🛠️ Tech Stack

## Frontend

- Next.js
- React
- TypeScript
- Tailwind CSS

## Backend

- Python
- FastAPI
- Pydantic
- Uvicorn

## AI

- OpenAI API
- Structured preference extraction
- Natural-language group analysis
- Candidate compatibility evaluation

## Movie Data

- TMDB API
- Movie metadata
- Genres
- Runtime
- Ratings
- Posters
- Release information

## Engineering

- REST API architecture
- Concurrent API requests
- Environment-based secret management
- Diversity-aware reranking
- Session-level recommendation novelty

---

# 📁 Project Structure

```text
commonground/
│
├── backend/
│   │
│   ├── app/
│   │   ├── api/
│   │   │   └── routes.py
│   │   │
│   │   ├── core/
│   │   │   └── config.py
│   │   │
│   │   ├── services/
│   │   │   ├── diversity_service.py
│   │   │   ├── preference_service.py
│   │   │   ├── recommendation_service.py
│   │   │   └── tmdb_service.py
│   │   │
│   │   └── main.py
│   │
│   └── requirements.txt
│
├── frontend/
│   │
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

## 1. Clone the Repository

```bash
git clone <your-repository-url>
cd commonground
```

---

## 2. Configure the Backend

Navigate to:

```bash
cd backend
```

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it on macOS/Linux:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## 3. Environment Variables

Create:

```text
backend/.env
```

Add:

```env
OPENAI_API_KEY=your_openai_api_key
TMDB_ACCESS_TOKEN=your_tmdb_access_token
```

Never commit this file.

The repository's `.gitignore` excludes environment files and local secrets.

---

## 4. Start the Backend

From `/backend`:

```bash
python -m uvicorn app.main:app --reload
```

The API should become available at:

```text
http://127.0.0.1:8000
```

FastAPI documentation:

```text
http://127.0.0.1:8000/docs
```

---

## 5. Configure the Frontend

Open another terminal:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Optional frontend environment configuration:

```env
NEXT_PUBLIC_API_URL=http://127.0.0.1:8000
```

---

## 6. Start the Frontend

```bash
npm run dev
```

Then open:

```text
http://localhost:3000
```

---

# 🔐 Security

API credentials are stored using environment variables and are never intended to be committed to source control.

Ignored files include:

```text
.env
.env.*
.venv/
node_modules/
.next/
```

The OpenAI and TMDB credentials remain on the backend rather than being exposed to browser-side application code.

---

# 🧪 Example Test

Try the following group:

### Viewer 1

```text
Something clever and suspenseful, but not super dark.
I'm okay with sci-fi, mystery, crime, or even a little comedy.
```

### Viewer 2

```text
Nothing scary, nothing too slow, and preferably under two hours.
```

### Viewer 3

```text
I want strong characters, a good story, and something that
feels different from the usual obvious picks.
```

CommonGround should identify the group's shared preferences, preserve the restrictions, search movie candidates, and produce a ranked set of group-compatible recommendations.

Run the same group again to test recommendation novelty and diversity.

---

# 🗺️ Roadmap

Potential future improvements include:

- Streaming-provider availability
- Persistent movie-night rooms
- Shareable group links
- User accounts
- Saved taste profiles
- Recommendation history
- Collaborative voting
- More advanced diversity optimization
- Improved recommendation latency
- Streaming-service filtering
- Watchlists
- Mobile-first experience

---

# 💡 Why I Built It

Choosing a movie with multiple people sounds simple until everyone has different preferences.

Most recommendation systems answer:

> "What would this person like?"

CommonGround explores a different question:

> **"What is the strongest choice for this group?"**

The project combines natural-language understanding, recommendation systems, external movie data, multi-user preference balancing, constraint handling, and product-focused frontend engineering into one application.

---

# 📄 License

This project is currently provided for portfolio and educational purposes.

---

<p align="center">
  <strong>CommonGround</strong><br />
  Different tastes. One movie.
</p>