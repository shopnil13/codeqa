# CodeQA: Complete Implementation Guide

**Companion to:** `codebase-qa-implementation-plan.md` (the plan says *what* to build; this guide says *exactly how*).
**Starting point:** commit `11860cd` ("Ingest feature implemented along with unit test cases").
**Written for:** a beginner who can read Python and use a terminal, and wants to finish the whole project without guessing.

---

## Table of contents

- [Part A. How to use this guide](#part-a-how-to-use-this-guide)
- [Part B. Audit of the current codebase](#part-b-audit-of-the-current-codebase)
- [Part C. The finished system at a glance](#part-c-the-finished-system-at-a-glance)
- [Phase 0. Fix the foundation](#phase-0-fix-the-foundation)
- [Phase 1. Ingestion and AST chunking](#phase-1-ingestion-and-ast-chunking)
- [Phase 2. Embeddings, vector store and the indexing pipeline](#phase-2-embeddings-vector-store-and-the-indexing-pipeline)
- [Phase 3. Hybrid retrieval](#phase-3-hybrid-retrieval)
- [Phase 4. Evaluation harness](#phase-4-evaluation-harness)
- [Phase 5. Reranking and the evidence gate](#phase-5-reranking-and-the-evidence-gate)
- [Phase 6. LangGraph pipeline and grounded generation](#phase-6-langgraph-pipeline-and-grounded-generation)
- [Phase 7. REST API and web UI](#phase-7-rest-api-and-web-ui)
- [Phase 8. Docker, CI and hardening](#phase-8-docker-ci-and-hardening)
- [Phase 9. Held-out evaluation, generation evaluation and documentation](#phase-9-held-out-evaluation-generation-evaluation-and-documentation)
- [Appendix A. Final file tree](#appendix-a-final-file-tree)
- [Appendix B. Command cheat sheet](#appendix-b-command-cheat-sheet)
- [Appendix C. Troubleshooting](#appendix-c-troubleshooting)
- [Appendix D. Concepts glossary](#appendix-d-concepts-glossary)
- [Appendix E. Interview preparation](#appendix-e-interview-preparation)

---

## Part A. How to use this guide

### A.1 The rules of the road

1. **Do the phases in order.** Each phase only imports code from earlier phases. Every
   phase in this guide was checked on a fresh copy of the repository: after you finish a
   phase, `make lint` and `make test` pass. If they fail, the problem is in what you
   typed, not in the plan.
2. **Copy files exactly.** Every code block is a *complete file* unless it says
   otherwise. Create the file at the path in the heading and paste the whole block.
   When a file changes in a later phase, the guide gives you the full new version
   again; replace the old content completely.
3. **Read the "Why" before the code.** The code is the easy part. The reasons are what
   you will be asked about in interviews, and what lets you fix things when they break.
4. **Commit after every step.** Small commits make mistakes cheap to undo. A good rhythm:
   ```bash
   git add -A
   git commit -m "feat(ingest): AST chunker handles nested classes"
   ```
   Commit types used in this guide: `feat` (new behaviour), `fix` (bug fix), `refactor`
   (same behaviour, better code), `test`, `docs`, `chore` (tooling), `ci`.
5. **Work on a branch per phase**, then merge into `main`:
   ```bash
   git checkout -b phase-1-chunking
   # ... do the phase, commit as you go ...
   git checkout main && git merge --no-ff phase-1-chunking
   ```
   *Why:* even solo, a PR per phase shows a reviewer that you work in reviewable units.

### A.2 How each step is written

Every step has the same shape:

- **What:** the file or command, in one sentence.
- **Why:** the reason this exists, and what would go wrong without it.
- **Code:** the complete file.
- **Check:** a command that proves the step worked.

### A.3 Versions this guide was verified with

| Tool / library | Version | Tool / library | Version |
|---|---|---|---|
| Python | 3.12 | uv | 0.12.8 |
| tree-sitter / tree-sitter-python | 0.26.0 / 0.25.0 | qdrant-client / Qdrant server | 1.19.1 / v1.19.1 |
| fastembed | 0.8.1 | langgraph | 1.2.12 |
| langchain-core | 1.6.6 | langchain-groq / -google-genai / -ollama | 1.1.3 / 4.4.0 / 1.1.0 |
| SQLAlchemy / Alembic | 2.0.52 / 1.20.0 | FastAPI / Pydantic | 0.141.1 / 2.13.5 |
| PostgreSQL image | 16.15 | Docker | 29.x with Compose v2 |

> **Version note.** tree-sitter, fastembed, qdrant-client and LangGraph change their APIs
> between versions. The code here matches the versions above, which are pinned in
> `pyproject.toml`. If you read a blog post that uses a different API, trust the pinned
> version's docs, not the blog.

### A.4 Everyday commands you will use

```bash
make up          # start Postgres + Qdrant in Docker
make migrate     # apply database migrations
make lint        # ruff (lint + format check) + mypy
make test        # pytest
make format      # auto-fix formatting and simple lint issues
```

---

## Part B. Audit of the current codebase

I read every tracked file, ran the tool chain (`pytest`, `ruff check`, `ruff format
--check`, `mypy src`), and compared the code with the plan. Summary first, then details.

### B.1 Status by phase

| Phase | Status | What exists | What is missing |
|---|---|---|---|
| 0. Skeleton | **~80%** | uv project, src layout, ruff/mypy/pytest/pre-commit config, `config.py`, `logging.py`, Postgres + Qdrant in Compose, Alembic with a first migration (4 tables), Makefile, `.gitignore`, a smoke test | CI workflow, LICENSE, README (empty), four tables from the data model, `make lint` currently **fails** |
| 1. Ingestion + AST chunking | **~50%** | `source.py`, `walker.py`, the `Chunk` contract, AST / fixed / markdown chunkers, edge extraction (as `ingest/ingest.py`), `codeqa chunk` CLI, 3 chunker tests | Several correctness bugs (below), edges are not stored anywhere, tests do not cover nested/decorated/async/large functions, no walker/edge tests, no chunk-size histogram, no comparison doc |
| 2. Embeddings + vector store | 0% | Empty `db/repositories.py` | Embedder, sparse encoder, Qdrant adapter, indexing pipeline, `codeqa index` |
| 3. Hybrid retrieval | 0% | | RRF, search service, `codeqa search` |
| 4. Evaluation harness | 0% | Empty `eval/` folders | Dataset, metrics, ablation runner |
| 5. Reranking + gate | 0% | `RERANKER_ENABLED` in `.env.example` | Reranker, threshold calibration |
| 6. LangGraph + generation | 0% | | Everything in `graph/` |
| 7. API + UI | 0% | FastAPI, Streamlit installed | Everything in `api/` and `ui/` |
| 8. Hardening, Docker, CI | 0% | | Dockerfile, CI, healthchecks |
| 9. Held-out eval + docs | 0% | Empty `docs/adr`, `docs/images` | Everything |

### B.2 What is complete and good

These are solid; the guide keeps them and builds on them:

- **Project layout.** `src/` layout, `[project.scripts]` entry point, dev dependency group,
  strict mypy, ruff rule set (`E, F, I, UP, B`), pre-commit with ruff + mypy.
- **Configuration pattern.** `pydantic-settings` with a cached `get_settings()`. This is
  the right pattern; it only needs more fields.
- **Alembic wiring.** `migrations/env.py` reads the URL from settings and imports
  `Base.metadata`, so autogenerate works. This is the part beginners usually get wrong.
- **Chunking design.** The `Chunk` dataclass + `Chunker` protocol, keeping the fixed-size
  chunker as a baseline, using the `decorated_definition` wrapper so decorators stay with
  their function, and slicing *bytes* (not characters) in `_text()`.
- **Walker basics.** `.gitignore` support, vendored-folder skip, size limit, NUL-byte
  binary check, SHA-256 per file.

### B.3 Problems found (with evidence)

Each item says where it is, what goes wrong, and which step fixes it.

| # | Where | Problem | Consequence | Fixed in |
|---|---|---|---|---|
| 1 | `config.py`, `models/*.py` | `ruff format --check` reports 4 files would be reformatted | `make lint` fails, so CI would be red from day one | 0.2 |
| 2 | `pyproject.toml` `[tool.ruff] exclude = [...]` | `exclude` *replaces* ruff's default excludes (which contain `.venv`) | Works in your git checkout only because ruff also reads `.gitignore`. In a non-git copy (Docker build context, a zip download) ruff lints `.venv`: I measured 79,000+ errors | 0.1 |
| 3 | `config.py:11` | Field is `environment`, but `.env.example` sets `APP_ENV` | `APP_ENV=production` is silently ignored; JSON logs never switch on | 0.3 |
| 4 | `config.py` | No fields for `GROQ_API_KEY`, `GOOGLE_API_KEY`, `OLLAMA_BASE_URL`, `RERANKER_ENABLED` although `.env.example` lists them | `extra="ignore"` hides the mismatch; the values can never be read | 0.3 |
| 5 | `db/session.py:6-8` | Engine is created at import time | Any import of this module needs a reachable DB config; tests cannot swap in another database | 0.7 |
| 6 | `models/repository.py:19` + first migration | `source_url` is `NOT NULL` | Indexing a local folder (no URL) crashes on insert | 0.8 |
| 7 | `models/repository.py:18` | `default=datetime.utcnow` | Deprecated since Python 3.12 and produces naive timestamps | 0.8 |
| 8 | models | No unique constraint on `repositories.name` or `(files.repository_id, files.path)` | Re-indexing can silently create duplicates | 0.8 |
| 9 | models | Tables `symbol_edges`, `query_logs`, `feedback`, `eval_runs` from the data model do not exist; `chunks` has no `part_index` | Phases 1, 4, 6, 7 have nowhere to store their data | 0.8, 0.9 |
| 10 | `python_ast.py:68-82` (`_make_part`) | Every split part keeps the **original** `start_line`/`end_line` | For any function over 4,000 chars, every citation points at the whole function, not the part that was used | 1.4 |
| 11 | `python_ast.py:43-65` | Oversized functions are split by character count, mid-statement | Parts can start in the middle of an `if` block | 1.4 |
| 12 | `python_ast.py:150-163` | Class members that are classes are ignored | Methods of nested classes are **never indexed** | 1.4 |
| 13 | `python_ast.py:183-189` | Module chunk keeps only imports and expression statements | `if __name__ == "__main__":`, `try:` import fallbacks, `with`/`for` at top level, and whole files with syntax errors are **silently dropped** | 1.4 |
| 14 | `python_ast.py:31-40` | Docstrings are cleaned with `.strip("\"' \n")` | Prefixed strings (`r"""..."""`) keep the prefix; indentation is not removed | 1.4 |
| 15 | `python_ast.py` | Class skeleton has no class attributes | "What config does `Client` have?" cannot be answered from the skeleton, which the plan requires | 1.4 |
| 16 | `ingest/ingest.py` | File name does not match its job (edge extraction); nothing calls it | Call graph is never stored | 1.6, 2.7 |
| 17 | `ingest/ingest.py:46-51` | Nested classes are qualified as `Inner.method`, not `Outer.Inner.method` | Edge owners do not match chunk names, so edges cannot be linked to chunks | 1.6 |
| 18 | `ingest/ingest.py:33` | Callee name is `text.split(".")[-1]` | `a().b()` and `x[0]()` produce garbage names; `print`/`len` create noise edges | 1.6 |
| 19 | `walker.py:54` | Uses the `"gitwildmatch"` pattern name | Deprecated in pathspec 1.x; it raises under `-W error` | 1.7 |
| 20 | `walker.py:66` | `root.rglob("*")` then filter | Walks every file of `.venv` and `node_modules` before skipping them: slow on real repos | 1.7 |
| 21 | `walker.py` | No file-type filter; symlinks are followed | Lock files, JSON dumps and CSVs get indexed; a symlink can point outside the repo | 1.7 |
| 22 | `source.py:28-34` | Every clone goes to a new random folder, with no timeout | Disk fills up on re-index; a hanging clone blocks forever | 1.8 |
| 23 | `source.py` | No "allowed root" check for local paths | Once the API exists, anyone could ask it to index `/etc` or `~/.ssh` | 1.8 |
| 24 | `logging.py:34, 39` | Logs go to stdout; return type claims a stdlib logger | Log lines mix with CLI output and `--json` output | 0.5 |
| 25 | `docker-compose.yml` | Qdrant `v1.11.0`, no healthchecks | Current `qdrant-client` warns when the server is more than one minor version behind; services can be "up" before they accept connections | 0.11 |
| 26 | `pyproject.toml` | `psycopg` without the `binary` extra | Needs `libpq` installed on the machine; fails in a slim Docker image | 0.1 |
| 27 | `src/codeqa/__init__.py` | Leftover `main()` printing "Hello from codeqa!" | Dead code | 0.6 |

### B.4 Design changes this guide makes to the plan (and why)

The plan is good. These small changes came out of building and testing the full system:

| Change | Why |
|---|---|
| `repositories` gets `chunker`, `embedding_model`, `collection_name` columns | The ablation indexes the same repo several ways. Search must query each variant with the *same* model and collection it was indexed with, so the repo row records them. |
| Chunk ids include `kind` and `start_line` | With only `repo|path|qualified_name|part`, a property getter and setter (same name) collide, and so do a class skeleton and its module chunk. A collision breaks the Postgres primary key. |
| Edge extraction lives in `ingest/edges.py` (as the plan says), but chunk ids for edges are resolved inside the pipeline | Edges must point at chunk rows, which only exist once the pipeline writes them. |
| Tests run on **SQLite in memory** by default and on Postgres in CI | You can run the whole suite with no Docker. CI still proves it works on the real database. Models use SQLAlchemy's portable `Uuid` and a `JSON`/`JSONB` variant to make this possible. |
| Fake embedders (`hashing-64`), fake sparse encoder, fake reranker and `FakeLLM` | The test suite needs no network and no model downloads, and runs in about 2 seconds. |
| The CLI is split into one module per command group | Each phase adds one module and one import line, instead of editing a 400-line file. |
| Evaluation logic lives in `src/codeqa/evaluation/`, run through `codeqa eval ...` | The plan's `eval/run_*.py` scripts become typed, tested package code. `eval/` keeps the datasets, configs and results. |
| The reranker module is created in Phase 4 | The retrieval ablation needs a "reranker on/off" switch. Phase 5 then studies it. |

---

## Part C. The finished system at a glance

### C.1 What happens when you index a repo

```
codeqa index ./httpx -n httpx
  │
  ├─ resolve_source()      local path or shallow git clone, record commit SHA
  ├─ walk_repository()     skip vendored/ignored/secret/binary/huge files, SHA-256 each
  ├─ for each changed file (unchanged hashes are skipped):
  │     chunker_for(lang)  AST chunks for .py, header sections for .md, windows otherwise
  │     extract_edges()    who-calls-what inside each function
  │     chunk_id()         deterministic uuid5, same in Postgres and Qdrant
  ├─ every 128 chunks:     embed dense (jina code) + sparse (BM25 with identifier splitting)
  │     Qdrant upsert      (first)
  │     Postgres commit    (last: the new file hash means "this file is done")
  ├─ delete files that disappeared
  └─ resolve_edges()       link call edges to the chunks they most likely call
```

### C.2 What happens when you ask a question

```
codeqa ask "how are retries handled?" -r httpx
  │
  route_question ──code_search──► retrieve_hybrid ─► rerank_and_gate ─┬─ sufficient ─► generate_answer ─► validate_citations ─► END
      │                                ▲                              ├─ weak, 0 retries ─► rewrite_query ─┘ (one retry only)
      │                                └──────────────────────────────┴─ weak, retry used ─► respond_not_found ─► END
      ├──dependency──► lookup_dependencies (SQL over symbol_edges) ─► generate_answer
      ├──overview────► build_repo_map (files + symbols + README) ───► generate_answer
      └──out_of_scope──────────────────────────────────────────────► respond_not_found
```

### C.3 Layering rule

```
interfaces   cli/  api/  ui/          (talk to services only; ui talks to the API over HTTP)
services     services/  ingest/pipeline.py  retrieval/search.py  graph/
domain       chunkers  edges  sparse  fusion  router  citations  metrics
adapters     retrieval/store.py (Qdrant)  db/ (Postgres)  graph/llm.py (LLM providers)
```

Dependencies only point **down**. Adapters sit behind small `Protocol` interfaces
(`Embedder`, `SparseEncoder`, `Reranker`, `LLM`), which is why the tests can swap in fakes.


---

## Phase 0. Fix the foundation

**Goal:** a skeleton that passes `make lint` and `make test`, has every table the project
needs, and has CI from day one.

**Why first:** everything later depends on configuration, the database schema and the
tool chain. Fixing them now is cheap; fixing them after 5,000 lines is not.

```bash
git checkout -b phase-0-foundation
```

### Step 0.1: Dependencies (`pyproject.toml`)

**What:** add the libraries for every later phase, pin the fast-moving ones exactly, and
fix the ruff `exclude` bug.

**Why each new dependency exists:**

| Package | Used for | Why pinned exactly (`==`) |
|---|---|---|
| `qdrant-client==1.19.1` | Talking to Qdrant; also an in-memory "local mode" for tests | Must match the Qdrant server's minor version |
| `fastembed==0.8.1` | CPU embeddings (ONNX), BM25 sparse vectors, cross-encoder reranker | Its model list and APIs change between releases |
| `langgraph==1.2.12`, `langchain-core==1.6.6` | The question-answering state machine | LangGraph APIs changed a lot before 1.0 |
| `langchain-groq`, `langchain-google-genai`, `langchain-ollama` | One chat-model interface over three providers | Same reason |
| `httpx` | The Streamlit UI calls the API | |
| `pyyaml` | Evaluation datasets are YAML | |
| `psycopg[binary]` | Postgres driver that ships its own `libpq` | Works in a slim Docker image without system packages |
| `types-pyyaml` (dev) | Type hints for `yaml`, so strict mypy passes | |

**How:** run this once. `uv add` edits `pyproject.toml` *and* updates `uv.lock`:

```bash
uv add "qdrant-client==1.19.1" "fastembed==0.8.1" "langgraph==1.2.12" \
       "langchain-core==1.6.6" "langchain-groq==1.1.3" "langchain-google-genai==4.4.0" \
       "langchain-ollama==1.1.0" "httpx==0.28.1" "pyyaml==6.0.3" "psycopg[binary]>=3.3.5"
uv add --dev "types-pyyaml>=6.0.12"
```

(`uv add "psycopg[binary]..."` replaces the existing `psycopg` line; you do not need to
remove it first.)

Then edit the rest by hand so the file matches this complete version. Note the three hand
edits: the `description`, `extend-exclude` instead of `exclude`, and the pytest/coverage
settings at the bottom.

<!-- file: pyproject.toml -->
**`pyproject.toml`**

```toml
[project]
name = "codeqa"
version = "0.1.0"
description = "Ask questions about a Python codebase; answers cite exact file:line sources."
readme = "README.md"
authors = [
    { name = "shopnil13", email = "rifat.shopnil13@gmail.com" }
]
requires-python = ">=3.12"
dependencies = [
    "alembic>=1.20.0",
    "fastapi>=0.141.1",
    "fastembed==0.8.1",
    "httpx==0.28.1",
    "langchain-core==1.6.6",
    "langchain-google-genai==4.4.0",
    "langchain-groq==1.1.3",
    "langchain-ollama==1.1.0",
    "langgraph==1.2.12",
    "pathspec>=1.1.1",
    "psycopg[binary]>=3.3.5",
    "pydantic>=2.13.5",
    "pydantic-settings>=2.15.0",
    "pyyaml==6.0.3",
    "qdrant-client==1.19.1",
    "rich>=15.0.0",
    "sqlalchemy>=2.0.52",
    "streamlit>=1.63.0",
    "structlog>=26.1.0",
    "tree-sitter>=0.26.0",
    "tree-sitter-python>=0.25.0",
    "typer>=0.27.2",
    "uvicorn>=0.52.4",
]

[project.scripts]
codeqa = "codeqa.cli.main:main"

[build-system]
requires = ["uv_build>=0.12.8,<0.13.0"]
build-backend = "uv_build"

[dependency-groups]
dev = [
    "mypy>=2.3.1",
    "pre-commit>=4.6.2",
    "pytest>=9.1.1",
    "pytest-cov>=7.1.0",
    "ruff>=0.16.7",
    "types-pyyaml>=6.0.12",
]


[tool.ruff]
line-length = 100
target-version = "py312"
extend-exclude = ["tests/fixtures"]


[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.mypy]
python_version = "3.12"
strict = true
ignore_missing_imports = true

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"

[tool.coverage.run]
source = ["codeqa"]
omit = ["*/ui/app.py"]
```


**Why `extend-exclude`:** ruff has a built-in exclude list (`.venv`, `.git`, `build`, ...).
`exclude = [...]` *replaces* that list; `extend-exclude = [...]` *adds* to it. Your
current setup only works because ruff also honours `.gitignore` inside a git checkout.

**Check:**

```bash
uv sync
uv run python -c "import qdrant_client, fastembed, langgraph; print('ok')"
```

### Step 0.2: Make `make lint` green

**What:** let ruff reformat the four files it complained about.

**Why:** a red linter trains you to ignore it. Fix it now; CI will enforce it later.

```bash
uv run ruff format .
make lint
```

Most of those files are rewritten later in this phase anyway; this just gets you to green.

### Step 0.3: Settings (`src/codeqa/config.py`)

**What:** one typed object holding every configuration value, read from environment
variables and `.env`.

**Why:** the "twelve-factor" rule: configuration lives in the environment, never in code.
Every other module asks `get_settings()` instead of reading `os.environ`, so there is
exactly one place to see what can be configured.

**What changed from your version:**

- `environment` now reads `APP_ENV` (or `ENVIRONMENT`) through `validation_alias`.
- Every key in `.env.example` now has a field. API keys are `SecretStr`, so they print as
  `**********` in logs and tracebacks.
- `DATABASE_URL` can override the individual Postgres fields (Docker and tests use this).
- `QDRANT_LOCATION` switches Qdrant to embedded mode (`:memory:` for tests).
- `postgres_port` defaults to `5433`, matching `docker-compose.yml`.
- `llm_provider` is a `Literal`, so a typo such as `LLM_PROVIDER=grok` fails at startup
  with a clear message instead of failing later inside a request.

<!-- file: src/codeqa/config.py -->
**`src/codeqa/config.py`**

```python
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and `.env`."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "CodeQA"
    environment: Literal["development", "production", "test"] = Field(
        default="development",
        validation_alias=AliasChoices("APP_ENV", "ENVIRONMENT"),
    )
    log_level: str = "INFO"

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5433
    postgres_db: str = "codeqa"
    postgres_user: str = "codeqa"
    postgres_password: str = "codeqa"
    database_url_override: str | None = Field(default=None, validation_alias="DATABASE_URL")

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_location: str | None = None  # ":memory:" or a folder path = embedded local mode
    qdrant_collection: str = "codeqa_chunks"

    # Ingestion
    max_file_size_mb: float = 1.0
    max_repo_chunks: int = 100_000
    cache_dir: Path = Path(".cache/codeqa")
    # If set, the API only indexes local folders inside this directory.
    local_index_root: Path | None = None

    # Embeddings
    embedding_model: str = "jinaai/jina-embeddings-v2-base-code"
    sparse_model: str = "Qdrant/bm25"
    embedding_batch_size: int = 32
    model_cache_dir: Path = Path(".cache/models")

    # Reranker and evidence gate
    reranker_enabled: bool = False
    reranker_model: str = "jinaai/jina-reranker-v1-tiny-en"
    evidence_threshold: float = 0.0

    # LLM
    llm_provider: Literal["groq", "gemini", "ollama", "fake"] = "groq"
    llm_model: str = ""  # empty string = use the provider default from llm.py
    llm_temperature: float = 0.0
    llm_timeout_s: float = 60.0
    groq_api_key: SecretStr | None = None
    google_api_key: SecretStr | None = None
    ollama_base_url: str = "http://localhost:11434"

    # RAG
    retrieval_top_k: int = 30
    final_context_k: int = 6
    max_context_tokens: int = 6000
    prompt_version: str = "v1"

    # Web UI -> API
    api_base_url: str = "http://localhost:8000"

    @property
    def database_url(self) -> str:
        """PostgreSQL connection URL. `DATABASE_URL` wins if set (tests, Docker)."""

        if self.database_url_override:
            return self.database_url_override
        return (
            f"postgresql+psycopg://"
            f"{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}"
            f"/{self.postgres_db}"
        )

    @property
    def qdrant_url(self) -> str:
        """Build the Qdrant connection URL."""

        return f"http://{self.qdrant_host}:{self.qdrant_port}"


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings."""

    return Settings()
```


**Check:**

```bash
uv run python -c "from codeqa.config import get_settings as g; s=g(); print(s.environment, s.database_url)"
```

### Step 0.4: Environment template (`.env.example`) and your `.env`

**What:** a documented list of every setting, with safe defaults and no secrets.

**Why:** a new developer (or a reviewer) copies it to `.env` and the project runs. `.env`
itself is gitignored because it will hold your API keys.

<!-- file: .env.example -->
**`.env.example`**

```bash
# Copy to .env and fill in. Never commit .env.
APP_ENV=development
LOG_LEVEL=INFO

# PostgreSQL (docker compose maps container 5432 -> host 5433)
POSTGRES_HOST=localhost
POSTGRES_PORT=5433
POSTGRES_DB=codeqa
POSTGRES_USER=codeqa
POSTGRES_PASSWORD=codeqa
# DATABASE_URL=postgresql+psycopg://codeqa:codeqa@localhost:5433/codeqa   # overrides the above

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION=codeqa_chunks
# QDRANT_LOCATION=:memory:        # embedded mode, no server (tests)

# Ingestion
MAX_FILE_SIZE_MB=1
MAX_REPO_CHUNKS=100000
CACHE_DIR=.cache/codeqa
# LOCAL_INDEX_ROOT=/path/to/repos # API may only index local folders inside this one

# Embeddings
EMBEDDING_MODEL=jinaai/jina-embeddings-v2-base-code
SPARSE_MODEL=Qdrant/bm25
EMBEDDING_BATCH_SIZE=32
MODEL_CACHE_DIR=.cache/models

# Reranker + evidence gate (calibrate with: make calibrate)
RERANKER_ENABLED=false
RERANKER_MODEL=jinaai/jina-reranker-v1-tiny-en
EVIDENCE_THRESHOLD=0.0

# LLM: groq | gemini | ollama | fake
LLM_PROVIDER=groq
LLM_MODEL=
LLM_TEMPERATURE=0.0
LLM_TIMEOUT_S=60
GROQ_API_KEY=
GOOGLE_API_KEY=
OLLAMA_BASE_URL=http://localhost:11434

# RAG
RETRIEVAL_TOP_K=30
FINAL_CONTEXT_K=6
MAX_CONTEXT_TOKENS=6000
PROMPT_VERSION=v1

# Web UI
API_BASE_URL=http://localhost:8000
```


```bash
cp .env.example .env     # then put your GROQ_API_KEY (or GOOGLE_API_KEY) in .env
```

> **Security:** never commit `.env`. It is already in `.gitignore`; check with
> `git check-ignore .env` (it should print `.env`).

### Step 0.5: Logging (`src/codeqa/logging.py`)

**What:** structured logs with `structlog`: pretty coloured lines in development, one
JSON object per line in production.

**Why:** JSON logs can be searched and aggregated ("show all queries slower than 2 s").
`merge_contextvars` lets the API attach a `request_id` to every log line of one request.
Logs now go to **stderr**, so they never mix with CLI output or `--json` output on stdout.

<!-- file: src/codeqa/logging.py -->
**`src/codeqa/logging.py`**

```python
import logging
import sys
from typing import Any

import structlog

from codeqa.config import get_settings


def configure_logging() -> None:
    """Configure structlog: JSON in production, pretty console in development.

    Logs go to stderr so they never mix with CLI output (stdout) or `--json` results.
    """

    settings = get_settings()
    level = logging.getLevelNamesMapping().get(settings.log_level.upper(), logging.INFO)

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,  # adds request_id etc. bound per request
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]
    if settings.environment == "production":
        processors += [structlog.processors.dict_tracebacks, structlog.processors.JSONRenderer()]
    else:
        processors += [structlog.dev.ConsoleRenderer()]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(sys.stderr),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = "codeqa") -> Any:
    return structlog.get_logger(name)
```


### Step 0.6: Error types and package metadata

**What:** a small exception hierarchy, and a clean package `__init__`.

**Why:** the API needs to turn "repo not found" into a 404 and "bad input" into a 422
without leaking stack traces. Raising `NotFoundError` anywhere in the code and handling
`CodeQAError` in one place (Phase 7) is how that works. The old `main()` in `__init__.py`
was dead code; `__version__` is used by the API.

<!-- file: src/codeqa/errors.py -->
**`src/codeqa/errors.py`**

```python
class CodeQAError(Exception):
    """Base class for errors we expect and can explain to a user."""

    code = "codeqa_error"
    status_code = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(CodeQAError):
    code = "not_found"
    status_code = 404


class InvalidInputError(CodeQAError):
    code = "invalid_input"
    status_code = 422


class UpstreamError(CodeQAError):
    """An external dependency (LLM provider, Qdrant) failed."""

    code = "upstream_error"
    status_code = 502
```


<!-- file: src/codeqa/__init__.py -->
**`src/codeqa/__init__.py`**

```python
"""CodeQA: hybrid-search question answering over Python codebases."""

__version__ = "0.1.0"
```


### Step 0.7: Database sessions (`src/codeqa/db/session.py`)

**What:** create the engine lazily and provide a `session_scope()` context manager.

**Why:**

- **Lazy:** `@lru_cache` builds the engine on first use, not at import time. Importing
  code no longer requires a database; tests pass their own session factory.
- **`session_scope()`:** commit on success, roll back on any exception, always close.
  This is the "unit of work" pattern. It removes a whole class of bugs (forgotten
  commits, leaked connections, half-written data after an error).
- **`expire_on_commit=False`:** objects stay readable after the session closes, which the
  services rely on when they return data.

<!-- file: src/codeqa/db/session.py -->
**`src/codeqa/db/session.py`**

```python
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from codeqa.config import get_settings

SessionFactory = Callable[[], Session]


@lru_cache
def get_engine() -> Engine:
    """Create the engine once, on first use (not at import time)."""

    return create_engine(get_settings().database_url, pool_pre_ping=True)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


@contextmanager
def session_scope(factory: SessionFactory | None = None) -> Iterator[Session]:
    """Open a session, commit on success, roll back on error, always close.

    Usage:
        with session_scope() as session:
            session.add(obj)
    """

    session = (factory or get_session_factory())()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```


### Step 0.8: The data model (`src/codeqa/models/`)

**What:** fix the four existing models and add the four missing ones.

**Why each change:**

- **`Uuid` instead of `postgresql.UUID`:** SQLAlchemy's generic `Uuid` is still a native
  `UUID` column on Postgres, but also works on SQLite, so the test suite runs without
  Docker.
- **`JSONType`:** `JSONB` on Postgres (binary, indexable), plain `JSON` elsewhere.
- **`DateTime(timezone=True)` + `utcnow()`:** timezone-aware timestamps. Naive datetimes
  are a classic source of "off by N hours" bugs.
- **Named unique constraints:** `uq_repositories_name` and `uq_files_repo_path` stop
  duplicates. They are *named* because Alembic cannot drop an unnamed constraint in a
  downgrade.
- **`source_url` nullable:** local folders have no URL.
- **`chunker`, `embedding_model`, `collection_name` on `repositories`:** record how a
  repo was indexed, so search uses the matching model and collection.
- **`part_index` on `chunks`:** which piece of a split function this is.
- **Indexes** on foreign keys and names: the dependency lookups query by `target_name`,
  `symbol_name` and `file_id` constantly.
- **New tables:** `symbol_edges` (call graph), `query_logs` (observability),
  `feedback` (thumbs up/down), `eval_runs` (reproducible evaluation history).

<!-- file: src/codeqa/models/base.py -->
**`src/codeqa/models/base.py`**

```python
from datetime import UTC, datetime

from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase

# JSONB on Postgres (indexable, fast), plain JSON elsewhere (e.g. SQLite in tests).
JSONType = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    """Timezone-aware 'now'. `datetime.utcnow()` is deprecated since Python 3.12."""

    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass
```


<!-- file: src/codeqa/models/repository.py -->
**`src/codeqa/models/repository.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from codeqa.models.base import Base, utcnow


class Repository(Base):
    __tablename__ = "repositories"
    __table_args__ = (UniqueConstraint("name", name="uq_repositories_name"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    source_url: Mapped[str | None] = mapped_column(String, nullable=True)
    local_path: Mapped[str] = mapped_column(String, nullable=False)
    commit_sha: Mapped[str] = mapped_column(String, nullable=False, default="")
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    last_indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # How this repo was indexed. Search must use the same settings to query it.
    chunker: Mapped[str] = mapped_column(String, nullable=False, default="ast")
    embedding_model: Mapped[str] = mapped_column(String, nullable=False, default="")
    collection_name: Mapped[str] = mapped_column(String, nullable=False, default="")
```


<!-- file: src/codeqa/models/file.py -->
**`src/codeqa/models/file.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from codeqa.models.base import Base


class File(Base):
    __tablename__ = "files"
    __table_args__ = (UniqueConstraint("repository_id", "path", name="uq_files_repo_path"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("repositories.id"), nullable=False, index=True
    )
    path: Mapped[str] = mapped_column(String, nullable=False)
    language: Mapped[str | None] = mapped_column(String)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False, default=0)
    indexed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```


<!-- file: src/codeqa/models/chunk.py -->
**`src/codeqa/models/chunk.py`**

```python
import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from codeqa.models.base import Base


class Chunk(Base):
    __tablename__ = "chunks"

    # Not auto-generated: we compute a deterministic uuid5 (see ingest/ids.py) so the
    # same chunk gets the same id in Postgres and Qdrant on every re-index.
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    file_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("files.id"), nullable=False, index=True
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("repositories.id"), nullable=False, index=True
    )
    kind: Mapped[str] = mapped_column(String, nullable=False)
    symbol_name: Mapped[str | None] = mapped_column(String, index=True)
    qualified_name: Mapped[str | None] = mapped_column(String, index=True)
    parent_name: Mapped[str | None] = mapped_column(String)
    signature: Mapped[str | None] = mapped_column(Text)
    docstring: Mapped[str | None] = mapped_column(Text)
    start_line: Mapped[int] = mapped_column(Integer, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, nullable=False)
    part_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer)
    content_hash: Mapped[str | None] = mapped_column(String)
```


<!-- file: src/codeqa/models/index_job.py -->
**`src/codeqa/models/index_job.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from codeqa.models.base import Base


class IndexJob(Base):
    __tablename__ = "index_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("repositories.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    files_processed: Mapped[int] = mapped_column(nullable=False, default=0)
    chunks_created: Mapped[int] = mapped_column(nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(String)
```


<!-- file: src/codeqa/models/symbol_edge.py -->
**`src/codeqa/models/symbol_edge.py`**

```python
import uuid

from sqlalchemy import ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from codeqa.models.base import Base


class SymbolEdge(Base):
    """One best-effort call or import relationship: `source_chunk` calls/imports `target_name`."""

    __tablename__ = "symbol_edges"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    repository_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("repositories.id"), nullable=False, index=True
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("files.id"), nullable=False, index=True
    )
    source_chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("chunks.id"), index=True
    )
    source_name: Mapped[str] = mapped_column(String, nullable=False)
    target_name: Mapped[str] = mapped_column(String, nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String, nullable=False)  # "call" | "import"
    target_chunk_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("chunks.id"), index=True
    )
```


**Why `symbol_edges` stores `target_name` as text *and* a nullable `target_chunk_id`:**
while indexing file A, the function it calls may live in file B that is not indexed yet.
So we store the *name* first and resolve it to a chunk id after all files are written.
Names that stay ambiguous stay `NULL`: honest, and good enough.

<!-- file: src/codeqa/models/query_log.py -->
**`src/codeqa/models/query_log.py`**

```python
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from codeqa.models.base import Base, JSONType, utcnow


class QueryLog(Base):
    __tablename__ = "query_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    repository_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("repositories.id"), index=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    route: Mapped[str | None] = mapped_column(String)
    retrieved_chunk_ids: Mapped[list[str]] = mapped_column(JSONType, nullable=False, default=list)
    answer: Mapped[str | None] = mapped_column(Text)
    citations: Mapped[list[dict[str, Any]]] = mapped_column(JSONType, nullable=False, default=list)
    grounded: Mapped[bool | None]
    stage_latency_ms: Mapped[dict[str, float]] = mapped_column(
        JSONType, nullable=False, default=dict
    )
    model: Mapped[str | None] = mapped_column(String)
    prompt_version: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
```


<!-- file: src/codeqa/models/feedback.py -->
**`src/codeqa/models/feedback.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from codeqa.models.base import Base, utcnow


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    query_log_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("query_logs.id"), nullable=False, index=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # +1 or -1
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
```


<!-- file: src/codeqa/models/eval_run.py -->
**`src/codeqa/models/eval_run.py`**

```python
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from codeqa.models.base import Base, JSONType, utcnow


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String, nullable=False)  # "retrieval" | "generation"
    config: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    dataset: Mapped[str] = mapped_column(String, nullable=False)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    git_sha: Mapped[str] = mapped_column(String, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
```


<!-- file: src/codeqa/models/__init__.py -->
**`src/codeqa/models/__init__.py`**

```python
from codeqa.models.base import Base
from codeqa.models.chunk import Chunk
from codeqa.models.eval_run import EvalRun
from codeqa.models.feedback import Feedback
from codeqa.models.file import File
from codeqa.models.index_job import IndexJob
from codeqa.models.query_log import QueryLog
from codeqa.models.repository import Repository
from codeqa.models.symbol_edge import SymbolEdge

__all__ = [
    "Base",
    "Chunk",
    "EvalRun",
    "Feedback",
    "File",
    "IndexJob",
    "QueryLog",
    "Repository",
    "SymbolEdge",
]
```


**Why `__init__.py` imports every model:** Alembic's autogenerate compares the database
with `Base.metadata`. A model that is never imported is never registered on the metadata,
so Alembic would not see it.

### Step 0.9: The migration

**What:** a second Alembic migration that brings the database from your first migration
to the new model.

**Why a new migration instead of editing the old one:** your first migration may already
be applied to your database. Rule: **never edit a migration that has been applied
anywhere**; add a new one. That is what makes migrations safe to run on any copy of the
database.

**Step 1. See what Alembic detects.** Start the database and let Alembic compare:

```bash
make up                      # starts postgres + qdrant (Step 0.11 improves the compose file)
make migrate                 # applies your first migration if not already applied
uv run alembic revision --autogenerate -m "add edges logs feedback eval runs"
```

Open the generated file in `migrations/versions/`. Autogenerate is a *draft*. Review it
and you will find two real problems:

1. `op.add_column("chunks", sa.Column("part_index", ..., nullable=False))` has no default.
   On a table that already has rows, Postgres refuses: existing rows would have no value.
   **Fix:** add `server_default="0"` (and `""` for the new string columns).
2. The timestamp columns change from `TIMESTAMP` to `TIMESTAMP WITH TIME ZONE`. Postgres
   needs to know how to interpret the old naive values. **Fix:** `postgresql_using=
   "<column> AT TIME ZONE 'UTC'"`.

(If you had kept `unique=True` on `name`, you would see a third problem: an unnamed
constraint that the downgrade cannot drop. That is why the model names it.)

**Step 2. Replace the draft with the reviewed version.** Delete the generated file and
create this one. The revision id `9b1e2f3a4c5d` is just a unique label; `down_revision`
points at your first migration.

```bash
rm migrations/versions/*add_edges_logs_feedback_eval_runs.py
```

<!-- file: migrations/versions/9b1e2f3a4c5d_add_edges_logs_feedback_eval_runs.py -->
**`migrations/versions/9b1e2f3a4c5d_add_edges_logs_feedback_eval_runs.py`**

```python
"""add symbol_edges, query_logs, feedback, eval_runs; harden existing tables

Revision ID: 9b1e2f3a4c5d
Revises: 4c17dc428a8e
Create Date: 2026-09-30 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "9b1e2f3a4c5d"
down_revision: str | Sequence[str] | None = "4c17dc428a8e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSONB = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
TZ_COLUMNS = [
    ("repositories", "created_at", False),
    ("repositories", "last_indexed_at", True),
    ("files", "indexed_at", True),
    ("index_jobs", "started_at", True),
    ("index_jobs", "finished_at", True),
]


def upgrade() -> None:
    """Upgrade schema."""
    # --- new tables -------------------------------------------------------
    op.create_table(
        "eval_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("config", JSONB, nullable=False),
        sa.Column("dataset", sa.String(), nullable=False),
        sa.Column("metrics", JSONB, nullable=False),
        sa.Column("git_sha", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "query_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("repository_id", sa.Uuid(), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("route", sa.String(), nullable=True),
        sa.Column("retrieved_chunk_ids", JSONB, nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("citations", JSONB, nullable=False),
        sa.Column("grounded", sa.Boolean(), nullable=True),
        sa.Column("stage_latency_ms", JSONB, nullable=False),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("prompt_version", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_query_logs_repository_id", "query_logs", ["repository_id"])
    op.create_table(
        "feedback",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("query_log_id", sa.Uuid(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["query_log_id"], ["query_logs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feedback_query_log_id", "feedback", ["query_log_id"])
    op.create_table(
        "symbol_edges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("repository_id", sa.Uuid(), nullable=False),
        sa.Column("file_id", sa.Uuid(), nullable=False),
        sa.Column("source_chunk_id", sa.Uuid(), nullable=True),
        sa.Column("source_name", sa.String(), nullable=False),
        sa.Column("target_name", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("target_chunk_id", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["file_id"], ["files.id"]),
        sa.ForeignKeyConstraint(["repository_id"], ["repositories.id"]),
        sa.ForeignKeyConstraint(["source_chunk_id"], ["chunks.id"]),
        sa.ForeignKeyConstraint(["target_chunk_id"], ["chunks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("file_id", "repository_id", "source_chunk_id", "target_chunk_id", "target_name"):
        op.create_index(f"ix_symbol_edges_{column}", "symbol_edges", [column])

    # --- new columns on existing tables ------------------------------------
    # server_default lets Postgres fill existing rows; without it, adding a
    # NOT NULL column to a non-empty table fails.
    op.add_column(
        "chunks", sa.Column("part_index", sa.Integer(), nullable=False, server_default="0")
    )
    for column in ("chunker", "embedding_model", "collection_name"):
        op.add_column(
            "repositories", sa.Column(column, sa.String(), nullable=False, server_default="")
        )

    # --- indexes and constraints -------------------------------------------
    op.create_index("ix_chunks_file_id", "chunks", ["file_id"])
    op.create_index("ix_chunks_repository_id", "chunks", ["repository_id"])
    op.create_index("ix_chunks_qualified_name", "chunks", ["qualified_name"])
    op.create_index("ix_chunks_symbol_name", "chunks", ["symbol_name"])
    op.create_index("ix_files_repository_id", "files", ["repository_id"])
    op.create_index("ix_index_jobs_repository_id", "index_jobs", ["repository_id"])
    op.create_unique_constraint("uq_files_repo_path", "files", ["repository_id", "path"])
    op.create_unique_constraint("uq_repositories_name", "repositories", ["name"])
    op.alter_column("repositories", "source_url", existing_type=sa.VARCHAR(), nullable=True)

    # --- naive timestamps -> timezone-aware (existing values are UTC) --------
    for table, column, nullable in TZ_COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=postgresql.TIMESTAMP(),
            type_=sa.DateTime(timezone=True),
            existing_nullable=nullable,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table, column, nullable in TZ_COLUMNS:
        op.alter_column(
            table,
            column,
            existing_type=sa.DateTime(timezone=True),
            type_=postgresql.TIMESTAMP(),
            existing_nullable=nullable,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )
    op.alter_column("repositories", "source_url", existing_type=sa.VARCHAR(), nullable=False)
    op.drop_constraint("uq_repositories_name", "repositories", type_="unique")
    op.drop_constraint("uq_files_repo_path", "files", type_="unique")
    op.drop_index("ix_index_jobs_repository_id", table_name="index_jobs")
    op.drop_index("ix_files_repository_id", table_name="files")
    op.drop_index("ix_chunks_symbol_name", table_name="chunks")
    op.drop_index("ix_chunks_qualified_name", table_name="chunks")
    op.drop_index("ix_chunks_repository_id", table_name="chunks")
    op.drop_index("ix_chunks_file_id", table_name="chunks")
    for column in ("chunker", "embedding_model", "collection_name"):
        op.drop_column("repositories", column)
    op.drop_column("chunks", "part_index")
    op.drop_table("symbol_edges")
    op.drop_index("ix_feedback_query_log_id", table_name="feedback")
    op.drop_table("feedback")
    op.drop_index("ix_query_logs_repository_id", table_name="query_logs")
    op.drop_table("query_logs")
    op.drop_table("eval_runs")
```


**Step 3. Prove it works both ways, and that models and migrations agree:**

```bash
uv run alembic upgrade head
uv run alembic downgrade -1      # proves the downgrade works
uv run alembic upgrade head
uv run alembic check             # "No new upgrade operations detected." = models == DB
```

`alembic check` is also run in CI: it fails the build if someone changes a model and
forgets the migration.

### Step 0.10: Local services (`docker-compose.yml`)

**What:** pin exact image versions and add healthchecks.

**Why:**

- **Pinned images** (`postgres:16.15`, `qdrant/qdrant:v1.19.1`): "latest" changes under
  you; a pinned tag gives everyone the same database. Qdrant is pinned to the same minor
  version as `qdrant-client`.
- **Healthchecks:** "container started" is not "database accepts connections". Later,
  other services wait for `service_healthy`.

This is the development version (databases only). Phase 8 adds the API and UI.

<!-- file: docker-compose.yml -->
**`docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:16.15
    environment:
      POSTGRES_USER: codeqa
      POSTGRES_PASSWORD: codeqa
      POSTGRES_DB: codeqa
    ports: ["5433:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U codeqa -d codeqa"]
      interval: 5s
      timeout: 3s
      retries: 20

  qdrant:
    image: qdrant/qdrant:v1.19.1   # keep in step with the qdrant-client version
    ports: ["6333:6333"]
    volumes: ["qdrantdata:/qdrant/storage"]
    healthcheck:
      test: ["CMD-SHELL", "bash -c ':> /dev/tcp/127.0.0.1/6333' || exit 1"]
      interval: 5s
      timeout: 3s
      retries: 20

volumes:
  pgdata:
  qdrantdata:
```


> **Upgrading Qdrant from v1.11 to v1.19.** Qdrant only guarantees storage compatibility
> between neighbouring minor versions. You have not stored any vectors yet, so the
> simplest path is to delete the old Qdrant volume. **This permanently deletes the data in
> that volume** (there is none yet):
> ```bash
> docker compose down
> docker volume ls | grep qdrantdata          # find the exact name, e.g. codeqa_qdrantdata
> docker volume rm codeqa_qdrantdata
> make up
> ```
> The Postgres upgrade `16 -> 16.15` is a patch upgrade and keeps its data.

**Check:** `docker compose ps` shows both services as `healthy` after a few seconds.

### Step 0.11: Makefile, `.gitignore`, LICENSE

**What:** a Makefile with every command you will use; one new `.gitignore` entry; an MIT
licence.

**Why:** `make test` is easier to remember (and to put in a README) than the full `uv run`
command. The Makefile already lists targets used in later phases; they simply fail until
those phases exist.

<!-- file: Makefile -->
**`Makefile`**

```makefile
.PHONY: install up down logs stack test cov lint format typecheck migrate api ui \
        eval-retrieval eval-generation calibrate ci

install:            ## install all dependencies + git hooks
	uv sync
	uv run pre-commit install

up:                 ## start Postgres + Qdrant only (for local development)
	docker compose up -d postgres qdrant

stack:              ## build and start everything (db, vector db, api, ui)
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api

migrate:
	uv run alembic upgrade head

test:
	uv run pytest

cov:
	uv run pytest --cov --cov-report=term-missing

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src

format:
	uv run ruff check --fix .
	uv run ruff format .

api:
	uv run uvicorn codeqa.api.main:app --reload --port 8000

ui:
	uv run streamlit run src/codeqa/ui/app.py

eval-retrieval:
	uv run codeqa eval retrieval --config eval/configs/retrieval.yaml

eval-generation:
	uv run codeqa eval generation --dataset eval/datasets/dev_questions.yaml

calibrate:
	uv run codeqa eval calibrate --dataset eval/datasets/dev_questions.yaml

ci: lint test
```


> Makefile recipes must be indented with a **tab**, not spaces. If you see
> `missing separator`, your editor converted the tab.

<!-- file: .gitignore -->
**`.gitignore`**

```gitignore
# Python
__pycache__/
*.py[cod]
*.so

# Virtual environments
.venv/
venv/
env/

# Environment
.env

# Testing
.pytest_cache/
.coverage
htmlcov/

# Type checking
.mypy_cache/

# Ruff
.ruff_cache/

# IDE
.vscode/
.idea/

# OS
.DS_Store

# Models
.cache/

# Application
data/
logs/

# Secrets
*.pem
*.key

# Local repos mounted into the API container (docker compose)
repos/
```


Create `LICENSE` with the standard MIT text (GitHub: *Add file > Create new file >
LICENSE > Choose a license template > MIT*), or:

```bash
curl -s https://raw.githubusercontent.com/licenses/license-templates/master/templates/mit.txt \
  | sed "s/{{ year }}/2026/; s/{{ organization }}/Your Name/" > LICENSE
```

### Step 0.12: Continuous integration (`.github/workflows/ci.yml`)

**What:** on every push and pull request, GitHub runs lint, type-check, migrations and
tests against a real Postgres.

**Why:** CI is the referee. It catches "works on my machine" problems and shows a reviewer
a green badge. Two details worth knowing:

- The `postgres` **service container** gives the job a real database, so the migrations
  and `alembic check` run for real.
- `TEST_DATABASE_URL` makes the test suite use that Postgres instead of SQLite (you will
  write that switch in Phase 2's `conftest.py`).

<!-- file: .github/workflows/ci.yml -->
**`.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16.15
        env:
          POSTGRES_USER: codeqa
          POSTGRES_PASSWORD: codeqa
          POSTGRES_DB: codeqa
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U codeqa"
          --health-interval 5s
          --health-timeout 3s
          --health-retries 20
    env:
      DATABASE_URL: postgresql+psycopg://codeqa:codeqa@localhost:5432/codeqa
    steps:
      - uses: actions/checkout@v7
      - uses: astral-sh/setup-uv@v10
        with:
          enable-cache: true
      - run: uv sync --locked
      - name: Lint
        run: |
          uv run ruff check .
          uv run ruff format --check .
      - name: Type-check
        run: uv run mypy src
      - name: Migrations apply cleanly and match the models
        run: |
          uv run alembic upgrade head
          uv run alembic check
      - name: Tests (against Postgres)
        env:
          TEST_DATABASE_URL: postgresql+psycopg://codeqa:codeqa@localhost:5432/codeqa
        run: uv run pytest --cov --cov-report=term-missing
```


Phase 8 adds a second job that builds the Docker image.

### Phase 0: Definition of Done

```bash
make up && make migrate      # both services healthy, migrations at head
uv run alembic check         # No new upgrade operations detected.
make lint                    # All checks passed! / Success: no issues found
make test                    # 4 passed
```

Commit, push, and check that the CI run on GitHub is green.


---

## Phase 1. Ingestion and AST chunking

**Goal:** turn a Python repository into clean, complete, metadata-rich chunks, plus a
best-effort call graph.

**Why this phase matters most:** retrieval can only return what chunking produced. If a
function is cut in half, or silently dropped, no embedding model can fix it. This is also
your headline differentiator: "structure-aware chunking of code".

```bash
git checkout -b phase-1-chunking
```

### 1.0 Concepts you need first

**Concrete syntax tree (CST).** tree-sitter parses source code into a tree of *nodes*.
Each node has a `type` (`function_definition`, `class_definition`, `block`, `call`, ...),
a position (`start_point` = (row, column), `start_byte`), children, and named *fields*
(`child_by_field_name("name")`, `"body"`, `"parameters"`). Here is a real tree for a
decorated class (printed with the installed grammar):

```
module
  decorated_definition            field: definition
    decorator
    class_definition              fields: name, body
      identifier                  <- the class name
      argument_list               <- (Base)
      block                       <- the body
        expression_statement      <- docstring or attribute
        decorated_definition      <- a decorated method
        class_definition          <- a nested class
  import_from_statement           fields: module_name, name
  expression_statement
    call                          field: function
      attribute                   field: attribute  (obj.method)
```

**Why tree-sitter and not Python's `ast` module?** tree-sitter is *error tolerant*: a file
with a syntax error still produces a tree (with `ERROR` nodes), so one broken file never
crashes indexing. It also has grammars for many languages, so adding TypeScript later is
a new chunker, not a rewrite.

**Bytes vs characters.** tree-sitter positions are **UTF-8 byte offsets**. `"é"` is one
character but two bytes. Slicing a Python `str` with byte offsets corrupts any file with
non-ASCII text. Rule: slice the `bytes`, then decode.

**Rows vs `splitlines()`.** tree-sitter counts rows by `\n` only. Python's
`str.splitlines()` *also* splits on form feed (`\x0c`, common in old Python files),
` ` and others. If you split with `splitlines()` your line numbers drift after the
first form feed. Rule: split on `"\n"` only.

**Chunk units** (from the plan):

| Kind | Content | Why |
|---|---|---|
| `function` | a top-level `def` with its decorators | the natural unit of "what does X do" |
| `method` | a `def` inside a class, named `Class.method` | same, plus the class context |
| `class_skeleton` | class header, docstring, attributes, method *signatures* only | answers "what is this class" without duplicating every body |
| `module` | module docstring, imports, constants, `if __name__ == ...` | top-level code must not vanish |
| `doc_section` | a Markdown section, named by its header path | README/docs answer "how do I..." |
| `fixed` | 60-line window | the baseline for the ablation |

### Step 1.1: The chunk contract (`ingest/chunkers/base.py`)

**What:** the `Chunk` dataclass every chunker returns, the `Chunker` protocol, and a safe
line splitter.

**Why:**

- A single contract means the pipeline does not care which chunker produced a chunk.
- `token_count` is now `field(init=False)`: it is always *computed* in `__post_init__`.
  When the AST chunker creates split parts with `dataclasses.replace()`, the count is
  recomputed for each part instead of being copied from the whole function.
- `split_lines()` implements the "`\n` only" rule from 1.0 in one place.

<!-- file: src/codeqa/ingest/chunkers/base.py -->
**`src/codeqa/ingest/chunkers/base.py`**

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol


@dataclass
class Chunk:
    kind: str  # "function" | "method" | "class_skeleton" | "module" | "doc_section" | "fixed"
    symbol_name: str | None
    qualified_name: str | None
    parent_name: str | None
    signature: str | None
    docstring: str | None
    start_line: int  # 1-based, inclusive
    end_line: int  # 1-based, inclusive
    content: str
    part_index: int = 0
    # Computed, never passed in: `dataclasses.replace()` then recomputes it for split parts.
    token_count: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        # ~4 characters per token is a good-enough estimate for English and code.
        self.token_count = max(1, len(self.content) // 4)


class Chunker(Protocol):
    def chunk_file(self, path: Path, source: bytes) -> list[Chunk]: ...


def split_lines(source: bytes) -> list[str]:
    """Decode and split on '\\n' only.

    tree-sitter counts rows by '\\n'. `str.splitlines()` also splits on form feeds,
    '\\u2028' and friends, which would shift every line number after them.
    """

    text = source.decode("utf-8", errors="replace")
    return [line.removesuffix("\r") for line in text.split("\n")]
```


### Step 1.2: Fixed-size baseline (`ingest/chunkers/fixed.py`)

**What:** 60-line windows with 10 lines of overlap.

**Why keep a "bad" chunker?** It is your *control group*. "AST chunking beats fixed
chunking by X points of Recall@5" is only a claim if you measured the fixed version.
**Change:** empty files now return no chunks, and it uses `split_lines()`.

<!-- file: src/codeqa/ingest/chunkers/fixed.py -->
**`src/codeqa/ingest/chunkers/fixed.py`**

```python
from pathlib import Path

from codeqa.ingest.chunkers.base import Chunk, split_lines

CHUNK_LINES = 60
OVERLAP_LINES = 10


class FixedSizeChunker:
    """Naive baseline: windows of 60 lines with 10 lines of overlap.

    Kept on purpose. The evaluation compares it against AST chunking.
    """

    def chunk_file(self, path: Path, source: bytes) -> list[Chunk]:
        lines = split_lines(source)
        if not any(line.strip() for line in lines):
            return []

        chunks: list[Chunk] = []
        start = 0
        part_index = 0
        while start < len(lines):
            end = min(start + CHUNK_LINES, len(lines))
            chunks.append(
                Chunk(
                    kind="fixed",
                    symbol_name=None,
                    qualified_name=None,
                    parent_name=None,
                    signature=None,
                    docstring=None,
                    start_line=start + 1,
                    end_line=end,
                    content="\n".join(lines[start:end]),
                    part_index=part_index,
                )
            )
            if end == len(lines):
                break
            start = end - OVERLAP_LINES
            part_index += 1

        return chunks
```


### Step 1.3: Markdown chunker (`ingest/chunkers/markdown.py`)

**What:** one chunk per header section; the chunk's name is the header path
(`Guide > Install`).

**Why the changes:**

- **Header path, not just the header:** "Install" appears in many READMEs; "Docker >
  Install" says where you are.
- **Code fences:** a `# comment` inside a fenced code block is not a header. The old
  version split sections there.
- **Long sections** are windowed at 120 lines so no chunk becomes huge.

<!-- file: src/codeqa/ingest/chunkers/markdown.py -->
**`src/codeqa/ingest/chunkers/markdown.py`**

````python
import re
from pathlib import Path

from codeqa.ingest.chunkers.base import Chunk, split_lines

HEADER = re.compile(r"^(#{1,6})\s+(.*)$")
MAX_SECTION_LINES = 120


class MarkdownChunker:
    """One chunk per header section. The chunk name is the header path, e.g. `Install > Docker`."""

    def chunk_file(self, path: Path, source: bytes) -> list[Chunk]:
        lines = split_lines(source)
        chunks: list[Chunk] = []
        header_stack: list[tuple[int, str]] = []  # (level, title)
        section_start = 1
        in_code_fence = False

        def flush(end_line: int) -> None:
            body = lines[section_start - 1 : end_line]
            if not any(line.strip() for line in body):
                return
            header_path = " > ".join(title for _, title in header_stack) or None
            # Very long sections are cut into windows so no chunk gets huge.
            for offset in range(0, len(body), MAX_SECTION_LINES):
                window = body[offset : offset + MAX_SECTION_LINES]
                chunks.append(
                    Chunk(
                        kind="doc_section",
                        symbol_name=header_stack[-1][1] if header_stack else None,
                        qualified_name=header_path,
                        parent_name=None,
                        signature=None,
                        docstring=None,
                        start_line=section_start + offset,
                        end_line=section_start + offset + len(window) - 1,
                        content="\n".join(window),
                        part_index=offset // MAX_SECTION_LINES,
                    )
                )

        for number, line in enumerate(lines, start=1):
            if line.lstrip().startswith("```"):
                in_code_fence = not in_code_fence  # '# comment' inside code is not a header
            match = None if in_code_fence else HEADER.match(line)
            if match is None:
                continue
            flush(number - 1)
            level, title = len(match.group(1)), match.group(2).strip()
            while header_stack and header_stack[-1][0] >= level:
                header_stack.pop()
            header_stack.append((level, title))
            section_start = number

        flush(len(lines))
        return chunks
````


### Step 1.4: The AST chunker (`ingest/chunkers/python_ast.py`), the centrepiece

**What:** the rewritten tree-sitter chunker.

**Why each fix (see audit items 10 to 15):**

1. **Correct line ranges for split parts.** Each part gets the lines of the statements it
   contains, so a citation points at the right 30 lines, not the whole 400-line function.
2. **Split at statement boundaries.** `_split_function` groups whole body statements
   until the size limit, instead of cutting at a character count. Part 0 keeps the
   decorators and signature; later parts start with the signature plus `# (continued)`,
   so each part still reads as "a piece of function X".
3. **Nested classes** are handled recursively; their methods become `Outer.Inner.ping`.
4. **Module chunks keep everything top-level** that is not a function or class, including
   `if __name__ == "__main__":`, `try:` import fallbacks, and `ERROR` nodes from files
   with syntax errors. Nothing is dropped.
5. **Docstrings** are cleaned properly: string prefixes (`r`, `b`, `u`, `f`) removed, then
   `inspect.cleandoc()` removes indentation, exactly as Python's `help()` does.
6. **Class skeleton includes attributes** (`timeout: float = 5.0`) and decorated method
   signatures (`@property def name(self): ...`).
7. **Content is built from whole lines** (`lines[start - 1 : end]`), so methods keep their
   indentation and the text matches the file exactly at those line numbers.
8. **One `Parser` per chunker instance**, not per file.

How to read the file: `chunk_file()` walks the top-level nodes of the module. Functions go
to `_function_chunks()`, classes to `_class_chunks()` (which recurses into members), and
everything else is collected for `_module_chunks()`. `_unwrap()` is the trick that keeps
decorators: for a `decorated_definition` node we *chunk the outer node* (so the text
starts at `@decorator`) but *read the name and body from the inner definition*.

<!-- file: src/codeqa/ingest/chunkers/python_ast.py -->
**`src/codeqa/ingest/chunkers/python_ast.py`**

```python
import inspect
from dataclasses import replace
from pathlib import Path

import tree_sitter_python as tspython
from tree_sitter import Language, Node, Parser

from codeqa.ingest.chunkers.base import Chunk, split_lines

PY_LANGUAGE = Language(tspython.language())
MAX_CHUNK_CHARS = 4000  # ~1,000 tokens
MAX_SKELETON_CHARS = 4000
DEFINITION_TYPES = ("function_definition", "class_definition")


def _text(node: Node, source: bytes) -> str:
    # tree-sitter offsets are UTF-8 *byte* offsets: slice bytes first, then decode.
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _span(node: Node) -> tuple[int, int]:
    """1-based inclusive (start_line, end_line)."""

    return node.start_point[0] + 1, node.end_point[0] + 1


def _unwrap(node: Node) -> Node | None:
    """Return the function/class inside a `decorated_definition`, or the node itself."""

    if node.type == "decorated_definition":
        return node.child_by_field_name("definition")
    return node if node.type in DEFINITION_TYPES else None


def _name(definition: Node, source: bytes) -> str:
    name_node = definition.child_by_field_name("name")
    return _text(name_node, source) if name_node is not None else "<anonymous>"


def _header(outer: Node, definition: Node, source: bytes) -> str:
    """Decorators + `def`/`class` line(s), up to the colon. Excludes the body."""

    body = definition.child_by_field_name("body")
    end = body.start_byte if body is not None else definition.end_byte
    return source[outer.start_byte : end].decode("utf-8", errors="replace").rstrip()


def _signature(definition: Node, source: bytes) -> str:
    """`def name(args) -> ret:` without decorators and without the body."""

    return _header(definition, definition, source)


def _clean_docstring(raw: str) -> str:
    text = raw.lstrip("rRbBuUfF")
    for quote in ('"""', "'''", '"', "'"):
        if text.startswith(quote) and text.endswith(quote) and len(text) >= 2 * len(quote):
            text = text[len(quote) : -len(quote)]
            break
    return inspect.cleandoc(text)


def _docstring_node(block: Node | None) -> Node | None:
    if block is None:
        return None
    statements = [c for c in block.named_children if c.type != "comment"]
    if not statements:
        return None
    first = statements[0]
    if first.type == "expression_statement" and first.named_children:
        if first.named_children[0].type == "string":
            return first
    return None


def _docstring(block: Node | None, source: bytes) -> str | None:
    node = _docstring_node(block)
    if node is None:
        return None
    return _clean_docstring(_text(node.named_children[0], source)) or None


class PythonASTChunker:
    """Split a Python file into semantic chunks using tree-sitter.

    Emits:
      - `function`: a top-level `def` (with its decorators)
      - `method`: a `def` inside a class; `qualified_name` is `Class.method`
      - `class_skeleton`: class header, docstring, attributes and method *signatures*
      - `module`: module docstring, imports and other top-level statements
    Oversized functions are split at statement boundaries into parts.
    """

    def __init__(self, max_chunk_chars: int = MAX_CHUNK_CHARS) -> None:
        self._parser = Parser(PY_LANGUAGE)
        self._max_chars = max_chunk_chars

    def chunk_file(self, path: Path, source: bytes) -> list[Chunk]:
        tree = self._parser.parse(source)
        lines = split_lines(source)
        chunks: list[Chunk] = []
        module_statements: list[Node] = []

        for child in tree.root_node.children:
            definition = _unwrap(child)
            if definition is None:
                module_statements.append(child)
            elif definition.type == "function_definition":
                chunks.extend(self._function_chunks(child, definition, source, lines, None))
            else:
                chunks.extend(self._class_chunks(child, definition, source, lines, None))

        chunks.extend(self._module_chunks(module_statements, source))
        return chunks

    # ------------------------------------------------------------------ functions

    def _function_chunks(
        self,
        outer: Node,
        definition: Node,
        source: bytes,
        lines: list[str],
        parent: str | None,
    ) -> list[Chunk]:
        name = _name(definition, source)
        body = definition.child_by_field_name("body")
        start, end = _span(outer)
        whole = Chunk(
            kind="method" if parent else "function",
            symbol_name=name,
            qualified_name=f"{parent}.{name}" if parent else name,
            parent_name=parent,
            signature=_signature(definition, source),
            docstring=_docstring(body, source),
            start_line=start,
            end_line=end,
            content="\n".join(lines[start - 1 : end]),
        )
        if len(whole.content) <= self._max_chars or body is None:
            return [whole]
        return self._split_function(whole, definition, body, lines)

    def _split_function(
        self, whole: Chunk, definition: Node, body: Node, lines: list[str]
    ) -> list[Chunk]:
        """Group body statements into parts under the size limit.

        Part 0 keeps decorators + signature. Later parts start with the signature line
        so that each part still reads as "a piece of function X".
        """

        groups: list[list[Node]] = []
        current: list[Node] = []
        size = 0
        for statement in body.named_children:
            length = statement.end_byte - statement.start_byte
            if current and size + length > self._max_chars:
                groups.append(current)
                current, size = [], 0
            current.append(statement)
            size += length
        if current:
            groups.append(current)

        indent = " " * definition.start_point[1]
        header = f"{indent}{whole.signature}  # (continued)"
        parts: list[Chunk] = []
        for index, group in enumerate(groups):
            start = whole.start_line if index == 0 else _span(group[0])[0]
            end = whole.end_line if index == len(groups) - 1 else _span(group[-1])[1]
            text = "\n".join(lines[start - 1 : end])
            parts.append(
                replace(
                    whole,
                    content=text if index == 0 else f"{header}\n{text}",
                    start_line=start,
                    end_line=end,
                    part_index=index,
                    docstring=whole.docstring if index == 0 else None,
                )
            )
        return parts

    # -------------------------------------------------------------------- classes

    def _class_chunks(
        self,
        outer: Node,
        definition: Node,
        source: bytes,
        lines: list[str],
        parent: str | None,
    ) -> list[Chunk]:
        name = _name(definition, source)
        qualified = f"{parent}.{name}" if parent else name
        body = definition.child_by_field_name("body")

        chunks: list[Chunk] = []
        skeleton = [_header(outer, definition, source)]
        member_indent = " " * (body.start_point[1] if body is not None else 4)

        for member in body.named_children if body is not None else []:
            inner = _unwrap(member)
            if inner is not None and inner.type == "function_definition":
                chunks.extend(self._function_chunks(member, inner, source, lines, qualified))
                skeleton.append(f"{member_indent}{_header(member, inner, source).strip()} ...")
            elif inner is not None:  # nested class
                chunks.extend(self._class_chunks(member, inner, source, lines, qualified))
                skeleton.append(f"{member_indent}class {_name(inner, source)}: ...")
            elif member.type == "expression_statement":
                # docstring or class attribute such as `timeout: float = 5.0`
                skeleton.append(f"{member_indent}{_text(member, source)}")

        content = "\n".join(skeleton)
        if len(content) > MAX_SKELETON_CHARS:
            content = content[:MAX_SKELETON_CHARS] + "\n    # ... (skeleton truncated)"

        start, end = _span(outer)
        chunks.append(
            Chunk(
                kind="class_skeleton",
                symbol_name=name,
                qualified_name=qualified,
                parent_name=parent,
                signature=_signature(definition, source),
                docstring=_docstring(body, source),
                start_line=start,
                end_line=end,
                content=content,
            )
        )
        return chunks

    # --------------------------------------------------------------------- module

    def _module_chunks(self, statements: list[Node], source: bytes) -> list[Chunk]:
        """Imports, constants, `if __name__ == "__main__":` and anything else top-level.

        Statements are grouped under the size limit. A file with a syntax error still
        lands here (as ERROR nodes), so broken code stays searchable instead of vanishing.
        """

        statements = [s for s in statements if _text(s, source).strip()]
        if not statements:
            return []

        first = statements[0]
        module_doc = None
        if first.type == "expression_statement" and first.named_children:
            if first.named_children[0].type == "string":
                module_doc = _clean_docstring(_text(first.named_children[0], source))

        groups: list[list[Node]] = []
        current: list[Node] = []
        size = 0
        for statement in statements:
            length = statement.end_byte - statement.start_byte
            if current and size + length > self._max_chars:
                groups.append(current)
                current, size = [], 0
            current.append(statement)
            size += length
        if current:
            groups.append(current)

        return [
            Chunk(
                kind="module",
                symbol_name=None,
                qualified_name=None,
                parent_name=None,
                signature=None,
                docstring=module_doc if index == 0 else None,
                start_line=_span(group[0])[0],
                end_line=_span(group[-1])[1],
                content="\n".join(_text(s, source) for s in group),
                part_index=index,
            )
            for index, group in enumerate(groups)
        ]
```


**Key idea: `MAX_CHUNK_CHARS = 4000` (about 1,000 tokens).** Embedding models have an input
limit, and one vector for a 3,000-token function is a blurry average of many ideas.
Around 1,000 tokens keeps a chunk focused. The limit is a constructor argument so the tests
can use a tiny limit to exercise splitting.

### Step 1.5: Picking a chunker (`ingest/chunkers/__init__.py`)

**What:** `chunker_for(language, strategy)`.

**Why:** the pipeline asks "which chunker for this file?" in one place. `strategy="fixed"`
forces the baseline for *every* file, which is how you index the "fixed" variant of a repo
for the ablation.

<!-- file: src/codeqa/ingest/chunkers/__init__.py -->
**`src/codeqa/ingest/chunkers/__init__.py`**

```python
from codeqa.ingest.chunkers.base import Chunk, Chunker
from codeqa.ingest.chunkers.fixed import FixedSizeChunker
from codeqa.ingest.chunkers.markdown import MarkdownChunker
from codeqa.ingest.chunkers.python_ast import PythonASTChunker

ChunkerName = str  # "ast" | "fixed"


def chunker_for(language: str, strategy: ChunkerName = "ast") -> Chunker:
    """Pick the chunker for one file.

    `strategy="fixed"` forces the fixed-size baseline for every file; this is how the
    evaluation compares AST chunking against naive chunking on the same repo.
    """

    if strategy == "fixed":
        return FixedSizeChunker()
    if language == "python":
        return PythonASTChunker()
    if language == "markdown":
        return MarkdownChunker()
    return FixedSizeChunker()


__all__ = [
    "Chunk",
    "Chunker",
    "FixedSizeChunker",
    "MarkdownChunker",
    "PythonASTChunker",
    "chunker_for",
]
```


<!-- file: src/codeqa/ingest/__init__.py -->
**`src/codeqa/ingest/__init__.py`** (empty file: create it with no content)


(`ingest/__init__.py` is an empty file. Every folder under `src/codeqa` should have one.)

### Step 1.6: Call and import edges (`ingest/edges.py`)

**What:** rename `ingest/ingest.py` to `ingest/edges.py` and rewrite it.

```bash
git mv src/codeqa/ingest/ingest.py src/codeqa/ingest/edges.py
```

**Why each fix (audit items 16 to 18):**

- **Owners match chunk names.** A method in a nested class is owned by
  `Outer.Inner.method`, exactly the chunker's `qualified_name`, so the pipeline can link
  each edge to its chunk.
- **Callee names come from the tree, not string splitting.** `foo()` gives `foo`,
  `self.client.send()` gives `send` (the `attribute` field), and anything else
  (`make()()`, `handlers[0]()`) is skipped instead of producing garbage.
- **Builtins are ignored:** `print`, `len`, `str` would otherwise be the most "called"
  functions in every repo.
- **Imports:** `import a.b as c` records `a.b`; `from x import y, z as w` records `y` and
  `z`. Only module-level imports count.
- **Deduplicated and sorted:** calling `send()` five times is one edge; sorted output makes
  tests deterministic.

<!-- file: src/codeqa/ingest/edges.py -->
**`src/codeqa/ingest/edges.py`**

```python
import builtins
from dataclasses import dataclass
from pathlib import Path

from tree_sitter import Node, Parser

from codeqa.ingest.chunkers.python_ast import PY_LANGUAGE

MODULE_OWNER = "<module>"
# Calls to len(), print(), str() ... are noise in a call graph.
BUILTIN_NAMES = frozenset(dir(builtins))


@dataclass(frozen=True)
class SymbolEdge:
    source_qualified_name: str  # "Client.send", or "<module>" for imports
    target_name: str  # plain name, e.g. "build_request"
    kind: str  # "call" | "import"


def _text(node: Node, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")


def _callee_name(call: Node, source: bytes) -> str | None:
    """`foo()` -> foo, `self.client.send()` -> send, `make()()` -> None."""

    func = call.child_by_field_name("function")
    if func is None:
        return None
    if func.type == "identifier":
        return _text(func, source)
    if func.type == "attribute":
        attr = func.child_by_field_name("attribute")
        return _text(attr, source) if attr is not None else None
    return None


def _imported_names(node: Node, source: bytes) -> list[str]:
    """`import a.b as c` -> ["a.b"]; `from x import y, z as w` -> ["y", "z"]."""

    names: list[str] = []
    for child in node.children_by_field_name("name"):
        target = child.child_by_field_name("name") if child.type == "aliased_import" else child
        if target is not None:
            names.append(_text(target, source))
    return names


def extract_edges(path: Path, source: bytes) -> list[SymbolEdge]:
    """Best-effort call and import edges for one Python file.

    Owners use the same qualified names as the AST chunker (`Outer.Inner.method`),
    so the pipeline can map each edge to its source chunk by name.
    """

    tree = Parser(PY_LANGUAGE).parse(source)
    edges: set[SymbolEdge] = set()

    def walk_calls(node: Node, owner: str) -> None:
        for child in node.children:
            if child.type == "call":
                name = _callee_name(child, source)
                if name and name not in BUILTIN_NAMES:
                    edges.add(SymbolEdge(owner, name, "call"))
            walk_calls(child, owner)

    def walk_defs(node: Node, parent: str | None) -> None:
        for child in node.children:
            if child.type == "function_definition":
                name_node = child.child_by_field_name("name")
                name = _text(name_node, source) if name_node else "<anonymous>"
                body = child.child_by_field_name("body")
                if body is not None:
                    walk_calls(body, f"{parent}.{name}" if parent else name)
            elif child.type == "class_definition":
                name_node = child.child_by_field_name("name")
                name = _text(name_node, source) if name_node else "<anonymous>"
                body = child.child_by_field_name("body")
                if body is not None:
                    walk_defs(body, f"{parent}.{name}" if parent else name)
            elif child.type in ("import_statement", "import_from_statement") and parent is None:
                for imported in _imported_names(child, source):
                    edges.add(SymbolEdge(MODULE_OWNER, imported, "import"))
            else:
                walk_defs(child, parent)  # e.g. decorated_definition, if/try blocks

    walk_defs(tree.root_node, None)
    return sorted(edges, key=lambda e: (e.source_qualified_name, e.kind, e.target_name))
```


**Known limitation (write this in your README):** this is *name matching*, not type
inference. `self.client.send()` records "calls something named `send`"; if the repo has
three `send` methods the edge stays unresolved. Real resolution is a research problem and
out of scope. Saying so yourself is better than being asked.

### Step 1.7: The file walker (`ingest/walker.py`)

**What:** list every file worth indexing, with its language and SHA-256.

**Why each change (audit items 19 to 21):**

- **`os.walk` with in-place pruning** (`dirnames[:] = ...`): Python's `os.walk` will not
  descend into folders you remove from `dirnames`. `rglob` visited every file inside
  `.venv` and `node_modules` first, which can be hundreds of thousands of files.
- **`GitIgnoreSpec`**: the non-deprecated pathspec API, with exact git semantics
  (including `!negation` and directory patterns like `build/`).
- **An allow-list of file types** (`LANGUAGE_BY_SUFFIX`): index code, docs and config;
  skip lock files, JSON dumps, CSVs and anything unknown. An allow-list is safer than a
  deny-list: new junk types are skipped automatically.
- **Symlinks are skipped:** a link could point outside the repo (for example to `~/.ssh`).
- **Secrets:** `.env`, `.env.*` (except `.env.example`), keys and certificates are never
  read into the index. Once a secret is in a vector database, it can be retrieved.
- **Sorted traversal:** the same repo always produces files in the same order, so runs
  are reproducible.
- `relative_path` always uses forward slashes (`as_posix()`), also on Windows.

<!-- file: src/codeqa/ingest/walker.py -->
**`src/codeqa/ingest/walker.py`**

```python
import hashlib
import os
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pathspec

from codeqa.config import get_settings

VENDORED_DIRS = {
    "node_modules",
    ".venv",
    "venv",
    "env",
    "dist",
    "build",
    "site-packages",
    ".git",
    ".hg",
    ".tox",
    ".nox",
    "__pycache__",
    ".mypy_cache",
    ".ruff_cache",
    ".pytest_cache",
    ".cache",
}
SECRET_NAMES = {
    ".env",
    "credentials.json",
    "secrets.yaml",
    "secrets.yml",
    "id_rsa",
    "id_ed25519",
    ".netrc",
    ".pypirc",
}
SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".keystore")
LOCK_FILES = {"uv.lock", "poetry.lock", "Pipfile.lock", "package-lock.json", "yarn.lock"}
MINIFIED_SUFFIXES = (".min.js", ".min.css", ".map")

# Which files we index, and how we label them. Anything else is skipped.
LANGUAGE_BY_SUFFIX = {
    ".py": "python",
    ".pyi": "python",
    ".md": "markdown",
    ".markdown": "markdown",
    ".rst": "text",
    ".txt": "text",
    ".toml": "config",
    ".cfg": "config",
    ".ini": "config",
    ".yaml": "config",
    ".yml": "config",
}


@dataclass
class WalkedFile:
    path: Path
    relative_path: str  # always forward slashes, e.g. "src/pkg/mod.py"
    language: str
    content_hash: str
    size_bytes: int


def detect_language(path: Path) -> str | None:
    return LANGUAGE_BY_SUFFIX.get(path.suffix.lower())


def _looks_like_secret(name: str) -> bool:
    lowered = name.lower()
    if lowered in SECRET_NAMES or lowered.endswith(SECRET_SUFFIXES):
        return True
    return lowered.startswith(".env.") and lowered != ".env.example"


def _load_gitignore(root: Path) -> pathspec.GitIgnoreSpec:
    gitignore = root / ".gitignore"
    lines = gitignore.read_text(errors="replace").splitlines() if gitignore.exists() else []
    return pathspec.GitIgnoreSpec.from_lines(lines)


def walk_repository(root: Path, max_file_size_mb: float | None = None) -> Iterator[WalkedFile]:
    """Yield every indexable file under `root`, with its SHA-256.

    Skips: vendored/cache dirs, .gitignore matches, symlinks, secrets, lock files,
    minified files, unknown file types, files over the size limit, and binaries.
    """

    limit_mb = max_file_size_mb if max_file_size_mb is not None else get_settings().max_file_size_mb
    max_size = int(limit_mb * 1024 * 1024)
    spec = _load_gitignore(root)

    for dirpath, dirnames, filenames in os.walk(root):
        current = Path(dirpath)
        rel_dir = current.relative_to(root).as_posix()
        # Prune in place: os.walk will not descend into removed dirs. Much faster than
        # rglob, which walks all of .venv/node_modules before we filter.
        dirnames[:] = sorted(
            d
            for d in dirnames
            if d not in VENDORED_DIRS
            and not d.endswith(".egg-info")
            and not spec.match_file(f"{d}/" if rel_dir == "." else f"{rel_dir}/{d}/")
        )

        for name in sorted(filenames):
            path = current / name
            relative = path.relative_to(root).as_posix()
            language = detect_language(path)
            if (
                language is None
                or path.is_symlink()
                or name in LOCK_FILES
                or name.endswith(MINIFIED_SUFFIXES)
                or _looks_like_secret(name)
                or spec.match_file(relative)
            ):
                continue

            try:
                size = path.stat().st_size
                if size > max_size:
                    continue
                data = path.read_bytes()
            except OSError:
                continue
            if b"\x00" in data[:8000]:
                continue  # binary heuristic: text files do not contain NUL bytes

            yield WalkedFile(
                path=path,
                relative_path=relative,
                language=language,
                content_hash=hashlib.sha256(data).hexdigest(),
                size_bytes=size,
            )
```


### Step 1.8: Resolving the source (`ingest/source.py`)

**What:** turn a local path or git URL into a folder on disk plus a commit SHA.

**Why each change (audit items 22 and 23):**

- **Deterministic clone folder** (`<repo>-<hash of URL>`): re-indexing the same URL does
  `git fetch --depth 1` + `reset` in the existing clone instead of cloning again into a new
  random folder.
- **Timeouts** on every git command: a network hang cannot block a job forever.
- **URL allow-list:** only `https://` and `git@` URLs. Git's `ext::` transport can run
  arbitrary commands, and `file://` can read local files.
- **`allowed_root`:** the API will only index local folders inside `LOCAL_INDEX_ROOT`, which
  blocks requests like "index `/etc`".
- **`github_permalink()`:** builds `https://github.com/{owner}/{repo}/blob/{sha}/{path}#L{a}-L{b}`.
  Pinning to the *commit SHA*, not a branch, means the link still points at the same code
  after the repo changes.
- `SourceError` subclasses `InvalidInputError`, so the API returns it as a 422.

<!-- file: src/codeqa/ingest/source.py -->
**`src/codeqa/ingest/source.py`**

```python
import hashlib
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from codeqa.config import get_settings
from codeqa.errors import InvalidInputError

GIT_TIMEOUT_S = 300
# Only these transports. `ext::` and `file://` URLs can run commands or read local files.
ALLOWED_URL = re.compile(r"^(https://[\w.-]+/[\w./-]+|git@[\w.-]+:[\w./-]+)$")
GITHUB_URL = re.compile(r"github\.com[/:](?P<owner>[\w.-]+)/(?P<repo>[\w.-]+?)(?:\.git)?/?$")


class SourceError(InvalidInputError):
    """The path or URL cannot be indexed."""


@dataclass
class ResolvedSource:
    local_path: Path
    commit_sha: str
    source_url: str | None


def _run_git(args: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
        timeout=GIT_TIMEOUT_S,
    )
    return result.stdout.strip()


def is_remote(path_or_url: str) -> bool:
    return path_or_url.startswith(("http://", "https://", "git@"))


def _clone_dir(url: str) -> Path:
    """Same URL -> same folder, so re-indexing updates the clone instead of re-cloning."""

    digest = hashlib.sha256(url.encode()).hexdigest()[:16]
    slug = re.sub(r"[^\w.-]", "_", url.rstrip("/").split("/")[-1].removesuffix(".git"))
    return get_settings().cache_dir / "repos" / f"{slug}-{digest}"


def resolve_source(path_or_url: str, allowed_root: Path | None = None) -> ResolvedSource:
    """Turn a local path or git URL into a folder on disk plus its commit SHA.

    URLs are shallow-cloned (`--depth 1`) into the cache dir. If `allowed_root` is
    given, local paths must live inside it (blocks `/etc`, `~/.ssh`, ... via the API).
    """

    if is_remote(path_or_url):
        if not ALLOWED_URL.match(path_or_url):
            raise SourceError(f"unsupported git URL: {path_or_url}")
        dest = _clone_dir(path_or_url)
        if (dest / ".git").exists():
            _run_git(["fetch", "--depth", "1", "origin", "HEAD"], cwd=dest)
            _run_git(["reset", "--hard", "FETCH_HEAD"], cwd=dest)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            _run_git(["clone", "--depth", "1", path_or_url, str(dest)])
        commit_sha = _run_git(["rev-parse", "HEAD"], cwd=dest)
        return ResolvedSource(local_path=dest, commit_sha=commit_sha, source_url=path_or_url)

    local_path = Path(path_or_url).expanduser().resolve()
    if not local_path.is_dir():
        raise SourceError(f"not a directory: {local_path}")
    if allowed_root is not None and not local_path.is_relative_to(allowed_root.resolve()):
        raise SourceError(f"path is outside the allowed root {allowed_root}: {local_path}")

    commit_sha = ""
    try:
        commit_sha = _run_git(["rev-parse", "HEAD"], cwd=local_path)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass  # not a git repo (or git not installed): permalinks fall back to path:line

    return ResolvedSource(local_path=local_path, commit_sha=commit_sha, source_url=None)


def github_permalink(
    source_url: str | None, commit_sha: str, path: str, start_line: int, end_line: int
) -> str | None:
    """`https://github.com/{owner}/{repo}/blob/{sha}/{path}#L{start}-L{end}` or None."""

    if not source_url or not commit_sha:
        return None
    match = GITHUB_URL.search(source_url)
    if match is None:
        return None
    return (
        f"https://github.com/{match['owner']}/{match['repo']}/blob/{commit_sha}/{path}"
        f"#L{start_line}-L{end_line}"
    )
```


### Step 1.9: Deterministic chunk ids (`ingest/ids.py`)

**What:** `uuid5(namespace, "repo|path|kind|qualified_name|start_line|part")`.

**Why:** a `uuid5` is a hash: the same input always gives the same id. Postgres and
Qdrant use the same id for the same chunk, so re-indexing *overwrites* (upserts) instead
of duplicating, and the two stores can always be matched up. `kind` and `start_line` are
part of the key because names alone are not unique (see Part B.4).

<!-- file: src/codeqa/ingest/ids.py -->
**`src/codeqa/ingest/ids.py`**

```python
import uuid

# Any fixed UUID works. Never change it: every stored chunk id depends on it.
CHUNK_NAMESPACE = uuid.UUID("6f1c2a8e-4b1d-4c55-9a8e-0c0d2f6e7a11")


def chunk_id(
    repository_id: uuid.UUID,
    path: str,
    kind: str,
    qualified_name: str | None,
    start_line: int,
    part_index: int,
) -> uuid.UUID:
    """Deterministic chunk id, shared by Postgres and Qdrant.

    Same inputs -> same id, so re-indexing *upserts* instead of duplicating. `kind` and
    `start_line` are included because a class skeleton and a module chunk can share a
    name (or have none), and a property getter/setter pair shares `qualified_name`.
    """

    key = f"{repository_id}|{path}|{kind}|{qualified_name or ''}|{start_line}|{part_index}"
    return uuid.uuid5(CHUNK_NAMESPACE, key)
```


### Step 1.10: The CLI, split by command group (`cli/`)

**What:** `cli/app.py` holds the Typer app and shared helpers, each command group lives in
its own module, and `cli/main.py` imports the modules to register their commands.

**Why this structure:** each phase adds one command module and one import line. Commands
import heavy libraries *inside* the function, so `codeqa --help` stays instant and
`codeqa chunk` never loads LangGraph or the embedding model.

**How registration works:** `@app.command()` runs when the module is imported and attaches
the function to `app`. That is why `main.py` imports modules it never calls directly (the
`# noqa: F401` tells ruff this unused import is intentional).

Delete the old `cli/main.py` content and create these files:

<!-- file: src/codeqa/cli/__init__.py -->
**`src/codeqa/cli/__init__.py`** (empty file: create it with no content)


<!-- file: src/codeqa/cli/app.py -->
**`src/codeqa/cli/app.py`**

```python
"""The Typer app object and helpers shared by every CLI command module."""

import json
from typing import Annotated, Any

import typer
from rich.console import Console

from codeqa.logging import configure_logging

app = typer.Typer(help="CodeQA: ask questions about a Python codebase.", no_args_is_help=True)
eval_app = typer.Typer(help="Evaluation: retrieval ablations, calibration, generation.")
app.add_typer(eval_app, name="eval")
console = Console()

RepoOption = Annotated[str, typer.Option("--repo", "-r", help="Indexed repository name")]
JsonOption = Annotated[bool, typer.Option("--json", help="Print machine-readable JSON")]


@app.callback()
def _setup() -> None:
    configure_logging()


def print_json(data: Any) -> None:
    typer.echo(json.dumps(data, indent=2, default=str))
```


<!-- file: src/codeqa/cli/chunk.py -->
**`src/codeqa/cli/chunk.py`**

```python
import statistics
from pathlib import Path
from typing import Annotated

import typer
from rich.markup import escape
from rich.table import Table

from codeqa.cli.app import app, console


@app.command()
def chunk(
    path: Path,
    limit: int = 20,
    strategy: Annotated[str, typer.Option(help="ast | fixed")] = "ast",
) -> None:
    """Chunk a file (prints chunks) or a folder (prints a chunk-size histogram)."""

    from codeqa.ingest.chunkers import chunker_for
    from codeqa.ingest.walker import detect_language, walk_repository

    if path.is_file():
        language = detect_language(path) or "text"
        chunks = chunker_for(language, strategy).chunk_file(path, path.read_bytes())
        table = Table(title=f"{len(chunks)} chunks in {path}")
        for column in ("kind", "qualified_name", "lines", "part", "tokens"):
            table.add_column(column)
        for c in chunks[:limit]:
            table.add_row(
                c.kind,
                escape(c.qualified_name or "-"),
                f"{c.start_line}-{c.end_line}",
                str(c.part_index),
                str(c.token_count),
            )
        console.print(table)
        return

    sizes: list[int] = []
    files = 0
    for walked in walk_repository(path):
        chunker = chunker_for(walked.language, strategy)
        sizes += [c.token_count for c in chunker.chunk_file(walked.path, walked.path.read_bytes())]
        files += 1
    if not sizes:
        console.print("[yellow]No chunks produced.[/yellow]")
        return
    sizes.sort()
    p95 = sizes[min(len(sizes) - 1, int(len(sizes) * 0.95))]
    console.print(
        f"{files} files, {len(sizes)} chunks | tokens: min={sizes[0]} "
        f"median={int(statistics.median(sizes))} p95={p95} max={sizes[-1]}"
    )
```


<!-- file: src/codeqa/cli/main.py -->
**`src/codeqa/cli/main.py`**

```python
from rich.markup import escape

# Importing a command module registers its commands on `app` (decorators run on import).
from codeqa.cli import chunk  # noqa: F401
from codeqa.cli.app import app, console
from codeqa.errors import CodeQAError


def main() -> None:
    try:
        app()
    except CodeQAError as exc:
        console.print(f"[red]Error:[/red] {escape(exc.message)}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
```


**Check:**

```bash
uv run codeqa chunk tests/fixtures/sample_code/basic.py
uv run codeqa chunk src/                     # folder mode: size histogram
```

### Step 1.11: Test fixtures

**What:** small, hand-written code with *known* structure, so tests can assert exact names
and line numbers.

**Why:** a test that says "there are some chunks" proves nothing. A test that says
"`Client.send` is lines 8 to 10" catches every off-by-one.

`tests/fixtures/sample_code/nested.py` covers nested classes, decorated and async
functions, class attributes and non-ASCII names:

<!-- file: tests/fixtures/sample_code/nested.py -->
**`tests/fixtures/sample_code/nested.py`**

```python
"""Nested, decorated and async definitions."""

import functools


def cached(fn):
    return functools.lru_cache(maxsize=None)(fn)


class Outer:
    """Outer class."""

    timeout: float = 5.0
    retries = 3

    class Inner:
        def ping(self):
            return "pong"

    @property
    def name(self):
        return "outer"

    @cached
    async def fetch(self, url):
        """Fetch a URL."""
        return await self._get(url)


@cached
async def top_level(x):
    return x


def héllo():
    return "ünïcode"
```


`tests/fixtures/sample_repo/` is a tiny fake project. The edge tests use it now; the
pipeline, search, graph, API and evaluation tests use it later.

<!-- file: tests/fixtures/sample_repo/README.md -->
**`tests/fixtures/sample_repo/README.md`**

```markdown
# Shop

A tiny example shop used by the CodeQA tests.

## Usage

Create a `Client` and call `send`.

## Retries

Failed requests are retried with exponential backoff (see `RetryPolicy`).
```


<!-- file: tests/fixtures/sample_repo/shop/__init__.py -->
**`tests/fixtures/sample_repo/shop/__init__.py`**

```python
"""Shop package."""
```


<!-- file: tests/fixtures/sample_repo/shop/retry.py -->
**`tests/fixtures/sample_repo/shop/retry.py`**

```python
"""Retry policy with exponential backoff."""

import random


class RetryPolicy:
    """Decide how long to wait between attempts."""

    max_attempts: int = 3

    def __init__(self, base_delay: float = 0.5) -> None:
        self.base_delay = base_delay

    def _backoff(self, attempt: int) -> float:
        """Exponential backoff with jitter: base * 2**attempt + noise."""
        return self.base_delay * (2**attempt) + random.random() / 10

    def should_retry(self, attempt: int, status_code: int) -> bool:
        return attempt < self.max_attempts and status_code >= 500
```


<!-- file: tests/fixtures/sample_repo/shop/client.py -->
**`tests/fixtures/sample_repo/shop/client.py`**

```python
"""HTTP-ish client for the shop API."""

import time

from shop.retry import RetryPolicy
from shop.users import get_user_by_id


class Client:
    """Sends requests and retries failures."""

    def __init__(self, policy: RetryPolicy | None = None) -> None:
        self.policy = policy or RetryPolicy()

    def send(self, request: dict) -> dict:
        """Send one request, retrying server errors according to the policy."""
        attempt = 0
        while True:
            response = self._transport(request)
            if not self.policy.should_retry(attempt, response["status"]):
                return response
            time.sleep(self.policy._backoff(attempt))
            attempt += 1

    def _transport(self, request: dict) -> dict:
        return {"status": 200, "body": request}

    def current_user(self, user_id: int) -> dict:
        return get_user_by_id(user_id)
```


<!-- file: tests/fixtures/sample_repo/shop/users.py -->
**`tests/fixtures/sample_repo/shop/users.py`**

```python
"""User lookups."""

USERS = {1: {"id": 1, "name": "Ada"}}


def get_user_by_id(user_id: int) -> dict:
    """Return the user with this id, or raise KeyError."""
    return USERS[user_id]


def parse_json_v2(raw: str) -> dict:
    """Parse the v2 JSON wire format."""
    import json

    return json.loads(raw)
```


> Leave `basic.py`, `empty.py` and `syntax_error.py` as they are. Ruff already skips
> `tests/fixtures` (that is what the `extend-exclude` line is for), so the deliberately
> broken file does not fail linting.

### Step 1.12: Tests

**What:** replace `tests/unit/test_python_ast_chunker.py` and add four new test files.

**Why these tests:** they encode the Phase 1 Definition of Done from the plan: exact
names and line ranges, decorators kept, nested/async handled, 400-line function split with
contiguous ranges, syntax errors degrade instead of crashing, empty files produce nothing.

<!-- file: tests/unit/test_python_ast_chunker.py -->
**`tests/unit/test_python_ast_chunker.py`**

```python
from pathlib import Path

from codeqa.ingest.chunkers.python_ast import PythonASTChunker

FIXTURES = Path(__file__).parent.parent / "fixtures" / "sample_code"


def _chunks(name: str) -> list:  # type: ignore[type-arg]
    path = FIXTURES / name
    return PythonASTChunker().chunk_file(path, path.read_bytes())


def test_basic_file_chunks() -> None:
    chunks = _chunks("basic.py")
    by_name = {(c.kind, c.qualified_name): c for c in chunks}

    assert set(by_name) == {
        ("method", "Client.send"),
        ("method", "Client.aclose"),
        ("class_skeleton", "Client"),
        ("function", "helper"),
        ("module", None),
    }
    send = by_name[("method", "Client.send")]
    assert send.docstring == "Send a request."
    assert (send.start_line, send.end_line) == (8, 10)
    assert send.parent_name == "Client"


def test_decorators_are_kept_with_the_function() -> None:
    helper = next(c for c in _chunks("basic.py") if c.qualified_name == "helper")
    assert helper.content.startswith("@staticmethod")
    assert helper.start_line == 16  # the decorator line, not the def line


def test_nested_decorated_and_async() -> None:
    chunks = _chunks("nested.py")
    names = {c.qualified_name for c in chunks if c.kind in ("method", "function")}
    assert names == {
        "cached",
        "Outer.Inner.ping",
        "Outer.name",
        "Outer.fetch",
        "top_level",
        "héllo",
    }

    fetch = next(c for c in chunks if c.qualified_name == "Outer.fetch")
    assert "@cached" in fetch.content and "async def fetch" in fetch.content
    assert fetch.docstring == "Fetch a URL."

    inner = next(
        c for c in chunks if c.qualified_name == "Outer.Inner" and c.kind == "class_skeleton"
    )
    assert inner.parent_name == "Outer"


def test_class_skeleton_has_attributes_and_signatures_only() -> None:
    outer = next(
        c
        for c in _chunks("nested.py")
        if c.kind == "class_skeleton" and c.qualified_name == "Outer"
    )
    assert "timeout: float = 5.0" in outer.content
    assert "async def fetch(self, url): ..." in outer.content
    assert "class Inner: ..." in outer.content
    assert "return await" not in outer.content  # no method bodies


def test_non_ascii_source_is_sliced_by_bytes() -> None:
    hello = next(c for c in _chunks("nested.py") if c.qualified_name == "héllo")
    assert '"ünïcode"' in hello.content


def test_large_function_is_split_with_correct_line_ranges(tmp_path: Path) -> None:
    body = "\n".join(f"    x{i} = {i}" for i in range(400))
    source = f"def big():\n{body}\n    return x0\n".encode()
    chunks = PythonASTChunker(max_chunk_chars=1000).chunk_file(tmp_path / "big.py", source)

    assert len(chunks) > 1
    assert [c.part_index for c in chunks] == list(range(len(chunks)))
    assert chunks[0].start_line == 1 and chunks[-1].end_line == 402
    for previous, current in zip(chunks, chunks[1:], strict=False):
        assert current.start_line == previous.end_line + 1  # contiguous, no gaps, no overlap
        assert current.content.startswith("def big():  # (continued)")


def test_syntax_error_does_not_crash() -> None:
    chunks = _chunks("syntax_error.py")
    assert isinstance(chunks, list)  # tree-sitter degrades, does not raise
    assert any("broken" in c.content for c in chunks)  # and does not drop the code


def test_empty_file() -> None:
    assert _chunks("empty.py") == []
```


<!-- file: tests/unit/test_other_chunkers.py -->
**`tests/unit/test_other_chunkers.py`**

````python
from pathlib import Path

from codeqa.ingest.chunkers import chunker_for
from codeqa.ingest.chunkers.fixed import FixedSizeChunker
from codeqa.ingest.chunkers.markdown import MarkdownChunker
from codeqa.ingest.chunkers.python_ast import PythonASTChunker


def test_fixed_chunker_windows_overlap() -> None:
    source = "\n".join(f"line {i}" for i in range(1, 131)).encode()
    chunks = FixedSizeChunker().chunk_file(Path("x.txt"), source)
    assert [(c.start_line, c.end_line) for c in chunks] == [(1, 60), (51, 110), (101, 130)]


def test_markdown_sections_keep_header_path() -> None:
    source = b"# Guide\nintro\n## Install\nrun it\n```\n# not a header\n```\n## Use\nok\n"
    chunks = MarkdownChunker().chunk_file(Path("README.md"), source)
    assert [c.qualified_name for c in chunks] == ["Guide", "Guide > Install", "Guide > Use"]
    assert "# not a header" in chunks[1].content
    assert (chunks[1].start_line, chunks[1].end_line) == (3, 7)


def test_chunker_for_picks_by_language_and_strategy() -> None:
    assert isinstance(chunker_for("python"), PythonASTChunker)
    assert isinstance(chunker_for("markdown"), MarkdownChunker)
    assert isinstance(chunker_for("config"), FixedSizeChunker)
    assert isinstance(chunker_for("python", "fixed"), FixedSizeChunker)
````


<!-- file: tests/unit/test_edges.py -->
**`tests/unit/test_edges.py`**

```python
from pathlib import Path

from codeqa.ingest.edges import SymbolEdge, extract_edges

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_calls_and_imports_are_extracted() -> None:
    path = FIXTURES / "sample_repo" / "shop" / "client.py"
    edges = set(extract_edges(path, path.read_bytes()))

    assert SymbolEdge("Client.send", "_transport", "call") in edges
    assert SymbolEdge("Client.send", "should_retry", "call") in edges
    assert SymbolEdge("Client.send", "_backoff", "call") in edges
    assert SymbolEdge("Client.current_user", "get_user_by_id", "call") in edges
    assert SymbolEdge("<module>", "RetryPolicy", "import") in edges
    assert SymbolEdge("<module>", "time", "import") in edges


def test_builtins_are_ignored_and_nested_classes_qualified() -> None:
    source = (
        b"class A:\n"
        b"    class B:\n"
        b"        def f(self):\n"
        b"            print(len([]))\n"
        b"            g()\n"
    )
    edges = extract_edges(Path("x.py"), source)
    assert edges == [SymbolEdge("A.B.f", "g", "call")]
```


<!-- file: tests/unit/test_walker.py -->
**`tests/unit/test_walker.py`**

```python
from pathlib import Path

from codeqa.ingest.walker import walk_repository


def _write(root: Path, relative: str, data: bytes = b"x = 1\n") -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def test_walker_filters(tmp_path: Path) -> None:
    _write(tmp_path, "src/app.py")
    _write(tmp_path, "README.md", b"# hi\n")
    _write(tmp_path, ".gitignore", b"generated/\n*.log\n")
    _write(tmp_path, "generated/out.py")
    _write(tmp_path, "debug.log")
    _write(tmp_path, ".venv/lib/site.py")
    _write(tmp_path, "node_modules/x/index.py")
    _write(tmp_path, ".env", b"SECRET=1\n")
    _write(tmp_path, "certs/server.pem", b"-----BEGIN")
    _write(tmp_path, "uv.lock", b"lock\n")
    _write(tmp_path, "image.py", b"\x00\x01binary")
    _write(tmp_path, "big.py", b"#" * 2_000_000)
    _write(tmp_path, "data.bin", b"abc")

    found = {f.relative_path: f for f in walk_repository(tmp_path, max_file_size_mb=1)}

    assert set(found) == {"src/app.py", "README.md"}
    assert found["src/app.py"].language == "python"
    assert len(found["src/app.py"].content_hash) == 64


def test_hash_changes_with_content(tmp_path: Path) -> None:
    _write(tmp_path, "a.py", b"x = 1\n")
    first = next(walk_repository(tmp_path)).content_hash
    _write(tmp_path, "a.py", b"x = 2\n")
    assert next(walk_repository(tmp_path)).content_hash != first
```


<!-- file: tests/unit/test_source.py -->
**`tests/unit/test_source.py`**

```python
import uuid
from pathlib import Path

import pytest

from codeqa.ingest.ids import chunk_id
from codeqa.ingest.source import SourceError, github_permalink, resolve_source


def test_local_path_outside_allowed_root_is_rejected(tmp_path: Path) -> None:
    allowed = tmp_path / "repos"
    allowed.mkdir()
    with pytest.raises(SourceError):
        resolve_source(str(tmp_path), allowed_root=allowed)


def test_dangerous_git_urls_are_rejected() -> None:
    with pytest.raises(SourceError):
        resolve_source("https://example.com/x; rm -rf /")


def test_github_permalink() -> None:
    url = github_permalink(
        "https://github.com/encode/httpx.git", "abc123", "httpx/_client.py", 3, 9
    )
    assert url == "https://github.com/encode/httpx/blob/abc123/httpx/_client.py#L3-L9"
    assert github_permalink(None, "abc", "x.py", 1, 2) is None


def test_chunk_ids_are_deterministic() -> None:
    repo = uuid.uuid4()
    first = chunk_id(repo, "a.py", "method", "A.f", 10, 0)
    assert first == chunk_id(repo, "a.py", "method", "A.f", 10, 0)
    assert first != chunk_id(repo, "a.py", "method", "A.f", 10, 1)
```


**How to read a failing test:** pytest prints the assertion with both sides, for example
`assert (8, 11) == (8, 10)`. That says the chunk ends one line too late: look at how
`end_line` is computed.

### Phase 1: Definition of Done

```bash
make lint && make test                # 20 passed
```

Then run the chunker on a real repository of about 5,000+ lines (any mid-size open-source
Python project, for example the dev repo you will pick in Phase 4). This guide clones into
`/tmp/httpx`; use a folder like `~/code/httpx` instead if you want it to survive a reboot,
and adjust the paths in later phases:

```bash
git clone --depth 1 https://github.com/encode/httpx /tmp/httpx
uv run codeqa chunk /tmp/httpx
# prints one line: "<files> files, <chunks> chunks | tokens: min=.. median=.. p95=.. max=.."
```

(For reference, this project's own `src/` gave `51 files, 294 chunks | tokens: min=7
median=72 p95=411 max=1002` when the guide was verified.)

Look for: zero crashes, `max` at or below about 1,000 tokens (the split limit), and a
median well under the limit.

**Write the comparison snippet** the plan asks for, `docs/chunking-comparison.md`: pick
one real function, run both strategies on its file, and paste the output:

```bash
uv run codeqa chunk /tmp/httpx/httpx/_client.py --strategy fixed --limit 10
uv run codeqa chunk /tmp/httpx/httpx/_client.py --strategy ast --limit 40
```

Show a fixed window that starts in the middle of a method next to the AST chunk that
contains the whole method. This is a very effective image for your README.


---

## Phase 2. Embeddings, vector store and the indexing pipeline

**Goal:** `codeqa index <path-or-url> -n <name>` turns a repo into searchable dense and
sparse vectors in Qdrant, with metadata, edges and job progress in Postgres. Re-running it
is fast and never duplicates anything.

```bash
git checkout -b phase-2-indexing
```

### 2.0 Concepts you need first

**Dense vectors (embeddings).** A neural model maps text to a list of numbers (768 for
jina-code) so that *similar meaning* gives *nearby vectors*. "retry with backoff" and
`time.sleep(policy._backoff(attempt))` end up close even with no shared words. Weakness:
exact identifiers. The vector for `get_user_by_id` is only "somewhat about users".

**Sparse vectors (BM25).** One dimension per word; the value is how important that word
is in this chunk (term frequency, damped) times how rare it is across all chunks (inverse
document frequency, IDF). Great at exact tokens (`get_user_by_id`), blind to synonyms.

**Why both (hybrid):** code questions mix both kinds. "Where do we parse JSON?" is
conceptual; "What does `parse_json_v2` return?" is exact. Each method covers the other's
blind spot. Phase 3 fuses them.

**Identifier splitting.** A plain BM25 tokenizer sees `getUserByID` as one token, so the
query "get user by id" shares no tokens with it. We add sub-words to *both* documents and
queries: `getUserByID` becomes `getuserbyid get user by id`. Exact queries still match the
whole token; natural-language queries match the parts.

**Qdrant collection layout.** One collection holds points. Each point has an id (our
deterministic chunk id), two *named* vectors (`dense`, `sparse`) and a JSON *payload*
(path, lines, name, content...). Returning the payload with each hit means search needs
no second round trip to Postgres. Postgres stays the source of truth; Qdrant is an index
that can always be rebuilt from it.

**Idempotent, crash-safe writes.** Idempotent: running twice gives the same result as once
(deterministic ids + upsert). Crash-safe: a crash at any moment leaves a state the next
run can repair. The pipeline writes Qdrant *first* and commits Postgres *last*; the new
file hash only lands in Postgres once the file is fully written everywhere. If the process
dies in between, Postgres still has the old hash, so the next run redoes that file.

### Step 2.1: Dense embedder (`retrieval/embedder.py`)

**What:** an `Embedder` protocol, a fastembed implementation, a hashing fake for tests,
and a cached `get_embedder()`.

**Why:**

- **Protocol:** the pipeline and search only know `embed_documents`, `embed_query`, `dim`,
  `name`. Swapping jina-code for bge-small is a config change, which is exactly what the
  ablation needs.
- **`passage_embed` vs `query_embed`:** some models expect different prefixes for
  documents and questions. fastembed applies the right one per model.
- **Load once:** `get_embedder()` is `lru_cache`d. Loading an ONNX model takes seconds;
  loading it per batch is the most common beginner performance bug.
- **`HashingEmbedder`:** a deterministic bag-of-words vector. Not smart, but it makes the
  whole test suite run offline in seconds. `EMBEDDING_MODEL=hashing-64` selects it.
- **Throughput log** (`per_second`): you will quote "N chunks/second on a CPU laptop" in the
  README. Run with `LOG_LEVEL=DEBUG` to see it.

The first real run downloads the model into `MODEL_CACHE_DIR` (`.cache/models`), about
640 MB for jina-code and 67 MB for bge-small.

<!-- file: src/codeqa/retrieval/embedder.py -->
**`src/codeqa/retrieval/embedder.py`**

```python
import hashlib
import math
import re
import time
from collections.abc import Sequence
from functools import lru_cache
from typing import Protocol

from codeqa.config import get_settings
from codeqa.logging import get_logger

log = get_logger(__name__)


class Embedder(Protocol):
    """Anything that turns text into dense vectors. Swap models by swapping this."""

    @property
    def name(self) -> str: ...

    @property
    def dim(self) -> int: ...

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class FastEmbedEmbedder:
    """Dense embeddings with fastembed (ONNX on CPU). The model loads once, in __init__."""

    def __init__(self, model_name: str, batch_size: int = 32) -> None:
        from fastembed import TextEmbedding  # heavy import: only when really needed

        settings = get_settings()
        self._name = model_name
        self._batch_size = batch_size
        self._model = TextEmbedding(model_name, cache_dir=str(settings.model_cache_dir))
        self._dim = int(self._model.embedding_size)

    @property
    def name(self) -> str:
        return self._name

    @property
    def dim(self) -> int:
        return self._dim

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        started = time.perf_counter()
        vectors = [
            v.tolist() for v in self._model.passage_embed(list(texts), batch_size=self._batch_size)
        ]
        elapsed = time.perf_counter() - started
        log.debug("embedded", count=len(texts), per_second=round(len(texts) / max(elapsed, 1e-9)))
        return vectors

    def embed_query(self, text: str) -> list[float]:
        return [float(x) for x in next(iter(self._model.query_embed(text)))]


class HashingEmbedder:
    """Deterministic bag-of-words vectors. For tests only: no download, no network."""

    def __init__(self, dim: int = 64) -> None:
        self._dim = dim

    @property
    def name(self) -> str:
        return f"hashing-{self._dim}"

    @property
    def dim(self) -> int:
        return self._dim

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self._dim
        for token in re.findall(r"[a-z0-9]+", text.lower()):
            bucket = int(hashlib.md5(token.encode()).hexdigest(), 16) % self._dim
            vector[bucket] += 1.0
        norm = math.sqrt(sum(x * x for x in vector)) or 1.0
        return [x / norm for x in vector]

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


@lru_cache(maxsize=4)
def get_embedder(model_name: str) -> Embedder:
    """One loaded model per name for the whole process (loading takes seconds)."""

    if model_name.startswith("hashing-"):
        return HashingEmbedder(int(model_name.removeprefix("hashing-")))
    return FastEmbedEmbedder(model_name, batch_size=get_settings().embedding_batch_size)
```


<!-- file: src/codeqa/retrieval/__init__.py -->
**`src/codeqa/retrieval/__init__.py`** (empty file: create it with no content)


### Step 2.2: Sparse encoder with identifier splitting (`retrieval/sparse.py`)

**What:** `split_identifier`, `expand_identifiers`, a BM25 encoder and a test fake.

**Why the regex works:** `SUBWORD` tries four shapes in order: an acronym followed by a
capitalised word (`HTTP` in `HTTPServer`), a capitalised or lowercase word (`User`,
`get`), a trailing acronym (`ID`), and digits (`2`). Splitting on `_` first handles
snake_case.

**Why expansion happens inside the encoder:** both `embed_documents` and `embed_query`
call `expand_identifiers`. Putting it in one class makes it impossible to apply it to one
side only, which is the pitfall the plan warns about ("silently destroys sparse recall").

**Why Qdrant computes IDF:** fastembed's BM25 gives term-frequency weights for documents
and weight 1 for query terms. The collection is created with `Modifier.IDF`, so Qdrant
multiplies in the inverse document frequency over *the whole collection* at query time.
You never have to recompute statistics when documents change.

<!-- file: src/codeqa/retrieval/sparse.py -->
**`src/codeqa/retrieval/sparse.py`**

```python
import hashlib
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from codeqa.config import get_settings

IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|\d+")
# One alternative per sub-word shape: "HTTP"(Server), "User", "user", "ID", "2"
SUBWORD = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+")


def split_identifier(identifier: str) -> list[str]:
    """`getUserByID` -> [get, user, by, id]; `parse_json_v2` -> [parse, json, v, 2]."""

    parts: list[str] = []
    for piece in identifier.split("_"):
        parts.extend(match.group(0).lower() for match in SUBWORD.finditer(piece))
    return parts


def expand_identifiers(text: str) -> str:
    """Keep each identifier whole *and* add its sub-words.

    `getUserByID(x)` -> `getuserbyid get user by id x`. Exact queries still match the
    whole token; natural-language queries ("get user by id") match the sub-words.
    Apply this to documents AND queries, or sparse recall silently collapses.
    """

    tokens: list[str] = []
    for match in IDENTIFIER.finditer(text):
        word = match.group(0)
        parts = split_identifier(word)
        tokens.append(word.lower())
        if len(parts) > 1:
            tokens.extend(parts)
    return " ".join(tokens)


@dataclass
class SparseVector:
    indices: list[int]
    values: list[float]


class SparseEncoder(Protocol):
    def embed_documents(self, texts: Sequence[str]) -> list[SparseVector]: ...

    def embed_query(self, text: str) -> SparseVector: ...


class FastEmbedBM25:
    """BM25 term weights from fastembed. Qdrant applies the IDF part server-side."""

    def __init__(self, model_name: str = "Qdrant/bm25") -> None:
        from fastembed import SparseTextEmbedding

        self._model = SparseTextEmbedding(model_name, cache_dir=str(get_settings().model_cache_dir))

    def embed_documents(self, texts: Sequence[str]) -> list[SparseVector]:
        expanded = [expand_identifiers(t) for t in texts]
        return [
            SparseVector(indices=e.indices.tolist(), values=e.values.tolist())
            for e in self._model.embed(expanded)
        ]

    def embed_query(self, text: str) -> SparseVector:
        embedding = next(iter(self._model.query_embed(expand_identifiers(text))))
        return SparseVector(indices=embedding.indices.tolist(), values=embedding.values.tolist())


class HashingSparseEncoder:
    """Term-frequency sparse vectors for tests. Same identifier expansion as BM25."""

    def _encode(self, text: str) -> SparseVector:
        counts = Counter(expand_identifiers(text).split())
        weights: dict[int, float] = {}
        for token, count in counts.items():
            index = int(hashlib.md5(token.encode()).hexdigest(), 16) % (2**31)
            weights[index] = weights.get(index, 0.0) + float(count)
        indices = sorted(weights)
        return SparseVector(indices=indices, values=[weights[i] for i in indices])

    def embed_documents(self, texts: Sequence[str]) -> list[SparseVector]:
        return [self._encode(t) for t in texts]

    def embed_query(self, text: str) -> SparseVector:
        return self._encode(text)


@lru_cache(maxsize=2)
def get_sparse_encoder(model_name: str) -> SparseEncoder:
    if model_name == "hashing":
        return HashingSparseEncoder()
    return FastEmbedBM25(model_name)
```


### Step 2.3: The two texts per chunk (`retrieval/texts.py`)

**What:** the text we embed densely, and the text we give to BM25.

**Why a context header for embeddings:** a method body alone often does not mention its
file or class. Prepending `# File:`, `# Symbol:`, `# Signature:` puts that information into
the vector, which helps questions such as "how does the Client send requests?".

**Why path + name + docstring for BM25:** these are where the exact words people search
for live.

<!-- file: src/codeqa/retrieval/texts.py -->
**`src/codeqa/retrieval/texts.py`**

```python
from codeqa.ingest.chunkers.base import Chunk


def embedding_text(path: str, chunk: Chunk) -> str:
    """Context header + code. The header tells the embedding model *where* code lives.

    # File: httpx/_client.py
    # Symbol: Client.send (method of Client)
    # Signature: def send(self, request, ...):
    <code>
    """

    header = [f"# File: {path}"]
    if chunk.qualified_name:
        of_parent = f" of {chunk.parent_name}" if chunk.parent_name else ""
        header.append(f"# Symbol: {chunk.qualified_name} ({chunk.kind}{of_parent})")
    if chunk.signature:
        header.append(f"# Signature: {' '.join(chunk.signature.split())}")
    return "\n".join(header) + "\n" + chunk.content


def sparse_text(path: str, chunk: Chunk) -> str:
    """Raw text for BM25. Identifier expansion happens inside the sparse encoder."""

    parts = [path, chunk.qualified_name or "", chunk.docstring or "", chunk.content]
    return "\n".join(p for p in parts if p)
```


### Step 2.4: Reciprocal Rank Fusion (`retrieval/fusion.py`)

**What:** ten lines that merge ranked lists. The store's `hybrid_local` mode uses it, so it
has to exist now; Phase 3 explains and tests it in depth.

<!-- file: src/codeqa/retrieval/fusion.py -->
**`src/codeqa/retrieval/fusion.py`**

```python
from collections.abc import Hashable, Sequence

RRF_K = 60


def reciprocal_rank_fusion[T: Hashable](
    rankings: Sequence[Sequence[T]], k: int = RRF_K
) -> list[tuple[T, float]]:
    """Fuse several ranked lists into one.

    score(d) = sum over lists of 1 / (k + rank(d)), rank starting at 1.

    Uses only *ranks*, never raw scores, so BM25 scores (0..inf) and cosine
    similarities (-1..1) can be combined without normalisation. k=60 comes from the
    original paper (Cormack et al., 2009) and damps the influence of the very top ranks.
    """

    scores: dict[T, float] = {}
    for ranking in rankings:
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
```


### Step 2.5: The Qdrant adapter (`retrieval/store.py`)

**What:** everything that talks to Qdrant: create the collection, upsert, delete, count,
and search in four modes.

**Why each design choice:**

- **Named vectors `dense` and `sparse`:** one point holds both, so one query can use both.
  The names must match between upsert and query; they are constants for that reason.
- **Dimension check in `ensure_collection`:** a collection built for a 768-d model cannot
  take 384-d vectors. Failing early with a clear message ("use another collection name")
  beats a cryptic error mid-index.
- **Payload indexes** on `repo_id`, `file_id`, `path_prefixes`, `language`, `kind`: every
  search filters by `repo_id`; without an index Qdrant scans all points. (Embedded
  mode has no payload indexes, so we skip them there.)
- **`path_prefixes`:** a file `a/b/c.py` stores `["a", "a/b", "a/b/c.py"]`. "Only search
  under `a/b`" becomes an exact keyword match, which is fast and needs no special index.
- **`MAX_PAYLOAD_CHARS`:** a single generated 2 MB chunk should not bloat Qdrant's memory.
- **Search modes:** `dense`, `sparse` and `hybrid` are the three ablation variants.
  `hybrid` sends two *prefetch* queries and fuses them with RRF on the server in a single
  request. `hybrid_local` does the same with our own RRF so you can check they agree.
- **`get_qdrant_client()`** chooses server, in-memory, or on-disk embedded mode from
  settings, once per process.

<!-- file: src/codeqa/retrieval/store.py -->
**`src/codeqa/retrieval/store.py`**

```python
import uuid
from collections.abc import Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Literal

from qdrant_client import QdrantClient, models

from codeqa.config import get_settings
from codeqa.retrieval.fusion import reciprocal_rank_fusion
from codeqa.retrieval.sparse import SparseVector

DENSE = "dense"
SPARSE = "sparse"
PAYLOAD_INDEXES = ("repo_id", "file_id", "path_prefixes", "language", "kind")
MAX_PAYLOAD_CHARS = 8000  # cap `content` so one giant chunk cannot bloat Qdrant memory

SearchMode = Literal["dense", "sparse", "hybrid", "hybrid_local"]


@dataclass
class ChunkPoint:
    id: uuid.UUID
    dense: list[float]
    sparse: SparseVector
    payload: dict[str, Any]


@dataclass
class StoreHit:
    id: str
    score: float
    payload: dict[str, Any]


@dataclass
class SearchFilters:
    path_prefix: str | None = None  # e.g. "src/httpx" (a directory)
    language: str | None = None
    kind: str | None = None
    extra: dict[str, str] = field(default_factory=dict)


def path_prefixes(path: str) -> list[str]:
    """`a/b/c.py` -> [`a`, `a/b`, `a/b/c.py`]. Lets us filter by folder with exact match."""

    parts = path.split("/")
    return ["/".join(parts[: i + 1]) for i in range(len(parts))]


@lru_cache(maxsize=1)
def get_qdrant_client() -> QdrantClient:
    settings = get_settings()
    if settings.qdrant_location == ":memory:":
        return QdrantClient(location=":memory:")  # embedded, in RAM (tests)
    if settings.qdrant_location:
        return QdrantClient(path=settings.qdrant_location)  # embedded, on disk
    return QdrantClient(url=settings.qdrant_url, timeout=30)


class QdrantStore:
    """Adapter around one Qdrant collection holding a named dense + named sparse vector."""

    def __init__(self, client: QdrantClient, collection: str) -> None:
        self._client = client
        self.collection = collection

    # ---------------------------------------------------------------- setup

    def ensure_collection(self, dim: int) -> None:
        if self._client.collection_exists(self.collection):
            info = self._client.get_collection(self.collection)
            vectors = info.config.params.vectors
            existing = vectors[DENSE].size if isinstance(vectors, dict) else None
            if existing != dim:
                raise ValueError(
                    f"collection {self.collection!r} has dim {existing}, model gives {dim}. "
                    "Use another collection name for a different embedding model."
                )
            return

        self._client.create_collection(
            self.collection,
            vectors_config={DENSE: models.VectorParams(size=dim, distance=models.Distance.COSINE)},
            # IDF modifier: Qdrant computes inverse document frequency over the collection,
            # which turns our term-frequency vectors into real BM25 scores.
            sparse_vectors_config={SPARSE: models.SparseVectorParams(modifier=models.Modifier.IDF)},
        )
        options = self._client.init_options
        is_embedded = options.get("location") == ":memory:" or options.get("path") is not None
        if not is_embedded:  # embedded mode has no payload indexes (and warns if asked)
            for field_name in PAYLOAD_INDEXES:
                self._client.create_payload_index(
                    self.collection, field_name, models.PayloadSchemaType.KEYWORD
                )

    # --------------------------------------------------------------- writes

    def upsert(self, points: Sequence[ChunkPoint], batch_size: int = 128) -> None:
        for start in range(0, len(points), batch_size):
            batch = points[start : start + batch_size]
            self._client.upsert(
                self.collection,
                points=[
                    models.PointStruct(
                        id=str(p.id),
                        vector={
                            DENSE: p.dense,
                            SPARSE: models.SparseVector(
                                indices=p.sparse.indices, values=p.sparse.values
                            ),
                        },
                        payload=_capped(p.payload),
                    )
                    for p in batch
                ],
                wait=True,
            )

    def delete_ids(self, ids: Sequence[uuid.UUID]) -> None:
        if ids:
            self._client.delete(
                self.collection,
                points_selector=models.PointIdsList(points=[str(i) for i in ids]),
                wait=True,
            )

    def delete_where(self, key: str, value: str) -> None:
        if not self._client.collection_exists(self.collection):
            return
        self._client.delete(
            self.collection,
            points_selector=models.FilterSelector(filter=_match(key, value)),
            wait=True,
        )

    def count(self, repo_id: str) -> int:
        if not self._client.collection_exists(self.collection):
            return 0
        return self._client.count(self.collection, count_filter=_match("repo_id", repo_id)).count

    # ---------------------------------------------------------------- reads

    def search(
        self,
        *,
        repo_id: str,
        mode: SearchMode,
        dense: list[float] | None,
        sparse: SparseVector | None,
        limit: int,
        filters: SearchFilters | None = None,
    ) -> list[StoreHit]:
        flt = _build_filter(repo_id, filters)
        if mode == "dense":
            return self._query(models_query=dense, using=DENSE, flt=flt, limit=limit)
        if mode == "sparse":
            return self._query(models_query=_to_qdrant(sparse), using=SPARSE, flt=flt, limit=limit)
        if mode == "hybrid":
            # Server-side fusion: two prefetches, fused with RRF, one round trip.
            response = self._client.query_points(
                self.collection,
                prefetch=[
                    models.Prefetch(query=dense, using=DENSE, filter=flt, limit=limit * 2),
                    models.Prefetch(
                        query=_to_qdrant(sparse), using=SPARSE, filter=flt, limit=limit * 2
                    ),
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                query_filter=flt,
                limit=limit,
                with_payload=True,
            )
            return [StoreHit(str(p.id), p.score, p.payload or {}) for p in response.points]
        # "hybrid_local": the same idea with our own RRF, to check we understand it.
        dense_hits = self._query(models_query=dense, using=DENSE, flt=flt, limit=limit * 2)
        sparse_hits = self._query(
            models_query=_to_qdrant(sparse), using=SPARSE, flt=flt, limit=limit * 2
        )
        by_id = {h.id: h for h in [*dense_hits, *sparse_hits]}
        fused = reciprocal_rank_fusion([[h.id for h in dense_hits], [h.id for h in sparse_hits]])
        return [StoreHit(i, score, by_id[i].payload) for i, score in fused[:limit]]

    def _query(
        self,
        *,
        models_query: list[float] | models.SparseVector | None,
        using: str,
        flt: models.Filter,
        limit: int,
    ) -> list[StoreHit]:
        if models_query is None:
            raise ValueError(f"mode needs a {using} query vector")
        response = self._client.query_points(
            self.collection,
            query=models_query,
            using=using,
            query_filter=flt,
            limit=limit,
            with_payload=True,
        )
        return [StoreHit(str(p.id), p.score, p.payload or {}) for p in response.points]


def _capped(payload: dict[str, Any]) -> dict[str, Any]:
    content = payload.get("content")
    if isinstance(content, str) and len(content) > MAX_PAYLOAD_CHARS:
        return {**payload, "content": content[:MAX_PAYLOAD_CHARS] + "\n# ... (truncated)"}
    return payload


def _match(key: str, value: str) -> models.Filter:
    condition = models.FieldCondition(key=key, match=models.MatchValue(value=value))
    return models.Filter(must=[condition])


def _build_filter(repo_id: str, filters: SearchFilters | None) -> models.Filter:
    must: list[models.Condition] = [
        models.FieldCondition(key="repo_id", match=models.MatchValue(value=repo_id))
    ]
    if filters is not None:
        conditions = {
            "path_prefixes": filters.path_prefix.strip("/") if filters.path_prefix else None,
            "language": filters.language,
            "kind": filters.kind,
            **filters.extra,
        }
        for key, value in conditions.items():
            if value:
                must.append(models.FieldCondition(key=key, match=models.MatchValue(value=value)))
    return models.Filter(must=must)


def _to_qdrant(sparse: SparseVector | None) -> models.SparseVector | None:
    if sparse is None:
        return None
    return models.SparseVector(indices=sparse.indices, values=sparse.values)
```


### Step 2.6: Data access (`db/repositories.py`)

**What:** every SQL query in the project, as small functions.

**Why:** services never build queries inline. That keeps SQL in one reviewable file and
makes services easy to read. A few functions here are only used in later phases
(`callers_of`, `repo_outline`, `add_query_log`, ...); they are explained where they are
used. Things worth noticing now:

- **Delete order** (`delete_files`, `replace_file_contents`): first *unlink* edges that
  point at the chunks being deleted, then delete the file's own edges, then chunks, then
  files. Foreign keys forbid deleting a row that another row still references.
- **`session.flush()`** sends pending SQL without committing, so generated ids exist and
  the next statement can reference them, while the whole thing can still roll back.
- **`resolve_edges`** is the name-matching resolver described in Step 1.6: prefer a unique
  definition in the same file, else a unique one in the repo, else leave it `NULL`.

<!-- file: src/codeqa/db/repositories.py -->
**`src/codeqa/db/repositories.py`**

```python
"""Data-access functions. All SQL lives here, so services never build queries inline."""

import uuid
from collections.abc import Iterable, Sequence
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from codeqa.models import (
    Chunk,
    EvalRun,
    Feedback,
    File,
    IndexJob,
    QueryLog,
    Repository,
    SymbolEdge,
)
from codeqa.models.base import utcnow

# ------------------------------------------------------------------ repositories


def get_repository_by_name(session: Session, name: str) -> Repository | None:
    return session.scalar(select(Repository).where(Repository.name == name))


def get_repository(session: Session, repository_id: uuid.UUID) -> Repository | None:
    return session.get(Repository, repository_id)


def list_repositories(session: Session) -> list[tuple[Repository, int, int]]:
    """Each repo with its file count and chunk count."""

    files = (
        select(File.repository_id, func.count(File.id).label("n"))
        .group_by(File.repository_id)
        .subquery()
    )
    chunks = (
        select(Chunk.repository_id, func.count(Chunk.id).label("n"))
        .group_by(Chunk.repository_id)
        .subquery()
    )
    rows = session.execute(
        select(Repository, func.coalesce(files.c.n, 0), func.coalesce(chunks.c.n, 0))
        .outerjoin(files, files.c.repository_id == Repository.id)
        .outerjoin(chunks, chunks.c.repository_id == Repository.id)
        .order_by(Repository.name)
    ).all()
    return [(repo, int(n_files), int(n_chunks)) for repo, n_files, n_chunks in rows]


def delete_repository_data(session: Session, repository_id: uuid.UUID) -> None:
    """Remove every file/chunk/edge row of a repo (children first: foreign keys)."""

    session.execute(delete(SymbolEdge).where(SymbolEdge.repository_id == repository_id))
    session.execute(delete(Chunk).where(Chunk.repository_id == repository_id))
    session.execute(delete(File).where(File.repository_id == repository_id))


# -------------------------------------------------------------------------- jobs


def create_job(session: Session, repository_id: uuid.UUID) -> IndexJob:
    job = IndexJob(repository_id=repository_id, status="pending")
    session.add(job)
    session.flush()  # assigns job.id without committing
    return job


def get_job(session: Session, job_id: uuid.UUID) -> IndexJob | None:
    return session.get(IndexJob, job_id)


def update_job(session: Session, job_id: uuid.UUID, **values: Any) -> None:
    session.execute(update(IndexJob).where(IndexJob.id == job_id).values(**values))


# ------------------------------------------------------------------------- files


def files_by_path(session: Session, repository_id: uuid.UUID) -> dict[str, File]:
    rows = session.scalars(select(File).where(File.repository_id == repository_id))
    return {f.path: f for f in rows}


def chunk_ids_for_files(session: Session, file_ids: Sequence[uuid.UUID]) -> list[uuid.UUID]:
    if not file_ids:
        return []
    return list(session.scalars(select(Chunk.id).where(Chunk.file_id.in_(file_ids))))


def delete_files(session: Session, file_ids: Sequence[uuid.UUID]) -> None:
    """Delete files with their chunks and edges. Edges first: they point at chunks."""

    if not file_ids:
        return
    chunk_ids = select(Chunk.id).where(Chunk.file_id.in_(file_ids))
    session.execute(
        update(SymbolEdge)
        .where(SymbolEdge.target_chunk_id.in_(chunk_ids))
        .values(target_chunk_id=None)
    )
    session.execute(delete(SymbolEdge).where(SymbolEdge.file_id.in_(file_ids)))
    session.execute(delete(Chunk).where(Chunk.file_id.in_(file_ids)))
    session.execute(delete(File).where(File.id.in_(file_ids)))


def replace_file_contents(
    session: Session,
    file: File,
    chunks: Iterable[Chunk],
    edges: Iterable[SymbolEdge],
) -> None:
    """Swap a file's chunks and edges for new ones inside the caller's transaction."""

    chunk_ids = select(Chunk.id).where(Chunk.file_id == file.id)
    session.execute(
        update(SymbolEdge)
        .where(SymbolEdge.target_chunk_id.in_(chunk_ids))
        .values(target_chunk_id=None)
    )
    session.execute(delete(SymbolEdge).where(SymbolEdge.file_id == file.id))
    session.execute(delete(Chunk).where(Chunk.file_id == file.id))
    session.flush()
    session.add_all(chunks)
    session.flush()
    session.add_all(edges)


def count_chunks(session: Session, repository_id: uuid.UUID) -> int:
    return int(
        session.scalar(select(func.count(Chunk.id)).where(Chunk.repository_id == repository_id))
        or 0
    )


# ------------------------------------------------------------------ call graph


def resolve_edges(session: Session, repository_id: uuid.UUID) -> int:
    """Point each call edge at the chunk it most likely calls. Returns how many resolved.

    Best effort by *name*: prefer a definition in the same file, else a unique match in
    the repo. Ambiguous names (e.g. five different `run` methods) stay unresolved; real
    resolution needs type inference, which is out of scope.
    """

    definitions: dict[str, list[tuple[uuid.UUID, uuid.UUID]]] = {}
    rows = session.execute(
        select(Chunk.symbol_name, Chunk.id, Chunk.file_id).where(
            Chunk.repository_id == repository_id,
            Chunk.kind.in_(("function", "method", "class_skeleton")),
            Chunk.part_index == 0,
        )
    )
    for name, chunk_id, file_id in rows:
        if name:
            definitions.setdefault(name, []).append((chunk_id, file_id))

    resolved = 0
    edges = session.scalars(
        select(SymbolEdge).where(
            SymbolEdge.repository_id == repository_id, SymbolEdge.kind == "call"
        )
    )
    for edge in edges:
        candidates = definitions.get(edge.target_name, [])
        same_file = [c for c, f in candidates if f == edge.file_id]
        target = same_file[0] if len(same_file) == 1 else None
        if target is None and len(candidates) == 1:
            target = candidates[0][0]
        edge.target_chunk_id = target
        resolved += target is not None
    return resolved


def find_symbol_chunks(session: Session, repository_id: uuid.UUID, name: str) -> list[Chunk]:
    """Chunks whose symbol or qualified name equals `name` (e.g. `send` or `Client.send`)."""

    return list(
        session.scalars(
            select(Chunk).where(
                Chunk.repository_id == repository_id,
                Chunk.part_index == 0,
                (Chunk.symbol_name == name) | (Chunk.qualified_name == name),
            )
        )
    )


def callers_of(session: Session, repository_id: uuid.UUID, names: Sequence[str]) -> list[Chunk]:
    """Chunks that call any of `names` (matched on the plain target name)."""

    source_ids = select(SymbolEdge.source_chunk_id).where(
        SymbolEdge.repository_id == repository_id,
        SymbolEdge.kind == "call",
        SymbolEdge.target_name.in_(names),
    )
    return list(session.scalars(select(Chunk).where(Chunk.id.in_(source_ids))))


def callees_of(session: Session, chunk_ids: Sequence[uuid.UUID]) -> list[Chunk]:
    """Resolved chunks called from any of `chunk_ids`."""

    target_ids = select(SymbolEdge.target_chunk_id).where(
        SymbolEdge.source_chunk_id.in_(chunk_ids), SymbolEdge.target_chunk_id.is_not(None)
    )
    return list(session.scalars(select(Chunk).where(Chunk.id.in_(target_ids))))


def paths_for_chunks(session: Session, chunks: Sequence[Chunk]) -> dict[uuid.UUID, str]:
    file_ids = {c.file_id for c in chunks}
    if not file_ids:
        return {}
    rows = session.execute(select(File.id, File.path).where(File.id.in_(file_ids)))
    return {file_id: path for file_id, path in rows}


# ---------------------------------------------------------------------- repo map


def repo_outline(
    session: Session, repository_id: uuid.UUID
) -> tuple[list[str], dict[str, list[str]], list[Chunk]]:
    """(all file paths, top-level symbols per path, README section chunks)."""

    paths = sorted(session.scalars(select(File.path).where(File.repository_id == repository_id)))
    symbols: dict[str, list[str]] = {}
    rows = session.execute(
        select(File.path, Chunk.kind, Chunk.qualified_name)
        .join(File, File.id == Chunk.file_id)
        .where(
            Chunk.repository_id == repository_id,
            Chunk.part_index == 0,
            Chunk.parent_name.is_(None),
            Chunk.kind.in_(("function", "class_skeleton")),
        )
        .order_by(File.path, Chunk.start_line)
    )
    for path, kind, name in rows:
        prefix = "class " if kind == "class_skeleton" else "def "
        symbols.setdefault(path, []).append(prefix + (name or "?"))

    readme = list(
        session.scalars(
            select(Chunk)
            .join(File, File.id == Chunk.file_id)
            .where(
                Chunk.repository_id == repository_id,
                Chunk.kind == "doc_section",
                func.lower(File.path).like("readme%"),
            )
            .order_by(Chunk.start_line)
        )
    )
    return paths, symbols, readme


# ------------------------------------------------------------ logs and feedback


def add_query_log(session: Session, log: QueryLog) -> uuid.UUID:
    session.add(log)
    session.flush()
    return log.id


def add_feedback(
    session: Session, query_log_id: uuid.UUID, rating: int, comment: str | None
) -> Feedback | None:
    if session.get(QueryLog, query_log_id) is None:
        return None
    feedback = Feedback(query_log_id=query_log_id, rating=rating, comment=comment)
    session.add(feedback)
    session.flush()
    return feedback


def add_eval_run(session: Session, run: EvalRun) -> None:
    session.add(run)


def mark_repository(session: Session, repository_id: uuid.UUID, status: str) -> None:
    values: dict[str, Any] = {"status": status}
    if status == "ready":
        values["last_indexed_at"] = utcnow()
    session.execute(update(Repository).where(Repository.id == repository_id).values(**values))
```


### Step 2.7: The indexing pipeline (`ingest/pipeline.py`)

**What:** `IndexingService`, which runs walk, chunk, edges, embed, write.

**How to read it (top to bottom):**

1. `prepare()` creates or updates the `repositories` row and a pending `index_jobs` row.
   If the repo was indexed before with a *different* chunker, model or collection, the old
   data is incompatible, so it is deleted. Returning `(repo_id, job_id)` quickly lets the
   API respond at once and run the slow part in the background (Phase 7).
2. `run()` wraps `_run()`: any exception marks the job `failed` with the error text, then
   re-raises. A job is never left "running" forever.
3. `_run()` walks the repo, compares each file's SHA-256 with the stored one (unchanged
   files are skipped: this is **incremental re-indexing**), prepares changed files,
   buffers them, and flushes every 128 chunks.
4. `_prepare_file()` runs the chunker and edge extractor for one file. It is wrapped in
   `try/except` in `_run()`: **one bad file must not kill the job**. Failures are counted
   and stored on the job.
5. `_flush()` embeds the whole buffer in one call (batching across files is much faster
   than one small call per file), then writes file by file.
6. `_write_file()` does the crash-safe write: Qdrant upsert first; then in one Postgres
   transaction delete stale Qdrant points, update or insert the file row with the new
   hash, and replace its chunks and edges. The commit at the end means "this file is done".
7. `_delete_removed()` removes files that disappeared from the repo, from both stores.
8. Finally: resolve edges, compare Postgres and Qdrant counts (a mismatch is logged as a
   warning), and mark the job and repo finished.

<!-- file: src/codeqa/ingest/pipeline.py -->
**`src/codeqa/ingest/pipeline.py`**

```python
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from codeqa.config import get_settings
from codeqa.db import repositories as repo_dao
from codeqa.db.session import SessionFactory, session_scope
from codeqa.ingest.chunkers import chunker_for
from codeqa.ingest.chunkers.base import Chunk
from codeqa.ingest.edges import MODULE_OWNER, extract_edges
from codeqa.ingest.ids import chunk_id
from codeqa.ingest.source import is_remote, resolve_source
from codeqa.ingest.walker import WalkedFile, walk_repository
from codeqa.logging import get_logger
from codeqa.models import Chunk as ChunkRow
from codeqa.models import File, Repository
from codeqa.models import SymbolEdge as EdgeRow
from codeqa.models.base import utcnow
from codeqa.retrieval.embedder import Embedder
from codeqa.retrieval.sparse import SparseEncoder, SparseVector
from codeqa.retrieval.store import ChunkPoint, QdrantStore, path_prefixes
from codeqa.retrieval.texts import embedding_text, sparse_text

log = get_logger(__name__)

ProgressCallback = Callable[[int, int], None]  # (files_done, files_total)
FLUSH_EVERY_CHUNKS = 128  # embed chunks from several files in one batch: much faster


class IndexingError(RuntimeError):
    pass


@dataclass
class IndexStats:
    repository_id: uuid.UUID
    job_id: uuid.UUID
    files_seen: int = 0
    files_added: int = 0
    files_updated: int = 0
    files_unchanged: int = 0
    files_deleted: int = 0
    files_failed: int = 0
    chunks_written: int = 0
    edges_resolved: int = 0
    seconds: float = 0.0
    errors: list[str] = field(default_factory=list)


@dataclass
class _PreparedFile:
    walked: WalkedFile
    existing: File | None
    chunks: list[Chunk]
    ids: list[uuid.UUID]
    edges: list[tuple[str, str, str]]  # (source_qualified_name, target_name, kind)


class IndexingService:
    """walk -> chunk -> extract edges -> embed -> write Qdrant -> write Postgres.

    Incremental: files whose SHA-256 did not change are skipped. Crash-safe: for each
    file, Qdrant is written first and the Postgres transaction (which stores the new
    hash) commits last. If we crash in between, the old hash is still in Postgres, so
    the next run simply redoes that file. Deterministic ids make the redo an upsert.
    """

    def __init__(
        self,
        store_for: Callable[[str], QdrantStore],
        embedder_for: Callable[[str], Embedder],
        sparse: SparseEncoder,
        session_factory: SessionFactory | None = None,
    ) -> None:
        self._store_for = store_for
        self._embedder_for = embedder_for
        self._sparse = sparse
        self._session_factory = session_factory

    # ------------------------------------------------------------------ public

    def prepare(
        self,
        path_or_url: str,
        name: str,
        *,
        chunker: str = "ast",
        embedding_model: str | None = None,
        collection: str | None = None,
    ) -> tuple[uuid.UUID, uuid.UUID]:
        """Create/update the repository row and a pending job. Returns (repo_id, job_id).

        Split from `run()` so the API can answer immediately with a job id and do the
        slow part in the background.
        """

        settings = get_settings()
        model = embedding_model or settings.embedding_model
        collection_name = collection or settings.qdrant_collection
        with session_scope(self._session_factory) as session:
            repo = repo_dao.get_repository_by_name(session, name)
            if repo is None:
                repo = Repository(name=name, local_path="", source_url=None)
                session.add(repo)
            elif (repo.chunker, repo.embedding_model, repo.collection_name) != (
                chunker,
                model,
                collection_name,
            ):
                # Settings changed: old vectors are incompatible, rebuild from scratch.
                if repo.collection_name:
                    self._store_for(repo.collection_name).delete_where("repo_id", str(repo.id))
                repo_dao.delete_repository_data(session, repo.id)
            repo.source_url = path_or_url if is_remote(path_or_url) else None
            repo.local_path = path_or_url
            repo.chunker = chunker
            repo.embedding_model = model
            repo.collection_name = collection_name
            repo.status = "pending"
            session.flush()
            job = repo_dao.create_job(session, repo.id)
            return repo.id, job.id

    def run(
        self,
        repository_id: uuid.UUID,
        job_id: uuid.UUID,
        *,
        on_progress: ProgressCallback | None = None,
        allowed_root: Path | None = None,
    ) -> IndexStats:
        started = time.perf_counter()
        stats = IndexStats(repository_id=repository_id, job_id=job_id)
        try:
            self._run(stats, on_progress, allowed_root)
        except Exception as exc:
            log.exception("index_failed", repository_id=str(repository_id))
            with session_scope(self._session_factory) as session:
                repo_dao.update_job(
                    session, job_id, status="failed", error=str(exc)[:2000], finished_at=utcnow()
                )
                repo_dao.mark_repository(session, repository_id, "failed")
            raise
        stats.seconds = round(time.perf_counter() - started, 2)
        log.info("index_finished", **{k: v for k, v in vars(stats).items() if k != "errors"})
        return stats

    def index(
        self,
        path_or_url: str,
        name: str,
        *,
        chunker: str = "ast",
        embedding_model: str | None = None,
        collection: str | None = None,
        on_progress: ProgressCallback | None = None,
    ) -> IndexStats:
        """`prepare` + `run` in one call (what the CLI uses)."""

        repo_id, job_id = self.prepare(
            path_or_url,
            name,
            chunker=chunker,
            embedding_model=embedding_model,
            collection=collection,
        )
        return self.run(repo_id, job_id, on_progress=on_progress)

    # ----------------------------------------------------------------- private

    def _run(
        self, stats: IndexStats, on_progress: ProgressCallback | None, allowed_root: Path | None
    ) -> None:
        settings = get_settings()
        with session_scope(self._session_factory) as session:
            repo = repo_dao.get_repository(session, stats.repository_id)
            if repo is None:
                raise IndexingError(f"repository {stats.repository_id} not found")
            source = resolve_source(repo.local_path, allowed_root=allowed_root)
            repo.local_path = str(source.local_path)
            repo.commit_sha = source.commit_sha
            repo.status = "indexing"
            chunker_name, model, collection = (
                repo.chunker,
                repo.embedding_model,
                repo.collection_name,
            )
            existing = repo_dao.files_by_path(session, repo.id)
            repo_dao.update_job(session, stats.job_id, status="running", started_at=utcnow())

        embedder = self._embedder_for(model)
        store = self._store_for(collection)
        store.ensure_collection(embedder.dim)

        walked = list(walk_repository(source.local_path))
        stats.files_seen = len(walked)
        seen_paths = {w.relative_path for w in walked}
        buffer: list[_PreparedFile] = []
        buffered_chunks = 0
        total_chunks = 0

        for done, item in enumerate(walked, start=1):
            previous = existing.get(item.relative_path)
            if previous is not None and previous.content_hash == item.content_hash:
                stats.files_unchanged += 1
            else:
                try:
                    prepared = self._prepare_file(item, previous, stats.repository_id, chunker_name)
                except Exception as exc:  # one bad file must not kill the whole job
                    stats.files_failed += 1
                    stats.errors.append(f"{item.relative_path}: {exc}")
                    log.warning("file_failed", path=item.relative_path, error=str(exc))
                else:
                    total_chunks += len(prepared.chunks)
                    if total_chunks > settings.max_repo_chunks:
                        raise IndexingError(
                            f"repo exceeds max_repo_chunks={settings.max_repo_chunks}"
                        )
                    buffer.append(prepared)
                    buffered_chunks += len(prepared.chunks)

            if buffered_chunks >= FLUSH_EVERY_CHUNKS or done == len(walked):
                self._flush(buffer, stats, embedder, store)
                buffer, buffered_chunks = [], 0
                with session_scope(self._session_factory) as session:
                    repo_dao.update_job(
                        session,
                        stats.job_id,
                        files_processed=done,
                        chunks_created=stats.chunks_written,
                    )
            if on_progress is not None:
                on_progress(done, len(walked))

        removed = [f for path, f in existing.items() if path not in seen_paths]
        self._delete_removed(removed, store, stats)

        with session_scope(self._session_factory) as session:
            stats.edges_resolved = repo_dao.resolve_edges(session, stats.repository_id)
            pg_count = repo_dao.count_chunks(session, stats.repository_id)
            qdrant_count = store.count(str(stats.repository_id))
            if pg_count != qdrant_count:
                log.warning("count_mismatch", postgres=pg_count, qdrant=qdrant_count)
            repo_dao.update_job(
                session,
                stats.job_id,
                status="completed_with_errors" if stats.files_failed else "completed",
                finished_at=utcnow(),
                files_processed=stats.files_seen,
                chunks_created=stats.chunks_written,
                error="\n".join(stats.errors)[:2000] or None,
            )
            repo_dao.mark_repository(session, stats.repository_id, "ready")

    def _prepare_file(
        self, item: WalkedFile, previous: File | None, repository_id: uuid.UUID, chunker_name: str
    ) -> _PreparedFile:
        source = item.path.read_bytes()
        chunks = chunker_for(item.language, chunker_name).chunk_file(item.path, source)
        ids = [
            chunk_id(
                repository_id,
                item.relative_path,
                c.kind,
                c.qualified_name,
                c.start_line,
                c.part_index,
            )
            for c in chunks
        ]
        edges: list[tuple[str, str, str]] = []
        if item.language == "python" and chunker_name == "ast":
            edges = [
                (e.source_qualified_name, e.target_name, e.kind)
                for e in extract_edges(item.path, source)
            ]
        return _PreparedFile(item, previous, chunks, ids, edges)

    def _flush(
        self,
        batch: list[_PreparedFile],
        stats: IndexStats,
        embedder: Embedder,
        store: QdrantStore,
    ) -> None:
        if not batch:
            return
        dense_texts = [embedding_text(p.walked.relative_path, c) for p in batch for c in p.chunks]
        sparse_texts = [sparse_text(p.walked.relative_path, c) for p in batch for c in p.chunks]
        dense = embedder.embed_documents(dense_texts)
        sparse = self._sparse.embed_documents(sparse_texts)

        offset = 0
        for prepared in batch:
            n = len(prepared.chunks)
            self._write_file(
                prepared, dense[offset : offset + n], sparse[offset : offset + n], stats, store
            )
            offset += n

    def _write_file(
        self,
        prepared: _PreparedFile,
        dense: list[list[float]],
        sparse: list[SparseVector],
        stats: IndexStats,
        store: QdrantStore,
    ) -> None:
        item = prepared.walked
        file_id = prepared.existing.id if prepared.existing else uuid.uuid4()
        repo_id = stats.repository_id

        # 1) Qdrant first (idempotent upsert), then remove points that no longer exist.
        points = [
            ChunkPoint(
                id=cid,
                dense=d,
                sparse=s,
                payload={
                    "repo_id": str(repo_id),
                    "file_id": str(file_id),
                    "path": item.relative_path,
                    "path_prefixes": path_prefixes(item.relative_path),
                    "language": item.language,
                    "kind": c.kind,
                    "symbol_name": c.symbol_name,
                    "qualified_name": c.qualified_name,
                    "signature": c.signature,
                    "docstring": c.docstring,
                    "start_line": c.start_line,
                    "end_line": c.end_line,
                    "content": c.content,
                },
            )
            for cid, c, d, s in zip(prepared.ids, prepared.chunks, dense, sparse, strict=True)
        ]
        store.upsert(points)

        # 2) Postgres in one transaction. Commit = "this file is done".
        with session_scope(self._session_factory) as session:
            if prepared.existing is not None:
                old_ids = repo_dao.chunk_ids_for_files(session, [file_id])
                store.delete_ids([i for i in old_ids if i not in set(prepared.ids)])
                file = session.merge(prepared.existing)
                file.content_hash = item.content_hash
                file.size_bytes = item.size_bytes
                file.language = item.language
                file.indexed_at = utcnow()
                stats.files_updated += 1
            else:
                file = File(
                    id=file_id,
                    repository_id=repo_id,
                    path=item.relative_path,
                    language=item.language,
                    content_hash=item.content_hash,
                    size_bytes=item.size_bytes,
                    indexed_at=utcnow(),
                )
                session.add(file)
                stats.files_added += 1
            session.flush()

            rows = [
                ChunkRow(
                    id=cid,
                    file_id=file_id,
                    repository_id=repo_id,
                    kind=c.kind,
                    symbol_name=c.symbol_name,
                    qualified_name=c.qualified_name,
                    parent_name=c.parent_name,
                    signature=c.signature,
                    docstring=c.docstring,
                    start_line=c.start_line,
                    end_line=c.end_line,
                    part_index=c.part_index,
                    content=c.content,
                    token_count=c.token_count,
                )
                for cid, c in zip(prepared.ids, prepared.chunks, strict=True)
            ]
            owner_ids = _owner_chunk_ids(prepared)
            edge_rows = [
                EdgeRow(
                    repository_id=repo_id,
                    file_id=file_id,
                    source_chunk_id=owner_ids.get(source),
                    source_name=source,
                    target_name=target,
                    kind=kind,
                )
                for source, target, kind in prepared.edges
            ]
            repo_dao.replace_file_contents(session, file, rows, edge_rows)
        stats.chunks_written += len(rows)

    def _delete_removed(self, removed: list[File], store: QdrantStore, stats: IndexStats) -> None:
        if not removed:
            return
        for file in removed:
            store.delete_where("file_id", str(file.id))
        with session_scope(self._session_factory) as session:
            repo_dao.delete_files(session, [f.id for f in removed])
        stats.files_deleted = len(removed)


def _owner_chunk_ids(prepared: _PreparedFile) -> dict[str, uuid.UUID]:
    """Map an edge owner name to its chunk: `Client.send` -> id of part 0 of that method."""

    owners: dict[str, uuid.UUID] = {}
    for cid, chunk in zip(prepared.ids, prepared.chunks, strict=True):
        if chunk.part_index != 0:
            continue
        if chunk.kind in ("function", "method") and chunk.qualified_name:
            owners.setdefault(chunk.qualified_name, cid)
        elif chunk.kind == "module":
            owners.setdefault(MODULE_OWNER, cid)
    return owners
```


### Step 2.8: Building real services (`container.py`)

**What:** the one place that wires real implementations together (Qdrant client, fastembed
models) for the CLI and API.

**Why:** "composition root". Services receive their dependencies through the constructor
(dependency injection), so tests pass fakes and production passes real objects. This file
grows in Phase 3 and Phase 6.

<!-- file: src/codeqa/container.py -->
**`src/codeqa/container.py`**

```python
"""Builds the real services once per process. CLI and API both get services from here.

Tests do not use this module: they construct services with fakes directly.
"""

from functools import lru_cache

from codeqa.config import get_settings
from codeqa.ingest.pipeline import IndexingService
from codeqa.retrieval.embedder import get_embedder
from codeqa.retrieval.sparse import get_sparse_encoder
from codeqa.retrieval.store import QdrantStore, get_qdrant_client


def store_for(collection: str) -> QdrantStore:
    return QdrantStore(get_qdrant_client(), collection)


@lru_cache
def get_indexing_service() -> IndexingService:
    return IndexingService(
        store_for=store_for,
        embedder_for=get_embedder,
        sparse=get_sparse_encoder(get_settings().sparse_model),
    )
```


### Step 2.9: CLI `index`, `status`, `job` (`cli/index.py`)

**What:** index with a progress bar; list repos; show a job.

<!-- file: src/codeqa/cli/index.py -->
**`src/codeqa/cli/index.py`**

```python
import uuid
from dataclasses import asdict
from typing import Annotated

import typer
from rich.markup import escape
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn, TimeElapsedColumn
from rich.table import Table

from codeqa.cli.app import JsonOption, app, console, print_json
from codeqa.errors import NotFoundError


@app.command()
def index(
    source: Annotated[str, typer.Argument(help="Local folder or git URL")],
    repo_name: Annotated[str, typer.Option("--repo-name", "-n", help="Name to store it under")],
    chunker: Annotated[str, typer.Option(help="ast | fixed (baseline)")] = "ast",
    embedding_model: Annotated[str | None, typer.Option(help="Override EMBEDDING_MODEL")] = None,
    collection: Annotated[str | None, typer.Option(help="Override QDRANT_COLLECTION")] = None,
    as_json: JsonOption = False,
) -> None:
    """Index (or incrementally re-index) a repository."""

    from codeqa.container import get_indexing_service

    service = get_indexing_service()
    with Progress(
        TextColumn("[bold]Indexing"),
        BarColumn(),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
        disable=as_json,
    ) as progress:
        task = progress.add_task("index", total=None)
        stats = service.index(
            source,
            repo_name,
            chunker=chunker,
            embedding_model=embedding_model,
            collection=collection,
            on_progress=lambda done, total: progress.update(task, completed=done, total=total),
        )

    if as_json:
        print_json(asdict(stats))
        return
    console.print(
        f"[green]Done[/green] in {stats.seconds}s: {stats.files_added} added, "
        f"{stats.files_updated} updated, {stats.files_unchanged} unchanged, "
        f"{stats.files_deleted} deleted, {stats.files_failed} failed; "
        f"{stats.chunks_written} chunks written, {stats.edges_resolved} call edges resolved."
    )
    for error in stats.errors[:10]:
        console.print(f"[red]  {escape(error)}[/red]")


@app.command()
def status(as_json: JsonOption = False) -> None:
    """List indexed repositories with their status and counts."""

    from codeqa.db import repositories as repo_dao
    from codeqa.db.session import session_scope

    with session_scope() as session:
        rows = repo_dao.list_repositories(session)
        data = [
            {
                "name": r.name,
                "status": r.status,
                "files": n_files,
                "chunks": n_chunks,
                "chunker": r.chunker,
                "embedding_model": r.embedding_model,
                "collection": r.collection_name,
                "commit": r.commit_sha[:10],
                "last_indexed_at": r.last_indexed_at,
            }
            for r, n_files, n_chunks in rows
        ]
    if as_json:
        print_json(data)
        return
    table = Table(title="Repositories")
    columns = ("name", "status", "files", "chunks", "chunker", "embedding_model", "commit")
    for column in columns:
        table.add_column(column)
    for d in data:
        table.add_row(*(str(d[column]) for column in columns))
    console.print(table)


@app.command()
def job(job_id: str) -> None:
    """Show one indexing job."""

    from codeqa.db import repositories as repo_dao
    from codeqa.db.session import session_scope

    with session_scope() as session:
        found = repo_dao.get_job(session, uuid.UUID(job_id))
        if found is None:
            raise NotFoundError(f"job {job_id} not found")
        print_json({c.name: getattr(found, c.name) for c in found.__table__.columns})
```


Register the new module in `cli/main.py` (full file):

<!-- file: src/codeqa/cli/main.py -->
**`src/codeqa/cli/main.py`**

```python
from rich.markup import escape

# Importing a command module registers its commands on `app` (decorators run on import).
from codeqa.cli import (  # noqa: F401
    chunk,
    index,
)
from codeqa.cli.app import app, console
from codeqa.errors import CodeQAError


def main() -> None:
    try:
        app()
    except CodeQAError as exc:
        console.print(f"[red]Error:[/red] {escape(exc.message)}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
```


### Step 2.10: Test setup (`tests/conftest.py`) and tests

**What:** shared pytest fixtures. `conftest.py` is loaded automatically by pytest before
any test.

**Why it looks like this:**

- **Environment first:** the `os.environ[...]` lines run before any `codeqa` import, so
  `get_settings()` sees the fake embedder, embedded Qdrant and fake LLM. That is why the
  imports below them carry `# noqa: E402` ("import not at top of file").
- **`session_factory`:** SQLite in memory by default (`StaticPool` keeps the single
  in-memory database alive across connections), or Postgres when `TEST_DATABASE_URL` is
  set (CI). Tables are created from the models and dropped after each test, so tests
  never see each other's data.
- **`qdrant`:** a fresh in-memory Qdrant per test.
- **`indexer`:** a real `IndexingService` wired to fakes. It is the same class as in
  production, only its dependencies differ.

Create empty `__init__.py` files so `from tests.conftest import SAMPLE_REPO` works:

```bash
touch tests/__init__.py tests/unit/__init__.py tests/integration/__init__.py
```

<!-- file: tests/__init__.py -->
**`tests/__init__.py`** (empty file: create it with no content)


<!-- file: tests/unit/__init__.py -->
**`tests/unit/__init__.py`** (empty file: create it with no content)


<!-- file: tests/integration/__init__.py -->
**`tests/integration/__init__.py`** (empty file: create it with no content)


<!-- file: tests/conftest.py -->
**`tests/conftest.py`**

```python
import os

# Test configuration must be set before anything reads settings.
os.environ["APP_ENV"] = "test"
os.environ["EMBEDDING_MODEL"] = "hashing-64"
os.environ["SPARSE_MODEL"] = "hashing"
os.environ["QDRANT_LOCATION"] = ":memory:"
os.environ["LLM_PROVIDER"] = "fake"
os.environ["RERANKER_ENABLED"] = "false"

from collections.abc import Iterator  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from qdrant_client import QdrantClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from codeqa.ingest.pipeline import IndexingService  # noqa: E402
from codeqa.models import Base  # noqa: E402
from codeqa.retrieval.embedder import HashingEmbedder  # noqa: E402
from codeqa.retrieval.sparse import HashingSparseEncoder  # noqa: E402
from codeqa.retrieval.store import QdrantStore  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_REPO = FIXTURES / "sample_repo"


@pytest.fixture
def session_factory() -> Iterator[sessionmaker[Session]]:
    """SQLite in memory by default; set TEST_DATABASE_URL to run against Postgres (CI)."""

    url = os.environ.get("TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    if url.startswith("sqlite"):
        engine = create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    else:
        engine = create_engine(url)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def qdrant() -> QdrantClient:
    return QdrantClient(location=":memory:")


@pytest.fixture
def embedder() -> HashingEmbedder:
    return HashingEmbedder(64)


@pytest.fixture
def indexer(
    session_factory: sessionmaker[Session], qdrant: QdrantClient, embedder: HashingEmbedder
) -> IndexingService:
    return IndexingService(
        store_for=lambda name: QdrantStore(qdrant, name),
        embedder_for=lambda _model: embedder,
        sparse=HashingSparseEncoder(),
        session_factory=session_factory,
    )
```


<!-- file: tests/unit/test_sparse.py -->
**`tests/unit/test_sparse.py`**

```python
import pytest

from codeqa.retrieval.sparse import expand_identifiers, split_identifier


@pytest.mark.parametrize(
    ("identifier", "parts"),
    [
        ("getUserByID", ["get", "user", "by", "id"]),
        ("HTTPServerError", ["http", "server", "error"]),
        ("parse_json_v2", ["parse", "json", "v", "2"]),
        ("__init__", ["init"]),
        ("URL", ["url"]),
        ("x", ["x"]),
    ],
)
def test_split_identifier(identifier: str, parts: list[str]) -> None:
    assert split_identifier(identifier) == parts


def test_expand_keeps_whole_identifier_and_adds_parts() -> None:
    assert expand_identifiers("getUserByID(x)") == "getuserbyid get user by id x"
    assert expand_identifiers("parse_json_v2") == "parse_json_v2 parse json v 2"


def test_query_and_document_share_tokens() -> None:
    doc = set(expand_identifiers("def get_user_by_id(user_id): ...").split())
    query = set(expand_identifiers("where do we get user by id").split())
    assert {"get", "user", "by", "id"} <= doc & query
```


The integration test proves the Definition of Done: counts match, re-indexing duplicates
nothing, only changed files are touched, deleted files disappear, edges resolve, and one
bad file does not stop the job.

<!-- file: tests/integration/test_indexing_pipeline.py -->
**`tests/integration/test_indexing_pipeline.py`**

```python
import shutil
from pathlib import Path

from qdrant_client import QdrantClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from codeqa.ingest.pipeline import IndexingService
from codeqa.models import Chunk, IndexJob, SymbolEdge
from codeqa.retrieval.store import QdrantStore
from tests.conftest import SAMPLE_REPO

COLLECTION = "test_chunks"


def _copy_repo(tmp_path: Path) -> Path:
    target = tmp_path / "shop_repo"
    shutil.copytree(SAMPLE_REPO, target)
    return target


def _pg_chunks(factory: sessionmaker[Session]) -> int:
    with factory() as session:
        return int(session.scalar(select(func.count(Chunk.id))) or 0)


def test_index_is_consistent_and_idempotent(
    tmp_path: Path,
    indexer: IndexingService,
    session_factory: sessionmaker[Session],
    qdrant: QdrantClient,
) -> None:
    repo = _copy_repo(tmp_path)

    first = indexer.index(str(repo), "shop", collection=COLLECTION)
    store = QdrantStore(qdrant, COLLECTION)
    assert first.files_added == 5
    assert first.chunks_written > 10
    assert _pg_chunks(session_factory) == store.count(str(first.repository_id))

    second = indexer.index(str(repo), "shop", collection=COLLECTION)
    assert second.repository_id == first.repository_id
    assert second.files_unchanged == 5 and second.chunks_written == 0
    assert _pg_chunks(session_factory) == first.chunks_written  # no duplicates

    with session_factory() as session:
        job = session.get(IndexJob, second.job_id)
        assert job is not None and job.status == "completed"


def test_incremental_reindex_touches_only_changed_files(
    tmp_path: Path,
    indexer: IndexingService,
    session_factory: sessionmaker[Session],
    qdrant: QdrantClient,
) -> None:
    repo = _copy_repo(tmp_path)
    first = indexer.index(str(repo), "shop", collection=COLLECTION)

    users = repo / "shop" / "users.py"
    users.write_text(users.read_text() + "\n\ndef delete_user(user_id: int) -> None:\n    pass\n")
    (repo / "shop" / "retry.py").unlink()

    second = indexer.index(str(repo), "shop", collection=COLLECTION)
    assert (second.files_updated, second.files_deleted, second.files_unchanged) == (1, 1, 3)

    store = QdrantStore(qdrant, COLLECTION)
    assert _pg_chunks(session_factory) == store.count(str(first.repository_id))
    with session_factory() as session:
        names = set(session.scalars(select(Chunk.qualified_name)))
    assert "delete_user" in names
    assert "RetryPolicy._backoff" not in names


def test_call_edges_are_resolved(
    tmp_path: Path, indexer: IndexingService, session_factory: sessionmaker[Session]
) -> None:
    stats = indexer.index(str(_copy_repo(tmp_path)), "shop", collection=COLLECTION)
    assert stats.edges_resolved > 0

    with session_factory() as session:
        edge = session.scalar(
            select(SymbolEdge).where(
                SymbolEdge.source_name == "Client.current_user",
                SymbolEdge.target_name == "get_user_by_id",
            )
        )
        assert edge is not None and edge.target_chunk_id is not None
        target = session.get(Chunk, edge.target_chunk_id)
        assert target is not None and target.qualified_name == "get_user_by_id"


def test_one_bad_file_does_not_kill_the_job(
    tmp_path: Path, indexer: IndexingService, monkeypatch: object
) -> None:
    repo = _copy_repo(tmp_path)
    original = IndexingService._prepare_file

    def flaky(self: IndexingService, item, *args, **kwargs):  # type: ignore[no-untyped-def]
        if item.relative_path.endswith("users.py"):
            raise RuntimeError("boom")
        return original(self, item, *args, **kwargs)

    monkeypatch.setattr(IndexingService, "_prepare_file", flaky)  # type: ignore[attr-defined]
    stats = indexer.index(str(repo), "shop", collection=COLLECTION)
    assert stats.files_failed == 1 and stats.files_added == 4
```


**Check:** `make lint && make test` (32 passed).

### Step 2.11: Index a real repository

```bash
make up && make migrate
uv run codeqa index /tmp/httpx -n httpx                  # first run downloads the model
uv run codeqa status
uv run codeqa index /tmp/httpx -n httpx                  # again: everything "unchanged"
```

Verify Postgres and Qdrant agree (the pipeline also checks this and warns on mismatch):

```bash
uv run codeqa status                                   # "chunks" column = Postgres count
docker compose exec postgres psql -U codeqa -c "select id, name from repositories;"
# copy the id of httpx, then count its points in Qdrant:
curl -s -X POST localhost:6333/collections/codeqa_chunks/points/count \
     -H 'content-type: application/json' \
     -d '{"exact": true, "filter": {"must": [{"key": "repo_id", "match": {"value": "<paste-id>"}}]}}'
```

**Tip for slow laptops:** `EMBEDDING_MODEL=BAAI/bge-small-en-v1.5` is about 10 times
smaller than jina-code. Use it to iterate, then index with jina for real numbers. A
different model needs its own collection (different vector size):
`--embedding-model BAAI/bge-small-en-v1.5 --collection codeqa_bge`.

### Phase 2: Definition of Done

- Indexing a mid-size repo completes on your laptop.
- Postgres chunk count equals Qdrant point count.
- Running the same command again writes 0 chunks and reports all files unchanged.
- Note the throughput (chunks per second) for your README.


---

## Phase 3. Hybrid retrieval

**Goal:** one `SearchService.search()` that every interface (CLI, API, graph, evaluation)
calls, with `dense`, `sparse` and `hybrid` modes, filters and per-stage timings.

```bash
git checkout -b phase-3-retrieval
```

### 3.0 Reciprocal Rank Fusion, on a whiteboard

You have two ranked lists for one query:

| Rank | Dense | Sparse |
|---|---|---|
| 1 | A | B |
| 2 | B | C |
| 3 | C | D |

RRF gives each document `sum over lists of 1 / (k + rank)`, with `k = 60`:

- A: `1/61` = 0.01639 (only in dense)
- B: `1/62 + 1/61` = 0.03252
- C: `1/63 + 1/62` = 0.03200
- D: `1/63` = 0.01587

Fused order: **B, C, A, D**. Documents that *both* methods rank well rise to the top.

**Why ranks instead of scores?** BM25 scores go from 0 to unbounded; cosine similarity is
between -1 and 1. Adding them needs normalisation and a tuned weight. RRF ignores the raw
scores, so there is nothing to tune. **Why k = 60?** It comes from the original paper
(Cormack et al., 2009). A large `k` flattens the difference between rank 1 and rank 2, so
one list cannot dominate just by being confident.

This is a common interview question. Be able to do the example above by hand.

### Step 3.1: RRF tests (`tests/unit/test_fusion.py`)

You wrote `fusion.py` in Step 2.4. Now test it against the formula:

<!-- file: tests/unit/test_fusion.py -->
**`tests/unit/test_fusion.py`**

```python
import pytest

from codeqa.retrieval.fusion import reciprocal_rank_fusion


def test_item_ranked_high_in_both_lists_wins() -> None:
    fused = reciprocal_rank_fusion([["a", "b", "c"], ["b", "a", "d"]])
    assert [item for item, _ in fused][:2] in (["a", "b"], ["b", "a"])
    assert fused[-1][0] in {"c", "d"}


def test_scores_match_the_formula() -> None:
    fused = dict(reciprocal_rank_fusion([["a", "b"], ["b"]], k=60))
    assert fused["a"] == pytest.approx(1 / 61)
    assert fused["b"] == pytest.approx(1 / 62 + 1 / 61)


def test_item_in_one_list_only_still_appears() -> None:
    fused = dict(reciprocal_rank_fusion([["a"], ["z"]]))
    assert set(fused) == {"a", "z"}
```


### Step 3.2: The search service (`retrieval/search.py`)

**What:** `SearchService.search(query, target, mode, top_k, filters)` returns typed
`SearchResult` objects plus timings.

**Why:**

- **`RepoSearchTarget`:** search needs the repo id, *its* collection and *its* embedding
  model (from the `repositories` row). Querying with a different model than the one used
  for indexing returns nonsense, silently.
- **Typed results:** `SearchResult` has everything a caller needs (path, lines, name,
  content, score, rank). `location` and `label` are small helpers for display.
- **Timings per stage:** "embedding the query takes 250 ms, the vector search 10 ms" is
  exactly the kind of observation that belongs in your README and tells you what to
  optimise.
- **Constructor injection** (`store_for`, `embedder_for`, `sparse`): the same class runs
  with fakes in tests and with real models in production.

<!-- file: src/codeqa/retrieval/search.py -->
**`src/codeqa/retrieval/search.py`**

```python
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from codeqa.retrieval.embedder import Embedder
from codeqa.retrieval.sparse import SparseEncoder
from codeqa.retrieval.store import QdrantStore, SearchFilters, SearchMode, StoreHit


@dataclass
class RepoSearchTarget:
    """What SearchService needs to know about a repo: where its vectors live and how
    they were made. Comes from the `repositories` row."""

    repo_id: str
    collection_name: str
    embedding_model: str


@dataclass
class SearchResult:
    chunk_id: str
    rank: int
    score: float
    path: str
    language: str
    kind: str
    symbol_name: str | None
    qualified_name: str | None
    signature: str | None
    docstring: str | None
    start_line: int
    end_line: int
    content: str

    @property
    def location(self) -> str:
        return f"{self.path}:L{self.start_line}-L{self.end_line}"

    @property
    def label(self) -> str:
        return self.qualified_name or self.kind


@dataclass
class SearchResponse:
    results: list[SearchResult]
    timings_ms: dict[str, float] = field(default_factory=dict)


def _to_result(hit: StoreHit, rank: int) -> SearchResult:
    p = hit.payload
    return SearchResult(
        chunk_id=hit.id,
        rank=rank,
        score=hit.score,
        path=str(p.get("path", "")),
        language=str(p.get("language", "")),
        kind=str(p.get("kind", "")),
        symbol_name=p.get("symbol_name"),
        qualified_name=p.get("qualified_name"),
        signature=p.get("signature"),
        docstring=p.get("docstring"),
        start_line=int(p.get("start_line", 0)),
        end_line=int(p.get("end_line", 0)),
        content=str(p.get("content", "")),
    )


class SearchService:
    """The single retrieval entry point used by the CLI, the API, the graph and eval."""

    def __init__(
        self,
        store_for: Callable[[str], QdrantStore],
        embedder_for: Callable[[str], Embedder],
        sparse: SparseEncoder,
    ) -> None:
        self._store_for = store_for
        self._embedder_for = embedder_for
        self._sparse = sparse

    def search(
        self,
        query: str,
        target: RepoSearchTarget,
        mode: SearchMode = "hybrid",
        top_k: int = 10,
        filters: SearchFilters | None = None,
    ) -> SearchResponse:
        timings: dict[str, float] = {}

        started = time.perf_counter()
        dense = None
        if mode != "sparse":
            dense = self._embedder_for(target.embedding_model).embed_query(query)
        timings["embed_dense_ms"] = _ms(started)

        started = time.perf_counter()
        sparse = self._sparse.embed_query(query) if mode != "dense" else None
        timings["embed_sparse_ms"] = _ms(started)

        started = time.perf_counter()
        hits = self._store_for(target.collection_name).search(
            repo_id=target.repo_id,
            mode=mode,
            dense=dense,
            sparse=sparse,
            limit=top_k,
            filters=filters,
        )
        timings["vector_search_ms"] = _ms(started)

        results = [_to_result(hit, rank) for rank, hit in enumerate(hits, start=1)]
        return SearchResponse(results=results, timings_ms=timings)


def _ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)
```


### Step 3.3: Looking up a repository (`services/repos.py`)

**What:** `load_repo_context(name)` turns a repo name into a `RepoContext` (id, collection,
model, URL, commit, local path).

**Why a separate module:** the CLI, the API, the graph and the evaluation all need this
lookup. Keeping it out of the graph code means Phases 3 to 5 can use it before the graph
exists. It refuses a repo that has never finished indexing, with a clear message.

<!-- file: src/codeqa/services/__init__.py -->
**`src/codeqa/services/__init__.py`** (empty file: create it with no content)


<!-- file: src/codeqa/services/repos.py -->
**`src/codeqa/services/repos.py`**

```python
from dataclasses import dataclass

from codeqa.db import repositories as repo_dao
from codeqa.db.session import SessionFactory, session_scope
from codeqa.errors import NotFoundError
from codeqa.retrieval.search import RepoSearchTarget


@dataclass(frozen=True)
class RepoContext:
    """An indexed repo, as the rest of the app needs it (from the `repositories` row)."""

    id: str
    name: str
    collection_name: str
    embedding_model: str
    source_url: str | None
    commit_sha: str
    local_path: str = ""

    def search_target(self) -> RepoSearchTarget:
        return RepoSearchTarget(self.id, self.collection_name, self.embedding_model)


def load_repo_context(session_factory: SessionFactory | None, name: str) -> RepoContext:
    with session_scope(session_factory) as session:
        repo = repo_dao.get_repository_by_name(session, name)
        if repo is None:
            raise NotFoundError(f"repository {name!r} is not indexed")
        if repo.status != "ready" and repo.last_indexed_at is None:
            raise NotFoundError(f"repository {name!r} is still being indexed ({repo.status})")
        return RepoContext(
            id=str(repo.id),
            name=repo.name,
            collection_name=repo.collection_name,
            embedding_model=repo.embedding_model,
            source_url=repo.source_url,
            commit_sha=repo.commit_sha,
            local_path=repo.local_path,
        )
```


### Step 3.4: Add the search service to the container

Replace `container.py` with this version (adds `get_search_service`):

<!-- file: src/codeqa/container.py -->
**`src/codeqa/container.py`**

```python
"""Builds the real services once per process. CLI and API both get services from here.

Tests do not use this module: they construct services with fakes directly.
"""

from functools import lru_cache

from codeqa.config import get_settings
from codeqa.ingest.pipeline import IndexingService
from codeqa.retrieval.embedder import get_embedder
from codeqa.retrieval.search import SearchService
from codeqa.retrieval.sparse import get_sparse_encoder
from codeqa.retrieval.store import QdrantStore, get_qdrant_client


def store_for(collection: str) -> QdrantStore:
    return QdrantStore(get_qdrant_client(), collection)


@lru_cache
def get_indexing_service() -> IndexingService:
    return IndexingService(
        store_for=store_for,
        embedder_for=get_embedder,
        sparse=get_sparse_encoder(get_settings().sparse_model),
    )


@lru_cache
def get_search_service() -> SearchService:
    return SearchService(
        store_for=store_for,
        embedder_for=get_embedder,
        sparse=get_sparse_encoder(get_settings().sparse_model),
    )
```


### Step 3.5: CLI `search` (`cli/search.py`)

**What:** `codeqa search "query" -r httpx --mode sparse --top-k 5`, printing
`path:Lstart-Lend (name) score` and a syntax-highlighted snippet.

**Why:** you need to *see* retrieval before you measure it. This command is also a great
live demo in an interview: run the same query in `dense` and `sparse` mode and show the
difference.

<!-- file: src/codeqa/cli/search.py -->
**`src/codeqa/cli/search.py`**

```python
from dataclasses import asdict
from typing import Annotated, cast, get_args

import typer
from rich.markup import escape
from rich.syntax import Syntax

from codeqa.cli.app import JsonOption, RepoOption, app, console, print_json


@app.command()
def search(
    query: str,
    repo: RepoOption,
    mode: Annotated[str, typer.Option(help="dense | sparse | hybrid | hybrid_local")] = "hybrid",
    top_k: int = 10,
    path_prefix: str | None = None,
    kind: str | None = None,
    as_json: JsonOption = False,
) -> None:
    """Raw retrieval, no LLM. Great for seeing hybrid search work."""

    from codeqa.container import get_search_service
    from codeqa.retrieval.store import SearchFilters, SearchMode
    from codeqa.services.repos import load_repo_context

    if mode not in get_args(SearchMode):
        raise typer.BadParameter(f"mode must be one of {get_args(SearchMode)}")
    target = load_repo_context(None, repo).search_target()
    response = get_search_service().search(
        query,
        target,
        mode=cast(SearchMode, mode),
        top_k=top_k,
        filters=SearchFilters(path_prefix=path_prefix, kind=kind),
    )

    if as_json:
        print_json({"results": [asdict(r) for r in response.results], **response.timings_ms})
        return
    for r in response.results:
        console.rule(f"#{r.rank}  {r.location}  ({escape(r.label)})  score={r.score:.4f}")
        snippet = "\n".join(r.content.split("\n")[:15])
        console.print(Syntax(snippet, "python", line_numbers=True, start_line=r.start_line))
    console.print(f"[dim]timings: {response.timings_ms}[/dim]")
```


<!-- file: src/codeqa/cli/main.py -->
**`src/codeqa/cli/main.py`**

```python
from rich.markup import escape

# Importing a command module registers its commands on `app` (decorators run on import).
from codeqa.cli import (  # noqa: F401
    chunk,
    index,
    search,
)
from codeqa.cli.app import app, console
from codeqa.errors import CodeQAError


def main() -> None:
    try:
        app()
    except CodeQAError as exc:
        console.print(f"[red]Error:[/red] {escape(exc.message)}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
```


### Step 3.6: Tests

Add a `search_service` fixture. Replace `tests/conftest.py` with the complete version:

<!-- file: tests/conftest.py -->
**`tests/conftest.py`**

```python
import os

# Test configuration must be set before anything reads settings.
os.environ["APP_ENV"] = "test"
os.environ["EMBEDDING_MODEL"] = "hashing-64"
os.environ["SPARSE_MODEL"] = "hashing"
os.environ["QDRANT_LOCATION"] = ":memory:"
os.environ["LLM_PROVIDER"] = "fake"
os.environ["RERANKER_ENABLED"] = "false"

from collections.abc import Iterator  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402
from qdrant_client import QdrantClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from codeqa.ingest.pipeline import IndexingService  # noqa: E402
from codeqa.models import Base  # noqa: E402
from codeqa.retrieval.embedder import HashingEmbedder  # noqa: E402
from codeqa.retrieval.search import SearchService  # noqa: E402
from codeqa.retrieval.sparse import HashingSparseEncoder  # noqa: E402
from codeqa.retrieval.store import QdrantStore  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLE_REPO = FIXTURES / "sample_repo"


@pytest.fixture
def session_factory() -> Iterator[sessionmaker[Session]]:
    """SQLite in memory by default; set TEST_DATABASE_URL to run against Postgres (CI)."""

    url = os.environ.get("TEST_DATABASE_URL", "sqlite+pysqlite:///:memory:")
    if url.startswith("sqlite"):
        engine = create_engine(url, connect_args={"check_same_thread": False}, poolclass=StaticPool)
    else:
        engine = create_engine(url)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def qdrant() -> QdrantClient:
    return QdrantClient(location=":memory:")


@pytest.fixture
def embedder() -> HashingEmbedder:
    return HashingEmbedder(64)


@pytest.fixture
def indexer(
    session_factory: sessionmaker[Session], qdrant: QdrantClient, embedder: HashingEmbedder
) -> IndexingService:
    return IndexingService(
        store_for=lambda name: QdrantStore(qdrant, name),
        embedder_for=lambda _model: embedder,
        sparse=HashingSparseEncoder(),
        session_factory=session_factory,
    )


@pytest.fixture
def search_service(qdrant: QdrantClient, embedder: HashingEmbedder) -> SearchService:
    return SearchService(
        store_for=lambda name: QdrantStore(qdrant, name),
        embedder_for=lambda _model: embedder,
        sparse=HashingSparseEncoder(),
    )
```


<!-- file: tests/integration/test_search.py -->
**`tests/integration/test_search.py`**

```python
import shutil
from pathlib import Path

import pytest

from codeqa.ingest.pipeline import IndexingService
from codeqa.retrieval.search import RepoSearchTarget, SearchService
from codeqa.retrieval.store import SearchFilters
from tests.conftest import SAMPLE_REPO


@pytest.fixture
def target(tmp_path: Path, indexer: IndexingService) -> RepoSearchTarget:
    repo = tmp_path / "shop_repo"
    shutil.copytree(SAMPLE_REPO, repo)
    stats = indexer.index(str(repo), "shop", collection="search_test")
    return RepoSearchTarget(str(stats.repository_id), "search_test", "hashing-64")


@pytest.mark.parametrize("mode", ["dense", "sparse", "hybrid", "hybrid_local"])
def test_every_mode_finds_the_exact_identifier(
    mode: str, target: RepoSearchTarget, search_service: SearchService
) -> None:
    response = search_service.search("get_user_by_id", target, mode=mode, top_k=5)  # type: ignore[arg-type]
    names = [r.qualified_name for r in response.results]
    assert "get_user_by_id" in names
    assert response.results[0].rank == 1
    assert "vector_search_ms" in response.timings_ms


def test_path_prefix_filter(target: RepoSearchTarget, search_service: SearchService) -> None:
    response = search_service.search(
        "retry", target, mode="hybrid", top_k=20, filters=SearchFilters(path_prefix="shop")
    )
    assert response.results
    assert all(r.path.startswith("shop/") for r in response.results)


def test_native_and_local_rrf_broadly_agree(
    target: RepoSearchTarget, search_service: SearchService
) -> None:
    native = search_service.search("exponential backoff", target, mode="hybrid", top_k=5)
    local = search_service.search("exponential backoff", target, mode="hybrid_local", top_k=5)
    overlap = {r.chunk_id for r in native.results} & {r.chunk_id for r in local.results}
    assert len(overlap) >= 3
```


**Check:** `make lint && make test` (41 passed).

### Step 3.7: The ten-query experiment

With your real repo indexed, write ten queries in `docs/retrieval-observations.md`: five
*exact identifier* queries (a real function or class name from the repo) and five
*conceptual* ones ("how are redirects followed?"). Run each in three modes:

```bash
for mode in dense sparse hybrid; do
  uv run codeqa search "how are redirects followed" -r httpx --mode $mode --top-k 5
done
```

Record for each query and mode: is the right chunk in the top 5, and at what rank? The
expected pattern: exact identifiers win on `sparse`, conceptual questions win on `dense`,
and `hybrid` is rarely the worst. Also compare `hybrid` with `hybrid_local`: the top
results should broadly agree (small differences come from tie-breaking). Write down what
you actually see, including surprises. It becomes README material.

### Phase 3: Definition of Done

- All three modes run end to end from the CLI.
- The ten-query table is written, with your observation in one or two sentences.


---

## Phase 4. Evaluation harness

**Goal:** one command regenerates a table of Recall@5, Recall@10, MRR, nDCG@10 and latency
for every retrieval configuration, broken down by question type, recorded with the git SHA.

**Why before the LLM:** most RAG failures are retrieval failures. If the right chunk is not
retrieved, no prompt can save the answer. This phase is the difference between "I made a
chatbot" and "I engineered a retrieval system", and it is the strongest hiring signal in
the project.

```bash
git checkout -b phase-4-evaluation
```

### 4.0 The metrics, explained with one example

A question has ground truth `{T1, T2}` (two relevant symbols). The retriever returns, in
order: `X, T1, Y, T2, Z`.

| Metric | Formula | Here | What it tells you |
|---|---|---|---|
| **Recall@k** | share of ground-truth items found in the top k | @2: 1/2 = 0.5, @5: 2/2 = 1.0 | "Did we find it at all?" The LLM only sees the top ~6, so Recall@5 matters most. |
| **Reciprocal rank (RR)** | 1 / rank of the first relevant result | first relevant at rank 2: 0.5 | "How soon does something useful appear?" **MRR** is the mean over questions. |
| **nDCG@10** | sum of `1/log2(rank+1)` for relevant hits, divided by the best possible sum | (1/log2 3 + 1/log2 5) / (1/log2 2 + 1/log2 3) = (0.631 + 0.431) / 1.631 = **0.651** | Rewards putting *all* relevant results near the top. |

**When does a result "match" the ground truth?** `metrics.matches()`:

1. Same file path, and
2. either the chunk's `qualified_name` equals the ground-truth symbol, **or** the chunk
   covers at least 50% of the symbol's lines.

Rule 2 is what makes the comparison fair to fixed-size chunks, which have no names.
Class skeletons are excluded from rule 2, because their line range spans the whole class
but they do not contain method bodies. And the ground-truth line range is read from the
**source file** with the AST chunker, not from your index, so every configuration is
judged by the same ruler.

### Step 4.1: Pick two repositories

- **Dev repo:** a mid-size, readable open-source Python project (roughly 5k to 30k lines),
  for example `httpx`, `rich`, `click` or `requests`. You tune everything on it.
- **Held-out repo:** a *different* project of similar size. Clone it, record the commit, and
  **do not look at its results until Phase 9.** Its whole value is that you never tuned on
  it.

Pin both by commit SHA:

```bash
git -C /tmp/httpx rev-parse HEAD      # write this into the dataset file below
```

### Step 4.2: Write the golden dataset by hand

**What:** `eval/datasets/dev_questions.yaml`, about 40 questions with hand-verified answers.

**Why by hand:** if an LLM writes your ground truth, you are measuring agreement with that
LLM. Reading the code and labelling 40 questions takes one long evening. It is the most
valuable evening of the project.

**Format** (the loader in Step 4.3 validates it):

```yaml
name: httpx-dev
repo: httpx                                     # name used with `codeqa index -n httpx`
source: https://github.com/encode/httpx
commit: <sha from Step 4.1>                     # ground truth is only valid for this commit
questions:
  - id: q001
    question: "Where is the retry backoff interval calculated?"
    route: code_search                          # code_search | dependency | overview | out_of_scope
    type: conceptual                            # conceptual | exact_identifier | dependency | overview | unanswerable
    difficulty: medium                          # easy | medium | hard
    relevant:                                   # ground truth: file + qualified symbol name
      - path: "httpx/_transports/default.py"
        symbol: "HTTPTransport.handle_request"
  - id: q030
    question: "Which Kubernetes operator deploys this library?"
    route: code_search
    type: unanswerable                          # correct behaviour is to abstain
```

(The `path`/`symbol` above only illustrate the format. Use real ones from your repo.)

**Target mix:** ~15 conceptual, ~10 exact-identifier, ~8 dependency ("who calls X?"),
~5 overview ("how is the repo structured?"), ~2 unanswerable.

**How to label, step by step:**

1. Read the repo's README and main package, and write questions a new contributor would
   ask.
2. For each question, find the answer in the code yourself. `grep -rn "def backoff" .` and
   your own `codeqa search` are fine for *finding candidates*; **you** decide what is
   correct by reading the code.
3. Get the exact qualified name: `uv run codeqa chunk path/to/file.py --limit 100` lists
   every chunk's `qualified_name` (`Class.method` for methods).
4. For overview questions, use `path: README.md` with no `symbol` (the whole file counts).
5. For dependency questions, list the *callers* as the relevant items.
6. Write two questions whose answer is **not** in the repo (`type: unanswerable`).

This small dataset is used by the tests; it shows the format working end to end:

<!-- file: tests/fixtures/eval/shop_questions.yaml -->
**`tests/fixtures/eval/shop_questions.yaml`**

```yaml
name: shop-dev
repo: shop
questions:
  - id: q001
    question: "Where is the retry backoff interval calculated?"
    route: code_search
    type: conceptual
    relevant:
      - path: shop/retry.py
        symbol: RetryPolicy._backoff
  - id: q002
    question: "get_user_by_id"
    route: code_search
    type: exact_identifier
    relevant:
      - path: shop/users.py
        symbol: get_user_by_id
  - id: q003
    question: "Who calls get_user_by_id?"
    route: dependency
    type: dependency
    relevant:
      - path: shop/client.py
        symbol: Client.current_user
  - id: q004
    question: "How is this repo organized?"
    route: overview
    type: overview
    relevant:
      - path: README.md
  - id: q005
    question: "Which Kubernetes operator deploys the frontend?"
    route: code_search
    type: unanswerable
```


### Step 4.3: Dataset model (`evaluation/dataset.py`)

**What:** Pydantic models for the YAML file.

**Why:** a typo like `type: conceptul` fails immediately with a clear message, instead of
silently producing a wrong breakdown table.

<!-- file: src/codeqa/evaluation/__init__.py -->
**`src/codeqa/evaluation/__init__.py`** (empty file: create it with no content)


<!-- file: src/codeqa/evaluation/dataset.py -->
**`src/codeqa/evaluation/dataset.py`**

```python
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

QuestionType = Literal["conceptual", "exact_identifier", "dependency", "overview", "unanswerable"]


class RelevantItem(BaseModel):
    path: str  # repo-relative, forward slashes
    symbol: str | None = None  # qualified name, e.g. "RetryPolicy._backoff"; None = whole file


class EvalQuestion(BaseModel):
    id: str
    question: str
    route: Literal["code_search", "dependency", "overview", "out_of_scope"]
    type: QuestionType
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    relevant: list[RelevantItem] = Field(default_factory=list)

    @property
    def answerable(self) -> bool:
        return self.type != "unanswerable"


class EvalDataset(BaseModel):
    name: str
    repo: str  # the repo name used with `codeqa index --repo-name`
    source: str | None = None
    commit: str | None = None  # pin it: ground truth is only valid for one commit
    questions: list[EvalQuestion]


def load_dataset(path: Path) -> EvalDataset:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return EvalDataset.model_validate(data)
```


### Step 4.4: Metrics (`evaluation/metrics.py`)

**What:** the matching rule and the three ranking metrics from 4.0.

**Why each detail:**

- `truth_spans` merges the parts of a split function back into one span, so "found part 2
  of the function" still counts as finding the function.
- `ndcg_at_k` credits each ground-truth item **once**: ten chunks of the same function in
  the top 10 should not score like ten different relevant results.
- `_symbol_spans` is cached per file: forty questions often point at the same few files.

<!-- file: src/codeqa/evaluation/metrics.py -->
**`src/codeqa/evaluation/metrics.py`**

```python
import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from codeqa.evaluation.dataset import RelevantItem
from codeqa.ingest.chunkers.python_ast import PythonASTChunker
from codeqa.retrieval.search import SearchResult

MIN_COVERAGE = 0.5  # a chunk "contains" a symbol if it covers >= 50% of its lines


@dataclass(frozen=True)
class Span:
    path: str
    start: int
    end: int
    name: str | None


@lru_cache(maxsize=512)
def _symbol_spans(repo_root: Path, path: str) -> tuple[Span, ...]:
    file = repo_root / path
    if not file.exists() or file.suffix != ".py":
        return ()
    chunks = PythonASTChunker().chunk_file(file, file.read_bytes())
    return tuple(
        Span(path, c.start_line, c.end_line, c.qualified_name)
        for c in chunks
        if c.qualified_name and c.kind != "module"
    )


def truth_spans(repo_root: Path, item: RelevantItem) -> list[Span]:
    """Where the ground-truth symbol lives, read from the source file itself.

    Using the file (not our index) keeps the ground truth independent of the chunker
    under test, so fixed-size chunks and AST chunks are judged by the same yardstick.
    """

    if item.symbol is None:
        return [Span(item.path, 0, 0, None)]
    spans = [s for s in _symbol_spans(repo_root, item.path) if s.name == item.symbol]
    # Split functions have several parts: merge them back into one span.
    if spans:
        return [
            Span(item.path, min(s.start for s in spans), max(s.end for s in spans), item.symbol)
        ]
    return []


def matches(result: SearchResult, spans: list[Span]) -> bool:
    for span in spans:
        if result.path != span.path:
            continue
        if span.name is None or result.qualified_name == span.name:
            return True
        # Class skeletons cover the whole class range but not the method bodies.
        if result.kind == "class_skeleton":
            continue
        overlap = min(result.end_line, span.end) - max(result.start_line, span.start) + 1
        if overlap / (span.end - span.start + 1) >= MIN_COVERAGE:
            return True
    return False


def recall_at_k(results: list[SearchResult], truth: list[list[Span]], k: int) -> float:
    """Share of ground-truth items found anywhere in the top k."""

    if not truth:
        return 0.0
    top = results[:k]
    found = sum(any(matches(r, spans) for r in top) for spans in truth)
    return found / len(truth)


def reciprocal_rank(results: list[SearchResult], truth: list[list[Span]]) -> float:
    """1 / rank of the first relevant result (0 if none). MRR = mean over questions."""

    for rank, result in enumerate(results, start=1):
        if any(matches(result, spans) for spans in truth):
            return 1.0 / rank
    return 0.0


def ndcg_at_k(results: list[SearchResult], truth: list[list[Span]], k: int) -> float:
    """Binary-relevance nDCG: rewards relevant results near the top.

    Each ground-truth item can be credited once, so ten chunks of the same function do
    not inflate the score.
    """

    credited: set[int] = set()
    dcg = 0.0
    for rank, result in enumerate(results[:k], start=1):
        for index, spans in enumerate(truth):
            if index not in credited and matches(result, spans):
                credited.add(index)
                dcg += 1.0 / math.log2(rank + 1)
                break
    ideal = sum(1.0 / math.log2(rank + 1) for rank in range(1, min(len(truth), k) + 1))
    return dcg / ideal if ideal else 0.0


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(pct / 100 * (len(ordered) - 1))))]
```


### Step 4.5: The reranker module (`retrieval/reranker.py`)

**What:** a `Reranker` protocol, a fastembed cross-encoder, and a word-overlap fake.

**Why now:** the ablation has a "reranker on/off" dimension, so the evaluation code needs
this type. Phase 5 is where you study whether it helps. The model loads lazily (only when
`get_reranker()` is first called), so it costs nothing while it is switched off.

**Bi-encoder vs cross-encoder:** the embedder encodes query and document *separately* and
compares vectors (fast, can be pre-computed for every chunk). A cross-encoder reads the
query and one document *together* and outputs one relevance score (much sharper, but it
must run once per candidate at query time). So: retrieve ~30 with the fast method,
rerank those 30 with the slow one.

<!-- file: src/codeqa/retrieval/reranker.py -->
**`src/codeqa/retrieval/reranker.py`**

```python
from collections.abc import Sequence
from functools import lru_cache
from typing import Protocol

from codeqa.config import get_settings


class Reranker(Protocol):
    def score(self, query: str, documents: Sequence[str]) -> list[float]: ...


class FastEmbedReranker:
    """Cross-encoder: reads (query, document) *together*, so it is slower but sharper
    than the bi-encoder used for retrieval. Only ever run it on ~30 candidates."""

    def __init__(self, model_name: str) -> None:
        from fastembed.rerank.cross_encoder import TextCrossEncoder

        self._model = TextCrossEncoder(model_name, cache_dir=str(get_settings().model_cache_dir))

    def score(self, query: str, documents: Sequence[str]) -> list[float]:
        return [float(s) for s in self._model.rerank(query, list(documents))]


class OverlapReranker:
    """Test double: score = share of query words that appear in the document."""

    def score(self, query: str, documents: Sequence[str]) -> list[float]:
        words = {w for w in query.lower().split() if len(w) > 2}
        if not words:
            return [0.0 for _ in documents]
        return [sum(w in d.lower() for w in words) / len(words) for d in documents]


@lru_cache(maxsize=1)
def get_reranker() -> Reranker:
    return FastEmbedReranker(get_settings().reranker_model)
```


### Step 4.6: The retrieval evaluation (`evaluation/retrieval.py`)

**What:** run one configuration over every answerable question; summarise overall and by
question type; render a Markdown table.

**Why per-type breakdown:** averages hide the effect you built. The typical finding is
"hybrid barely changes the overall average but helps exact-identifier questions a lot".
You can only see that per type.

<!-- file: src/codeqa/evaluation/retrieval.py -->
**`src/codeqa/evaluation/retrieval.py`**

```python
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from codeqa.evaluation.dataset import EvalDataset
from codeqa.evaluation.metrics import (
    ndcg_at_k,
    percentile,
    recall_at_k,
    reciprocal_rank,
    truth_spans,
)
from codeqa.retrieval.reranker import Reranker
from codeqa.retrieval.search import SearchResult, SearchService
from codeqa.retrieval.store import SearchMode
from codeqa.services.repos import RepoContext

RERANK_CANDIDATES = 30


class RetrievalConfig(BaseModel):
    name: str
    repo: str  # indexed repo name (e.g. "httpx-fixed" for the fixed-chunk variant)
    mode: SearchMode = "hybrid"
    rerank: bool = False


def load_configs(path: Path) -> tuple[str, list[RetrievalConfig]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data["dataset"], [RetrievalConfig.model_validate(c) for c in data["configs"]]


@dataclass
class QuestionScore:
    id: str
    type: str
    recall_at_5: float
    recall_at_10: float
    rr: float
    ndcg_at_10: float
    latency_ms: float
    top_results: list[str]


def _retrieve(
    question: str,
    repo: RepoContext,
    config: RetrievalConfig,
    search: SearchService,
    reranker: Reranker | None,
) -> list[SearchResult]:
    k = RERANK_CANDIDATES if config.rerank else 10
    results = search.search(question, repo.search_target(), mode=config.mode, top_k=k).results
    if config.rerank and reranker is not None and results:
        scores = reranker.score(question, [r.content[:2000] for r in results])
        order = sorted(range(len(results)), key=lambda i: scores[i], reverse=True)
        results = [results[i] for i in order][:10]
    return results


def evaluate_config(
    config: RetrievalConfig,
    dataset: EvalDataset,
    repo: RepoContext,
    repo_root: Path,
    search: SearchService,
    reranker: Reranker | None = None,
) -> tuple[dict[str, Any], list[QuestionScore]]:
    scores: list[QuestionScore] = []
    for q in dataset.questions:
        if not q.answerable or not q.relevant:
            continue  # unanswerable questions are scored in the generation eval
        truth = [truth_spans(repo_root, item) for item in q.relevant]
        started = time.perf_counter()
        results = _retrieve(q.question, repo, config, search, reranker)
        latency = (time.perf_counter() - started) * 1000
        scores.append(
            QuestionScore(
                id=q.id,
                type=q.type,
                recall_at_5=recall_at_k(results, truth, 5),
                recall_at_10=recall_at_k(results, truth, 10),
                rr=reciprocal_rank(results, truth),
                ndcg_at_10=ndcg_at_k(results, truth, 10),
                latency_ms=round(latency, 1),
                top_results=[f"{r.path}:{r.label}" for r in results[:5]],
            )
        )
    return summarize(scores), scores


def summarize(scores: list[QuestionScore]) -> dict[str, Any]:
    def mean(values: list[float]) -> float:
        return round(sum(values) / len(values), 3) if values else 0.0

    def block(items: list[QuestionScore]) -> dict[str, float]:
        return {
            "n": len(items),
            "recall@5": mean([s.recall_at_5 for s in items]),
            "recall@10": mean([s.recall_at_10 for s in items]),
            "mrr": mean([s.rr for s in items]),
            "ndcg@10": mean([s.ndcg_at_10 for s in items]),
            "p50_ms": round(percentile([s.latency_ms for s in items], 50), 1),
        }

    by_type: dict[str, list[QuestionScore]] = defaultdict(list)
    for s in scores:
        by_type[s.type].append(s)
    return {"overall": block(scores), "by_type": {t: block(v) for t, v in sorted(by_type.items())}}


def to_markdown(results: dict[str, dict[str, Any]]) -> str:
    lines = [
        "| Config | Recall@5 | Recall@10 | MRR | nDCG@10 | p50 latency (ms) |",
        "|---|---|---|---|---|---|",
    ]
    for name, metrics in results.items():
        o = metrics["overall"]
        lines.append(
            f"| {name} | {o['recall@5']} | {o['recall@10']} | {o['mrr']} | "
            f"{o['ndcg@10']} | {o['p50_ms']} |"
        )
    types = sorted({t for m in results.values() for t in m["by_type"]})
    lines += ["", "**Recall@5 by question type**", ""]
    lines.append("| Config | " + " | ".join(types) + " |")
    lines.append("|---" * (len(types) + 1) + "|")
    for name, metrics in results.items():
        cells = [str(metrics["by_type"].get(t, {}).get("recall@5", "-")) for t in types]
        lines.append(f"| {name} | " + " | ".join(cells) + " |")
    lines.append("")
    return "\n".join(lines)


def rows_for_json(per_config: dict[str, list[QuestionScore]]) -> list[dict[str, Any]]:
    return [{"config": name, **asdict(s)} for name, scores in per_config.items() for s in scores]
```


### Step 4.7: Saving results (`evaluation/runs.py`)

**What:** write JSON (every per-question score) and Markdown (the table) into
`eval/results/`, and a row into `eval_runs` with the current git SHA.

**Why:** reproducibility. Six months from now, "Recall@5 = 0.82" means nothing unless you
know which code, config and dataset produced it. The JSON goes into git; the `-latest.md`
file is what you paste into the README.

<!-- file: src/codeqa/evaluation/runs.py -->
**`src/codeqa/evaluation/runs.py`**

```python
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from codeqa.db import repositories as repo_dao
from codeqa.db.session import SessionFactory, session_scope
from codeqa.models import EvalRun


def git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True, timeout=10
        )
        return out.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return ""


def save_results(
    out_dir: Path,
    kind: str,
    dataset: str,
    config: dict[str, Any],
    metrics: dict[str, Any],
    rows: list[dict[str, Any]],
    markdown: str,
    session_factory: SessionFactory | None = None,
    record: bool = True,
) -> Path:
    """Write JSON + Markdown to eval/results/ and one row to `eval_runs`.

    JSON is committed to git; the DB row makes every number traceable to a git SHA.
    """

    sha = git_sha()
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    out_dir.mkdir(parents=True, exist_ok=True)
    base = out_dir / f"{kind}-{Path(dataset).stem}-{stamp}"
    payload = {
        "kind": kind,
        "dataset": dataset,
        "git_sha": sha,
        "config": config,
        "metrics": metrics,
        "rows": rows,
    }
    base.with_suffix(".json").write_text(json.dumps(payload, indent=2, default=str))
    base.with_suffix(".md").write_text(markdown)
    (out_dir / f"{kind}-latest.md").write_text(markdown)
    if record:
        with session_scope(session_factory) as session:
            repo_dao.add_eval_run(
                session,
                EvalRun(kind=kind, config=config, dataset=dataset, metrics=metrics, git_sha=sha),
            )
    return base.with_suffix(".json")
```


### Step 4.8: The ablation config (`eval/configs/retrieval.yaml`)

**What:** the list of rows in your results table.

**Why a file:** the experiment is data, not code. Adding a row is a one-line change, and the
config is saved with every run.

<!-- file: eval/configs/retrieval.yaml -->
**`eval/configs/retrieval.yaml`**

```yaml
# Each config = one row of the ablation table.
# Index the variants first (see the guide, Phase 4):
#   codeqa index <repo> -n httpx
#   codeqa index <repo> -n httpx-fixed --chunker fixed --collection codeqa_fixed
#   codeqa index <repo> -n httpx-bge --embedding-model BAAI/bge-small-en-v1.5 --collection codeqa_bge
dataset: eval/datasets/dev_questions.yaml
configs:
  - {name: "fixed + dense",            repo: httpx-fixed, mode: dense}
  - {name: "AST + dense",              repo: httpx,       mode: dense}
  - {name: "AST + sparse (BM25)",      repo: httpx,       mode: sparse}
  - {name: "AST + hybrid (RRF)",       repo: httpx,       mode: hybrid}
  - {name: "AST + hybrid, bge-small",  repo: httpx-bge,   mode: hybrid}
  - {name: "AST + hybrid + reranker",  repo: httpx,       mode: hybrid, rerank: true}
```


### Step 4.9: CLI `eval retrieval` (`cli/eval_retrieval.py`)

<!-- file: src/codeqa/cli/eval_retrieval.py -->
**`src/codeqa/cli/eval_retrieval.py`**

```python
from pathlib import Path
from typing import Annotated, Any

import typer

from codeqa.cli.app import console, eval_app


@eval_app.command("retrieval")
def eval_retrieval(
    config: Annotated[Path, typer.Option(help="YAML listing dataset + configs")] = Path(
        "eval/configs/retrieval.yaml"
    ),
    out: Path = Path("eval/results"),
    record: Annotated[bool, typer.Option(help="Also write a row to eval_runs")] = True,
) -> None:
    """Run every retrieval config on the dataset and write a results table."""

    from codeqa.container import get_search_service
    from codeqa.evaluation import retrieval
    from codeqa.evaluation.dataset import load_dataset
    from codeqa.evaluation.runs import save_results
    from codeqa.retrieval.reranker import get_reranker
    from codeqa.services.repos import load_repo_context

    dataset_path, configs = retrieval.load_configs(config)
    dataset = load_dataset(Path(dataset_path))
    repo_root = Path(load_repo_context(None, dataset.repo).local_path)
    search_service = get_search_service()

    results: dict[str, dict[str, Any]] = {}
    per_question = {}
    for cfg in configs:
        console.print(f"[bold]{cfg.name}[/bold] ...")
        reranker = get_reranker() if cfg.rerank else None
        repo = load_repo_context(None, cfg.repo)
        metrics, scores = retrieval.evaluate_config(
            cfg, dataset, repo, repo_root, search_service, reranker
        )
        results[cfg.name] = metrics
        per_question[cfg.name] = scores

    markdown = retrieval.to_markdown(results)
    path = save_results(
        out,
        "retrieval",
        dataset_path,
        {"configs": [c.model_dump() for c in configs]},
        {"results": results},
        retrieval.rows_for_json(per_question),
        markdown,
        record=record,
    )
    console.print(markdown)
    console.print(f"[dim]saved {path}[/dim]")
```


<!-- file: src/codeqa/cli/main.py -->
**`src/codeqa/cli/main.py`**

```python
from rich.markup import escape

# Importing a command module registers its commands on `app` (decorators run on import).
from codeqa.cli import (  # noqa: F401
    chunk,
    eval_retrieval,
    index,
    search,
)
from codeqa.cli.app import app, console
from codeqa.errors import CodeQAError


def main() -> None:
    try:
        app()
    except CodeQAError as exc:
        console.print(f"[red]Error:[/red] {escape(exc.message)}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
```


### Step 4.10: Tests

<!-- file: tests/unit/test_eval_metrics.py -->
**`tests/unit/test_eval_metrics.py`**

```python
from codeqa.evaluation.dataset import RelevantItem, load_dataset
from codeqa.evaluation.metrics import (
    Span,
    matches,
    ndcg_at_k,
    recall_at_k,
    reciprocal_rank,
    truth_spans,
)
from codeqa.retrieval.search import SearchResult
from tests.conftest import FIXTURES, SAMPLE_REPO


def _result(
    path: str, name: str | None, start: int, end: int, kind: str = "function"
) -> SearchResult:
    return SearchResult("id", 1, 1.0, path, "python", kind, name, name, None, None, start, end, "")


def test_truth_spans_come_from_the_source_file() -> None:
    spans = truth_spans(
        SAMPLE_REPO, RelevantItem(path="shop/retry.py", symbol="RetryPolicy._backoff")
    )
    assert spans == [Span("shop/retry.py", 14, 16, "RetryPolicy._backoff")]


def test_match_by_name_or_by_line_coverage() -> None:
    truth = [Span("a.py", 10, 20, "f")]
    assert matches(_result("a.py", "f", 10, 20), truth)
    assert matches(_result("a.py", None, 1, 60, kind="fixed"), truth)  # window covers f
    assert not matches(_result("a.py", None, 18, 70, kind="fixed"), truth)  # only 3 of 11 lines
    assert not matches(_result("a.py", "A", 1, 100, kind="class_skeleton"), truth)
    assert not matches(_result("b.py", "f", 10, 20), truth)


def test_ranking_metrics() -> None:
    truth = [[Span("a.py", 1, 5, "f")], [Span("b.py", 1, 5, "g")]]
    results = [_result("x.py", "x", 1, 5), _result("a.py", "f", 1, 5), _result("b.py", "g", 1, 5)]
    assert recall_at_k(results, truth, 2) == 0.5
    assert recall_at_k(results, truth, 3) == 1.0
    assert reciprocal_rank(results, truth) == 0.5
    assert 0 < ndcg_at_k(results, truth, 10) < 1


def test_dataset_loads() -> None:
    dataset = load_dataset(FIXTURES / "eval" / "shop_questions.yaml")
    assert len(dataset.questions) == 5 and not dataset.questions[-1].answerable
```


**Check:** `make lint && make test` (45 passed).

### Step 4.11: Run the ablation

Index the variants the config refers to (each is the same code, indexed differently):

```bash
uv run codeqa index /tmp/httpx -n httpx
uv run codeqa index /tmp/httpx -n httpx-fixed --chunker fixed --collection codeqa_fixed
uv run codeqa index /tmp/httpx -n httpx-bge \
    --embedding-model BAAI/bge-small-en-v1.5 --collection codeqa_bge
make eval-retrieval
```

(`--collection` matters: `httpx-fixed` uses the same model as `httpx` and could share a
collection, but a separate one keeps the variants cleanly apart; `httpx-bge` *must* use
another collection because its vectors have 384 dimensions instead of 768.)

The output is a table like this (shape only; your numbers will differ):

```
| Config | Recall@5 | Recall@10 | MRR | nDCG@10 | p50 latency (ms) |
|---|---|---|---|---|---|
| fixed + dense | ... |
| AST + dense | ... |
| AST + sparse (BM25) | ... |
| AST + hybrid (RRF) | ... |
| AST + hybrid, bge-small | ... |
| AST + hybrid + reranker | ... |

**Recall@5 by question type**
| Config | conceptual | dependency | exact_identifier | overview |
```

Commit the JSON and Markdown in `eval/results/`.

### Phase 4: Definition of Done

- `make eval-retrieval` regenerates every number from scratch.
- The results table is committed.
- You can say in one sentence which configuration wins and by how much, **per question
  type**. Write that sentence down.


---

## Phase 5. Reranking and the evidence gate

**Goal:** decide, with data, (a) whether the reranker improves ranking and (b) which
reranker score means "the evidence is good enough to answer".

```bash
git checkout -b phase-5-reranking
```

### 5.0 What the evidence gate is

Before generating, the graph asks: "is the best retrieved chunk actually relevant?" If
not, it rewrites the query once, and if that also fails it answers
"I couldn't find this in the indexed code." instead of letting the LLM guess. That is how
you control hallucination at the *retrieval* stage.

The cross-encoder's top score is a good "relevance" signal. But what number is "good
enough"? That depends on the model and on your data, so you **calibrate** it: compute the
top score for every question, then pick the threshold that best separates answerable from
unanswerable questions.

**Two error types, and why you report both:**

- *False abstention:* an answerable question refused (users get "not found" for things
  that exist). Annoying.
- *Missed abstention:* an unanswerable question answered (the model makes something up).
  Dangerous.

A threshold trades one for the other. Report the trade-off; do not hide it.

### Step 5.1: Re-run the ablation with the reranker

The config from Step 4.8 already has the row `AST + hybrid + reranker`. Look at two
columns: Recall@5/MRR (does it rank better?) and p50 latency (what does it cost?). On CPU,
reranking 30 candidates typically adds a few hundred milliseconds.

**Be ready for "it did not help".** Many small rerankers are trained on web search pairs,
not code. When this guide was verified on the small test repo, the reranker *lowered*
Recall@5 on the conceptual question and added about 300 ms. On your repo it may help or
not: the point is that you *measure* it. "It didn't help on code, here is the table" is a
better interview story than keeping it because it sounds impressive.

### Step 5.2: Threshold calibration (`evaluation/calibrate.py`)

**What:** `top_scores()` gets the best reranker score for each question; `sweep()` tries
every observed score as a threshold and reports accuracy, false-abstention and
correct-abstention rates.

**Why every observed score:** the best threshold always sits at one of the observed
values (between them nothing changes), so trying each one is exact and cheap.

<!-- file: src/codeqa/evaluation/calibrate.py -->
**`src/codeqa/evaluation/calibrate.py`**

```python
from typing import Any

from codeqa.evaluation.dataset import EvalDataset
from codeqa.retrieval.reranker import Reranker
from codeqa.retrieval.search import SearchService
from codeqa.services.repos import RepoContext


def top_scores(
    dataset: EvalDataset, repo: RepoContext, search: SearchService, reranker: Reranker
) -> list[tuple[bool, float]]:
    """(answerable?, best reranker score) for every question."""

    pairs: list[tuple[bool, float]] = []
    for q in dataset.questions:
        results = search.search(q.question, repo.search_target(), mode="hybrid", top_k=30).results
        best = max(reranker.score(q.question, [r.content[:2000] for r in results]), default=0.0)
        pairs.append((q.answerable, best))
    return pairs


def sweep(pairs: list[tuple[bool, float]]) -> tuple[float, list[dict[str, Any]]]:
    """Try every observed score as the threshold; pick the one with the best accuracy.

    Accuracy = answer the answerable (score >= t) + abstain on the unanswerable (score < t).
    We also report the false-abstention rate: answerable questions we would refuse.
    """

    table: list[dict[str, Any]] = []
    answerable = [s for ok, s in pairs if ok]
    unanswerable = [s for ok, s in pairs if not ok]
    for t in sorted({s for _, s in pairs}):
        correct = sum(s >= t for s in answerable) + sum(s < t for s in unanswerable)
        table.append(
            {
                "threshold": round(t, 4),
                "accuracy": round(correct / len(pairs), 3),
                "false_abstention": round(sum(s < t for s in answerable) / len(answerable), 3)
                if answerable
                else 0.0,
                "correct_abstention": round(sum(s < t for s in unanswerable) / len(unanswerable), 3)
                if unanswerable
                else 0.0,
            }
        )
    best = max(table, key=lambda row: (row["accuracy"], -row["false_abstention"]))
    return float(best["threshold"]), table
```


### Step 5.3: CLI `eval calibrate` (`cli/eval_calibrate.py`)

<!-- file: src/codeqa/cli/eval_calibrate.py -->
**`src/codeqa/cli/eval_calibrate.py`**

```python
from pathlib import Path

from rich.table import Table

from codeqa.cli.app import console, eval_app


@eval_app.command("calibrate")
def eval_calibrate(dataset: Path = Path("eval/datasets/dev_questions.yaml")) -> None:
    """Find the reranker score threshold that best separates answerable questions."""

    from codeqa.container import get_search_service
    from codeqa.evaluation.calibrate import sweep, top_scores
    from codeqa.evaluation.dataset import load_dataset
    from codeqa.retrieval.reranker import get_reranker
    from codeqa.services.repos import load_repo_context

    data = load_dataset(dataset)
    repo = load_repo_context(None, data.repo)
    pairs = top_scores(data, repo, get_search_service(), get_reranker())
    best, table = sweep(pairs)
    view = Table(title="Evidence threshold sweep")
    for column in ("threshold", "accuracy", "false_abstention", "correct_abstention"):
        view.add_column(column)
    for row in table:
        view.add_row(*(str(row[c]) for c in row))
    console.print(view)
    console.print(f"Best threshold: [bold]{best}[/bold]  ->  set EVIDENCE_THRESHOLD={best}")
```


<!-- file: src/codeqa/cli/main.py -->
**`src/codeqa/cli/main.py`**

```python
from rich.markup import escape

# Importing a command module registers its commands on `app` (decorators run on import).
from codeqa.cli import (  # noqa: F401
    chunk,
    eval_calibrate,
    eval_retrieval,
    index,
    search,
)
from codeqa.cli.app import app, console
from codeqa.errors import CodeQAError


def main() -> None:
    try:
        app()
    except CodeQAError as exc:
        console.print(f"[red]Error:[/red] {escape(exc.message)}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
```


### Step 5.4: Test

<!-- file: tests/unit/test_calibrate.py -->
**`tests/unit/test_calibrate.py`**

```python
from codeqa.evaluation.calibrate import sweep


def test_threshold_sweep_separates_classes() -> None:
    best, table = sweep([(True, 0.9), (True, 0.7), (False, 0.2), (False, 0.1)])
    assert 0.2 < best <= 0.7
    assert max(row["accuracy"] for row in table) == 1.0
```


**Check:** `make lint && make test` (46 passed).

### Step 5.5: Calibrate and decide

```bash
make calibrate
```

You get a table like:

```
threshold  accuracy  false_abstention  correct_abstention
...
Best threshold: 0.42  ->  set EVIDENCE_THRESHOLD=0.42
```

With only ~2 unanswerable questions in 40, the estimate is rough. Add a few more
unanswerable questions if the choice looks fragile. Then decide and write it down:

1. Put the chosen values in `.env`:
   ```bash
   RERANKER_ENABLED=true            # or false, if the data says so
   EVIDENCE_THRESHOLD=<best>
   ```
2. Write `docs/adr/0004-reranker-and-gate.md` (template in Phase 9): the before/after table
   with latency, the threshold sweep, the false-abstention rate, and your decision.

**Note on the gate when the reranker is off:** the graph then only checks "did retrieval
return anything?", and relies on the answer prompt's instruction to say "not found". It
is a weaker gate. If you disable reranking for *ranking* but still want a strong gate, you
could keep the cross-encoder for gating only; that is a good "next step" to mention.

### Phase 5: Definition of Done

A documented decision (keep or drop the reranker, which threshold), backed by a
before/after table that includes latency.


---

## Phase 6. LangGraph pipeline and grounded generation

**Goal:** `codeqa ask "question" -r httpx` streams an answer whose every claim carries a
`[n]` citation that maps to `file:Lstart-Lend` (and a GitHub permalink), abstains when the
evidence is weak, and logs everything to `query_logs`.

```bash
git checkout -b phase-6-graph
```

### 6.0 Concepts you need first

**Why a graph and not a function?** Straight-line RAG (retrieve, then generate) is one
function. Ours has **branches** (three routes plus refusal) and a **bounded loop** (rewrite
the query once). LangGraph makes that control flow explicit, drawable and testable.

**How LangGraph works, in five facts:**

1. **State** is a `TypedDict`. Every node receives the whole state.
2. A **node** is a function `state -> dict`. The returned dict is a *partial update*,
   merged into the state.
3. **Edges** connect nodes. A **conditional edge** calls a function on the state that
   returns the name of the next node.
4. A **reducer** (`Annotated[type, fn]`) says how to merge a key that several nodes
   update. We use one to *add up* timings, because `retrieve_hybrid` can run twice.
5. `graph.stream(..., stream_mode=["custom", "values"])` yields both the state after each
   node (`values`) and anything a node writes with `get_stream_writer()` (`custom`). That
   is how answer tokens reach the CLI while the graph is still running.

**Design rule:** nodes are plain methods on a `QueryNodes` class. None of them imports
LangGraph (except the tiny token emitter), so every node can be unit-tested by calling it
with a dict.

**Grounding and citations.** The LLM sees numbered sources `[1] path L10-L40 (Client.send)`
and must cite `[n]` after each claim. We then *validate* the markers: numbers that do not
exist are removed, and an answer with no valid citation is flagged `grounded = false`. We
parse markers with a regex instead of asking for JSON, because small models break JSON
often but write `[2]` reliably.

### Step 6.1: Graph state (`graph/state.py`)

**What:** the state `TypedDict`, the `Source` and `Citation` shapes, and the timings
reducer.

**Why `total=False`:** nodes fill the state step by step; not every key exists at every
moment. Nodes read optional keys with `state.get(...)`.

<!-- file: src/codeqa/graph/__init__.py -->
**`src/codeqa/graph/__init__.py`** (empty file: create it with no content)


<!-- file: src/codeqa/graph/state.py -->
**`src/codeqa/graph/state.py`**

```python
from typing import Annotated, Literal, TypedDict

from codeqa.retrieval.search import SearchResult

# Re-exported (the "as" form tells mypy it is intentional): graph code imports it from here.
from codeqa.services.repos import RepoContext as RepoContext

Route = Literal["code_search", "dependency", "overview", "out_of_scope"]
GateDecision = Literal["sufficient", "retry", "abstain"]


class Source(TypedDict):
    """One numbered block of context shown to the LLM as `[n]`."""

    index: int
    chunk_id: str | None
    path: str
    start_line: int
    end_line: int
    label: str
    content: str
    score: float | None


class Citation(TypedDict):
    index: int
    chunk_id: str | None
    path: str
    start_line: int
    end_line: int
    label: str
    permalink: str | None


def merge_timings(left: dict[str, float], right: dict[str, float]) -> dict[str, float]:
    """Reducer: add up per-stage times (a stage can run twice when we retry)."""

    merged = dict(left)
    for stage, ms in right.items():
        merged[stage] = round(merged.get(stage, 0.0) + ms, 2)
    return merged


class GraphState(TypedDict, total=False):
    # inputs
    question: str
    repo: RepoContext
    # routing and retrieval
    route: Route
    symbol: str | None
    queries: list[str]  # the question, then any rewrites
    candidates: list[SearchResult]
    context: list[Source]
    top_score: float | None
    gate: GateDecision
    retries: int
    # outputs
    answer: str
    citations: list[Citation]
    grounded: bool
    abstained: bool
    timings_ms: Annotated[dict[str, float], merge_timings]
```


### Step 6.2: Rule-based router (`graph/router.py`)

**What:** `route_question` (which path), `dependency_direction` (callers or callees), and
`extract_symbol` (which name the question is about).

**Why rules first:** deterministic, free, instant and unit-testable. You label the expected
`route` of every eval question, so you can *measure* the router (Step 6.12) and replace it
with an LLM router only if the numbers justify it. That is evaluation-driven development.

**How `extract_symbol` decides:** backticks win (`` `send()` ``), then anything that looks
like code (dotted `Client.send`, `snake_case`, `camelCase`, `PascalCase` with two humps),
then the word after "calls/uses/of/does".

<!-- file: src/codeqa/graph/router.py -->
**`src/codeqa/graph/router.py`**

```python
import re

from codeqa.graph.state import Route

CALLERS_PATTERNS = [
    r"\bwho (calls|uses)\b",
    r"\bwhat (calls|uses)\b",
    r"\bcallers? of\b",
    r"\b(called|used) by\b",
    r"\bwhere is .+ (called|used)\b",
    r"\busages? of\b",
    r"\bwhat depends on\b",
]
CALLEES_PATTERNS = [
    r"\bwhat does .+ call\b",
    r"\bcallees? of\b",
    r"\bwhat functions does .+ (call|use)\b",
    r"\bwhat does .+ depend on\b",
]
OVERVIEW_PATTERNS = [
    r"\b(structure|architecture|overview)\b",
    r"\bhow is (this|the) (repo|repository|project|codebase) (organi[sz]ed|laid out)\b",
    r"\b(main|key) (modules|components|packages)\b",
    r"\bwhat does (this|the) (repo|repository|project|codebase) do\b",
]
OUT_OF_SCOPE_PATTERNS = [
    r"^\s*(hi|hello|hey|thanks|thank you)\W*$",
    r"\b(weather|joke|poem|recipe|stock price)\b",
]

BACKTICKED = re.compile(r"`([^`]+)`")
CODE_LIKE = re.compile(
    r"\b("
    r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+"  # dotted: Client.send
    r"|[a-z]+_\w+"  # snake_case: get_user_by_id
    r"|[a-z]+[A-Z]\w*"  # camelCase: getUser
    r"|[A-Z]\w*[A-Z]\w*"  # PascalCase with 2+ humps: RetryPolicy
    r")\b"
)
AFTER_VERB = re.compile(r"\b(?:calls?|uses?|of|does)\s+([A-Za-z_][\w.]*)")
STOPWORDS = {"the", "this", "that", "a", "an", "it", "function", "method", "class"}


def _matches(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text) for p in patterns)


def route_question(question: str) -> Route:
    """Rule-based routing. Deterministic, free and unit-testable.

    Measure its accuracy on the eval set before replacing it with an LLM router.
    """

    text = question.lower().strip()
    if not text or _matches(OUT_OF_SCOPE_PATTERNS, text):
        return "out_of_scope"
    if _matches(CALLERS_PATTERNS, text) or _matches(CALLEES_PATTERNS, text):
        return "dependency"
    if _matches(OVERVIEW_PATTERNS, text):
        return "overview"
    return "code_search"


def dependency_direction(question: str) -> str:
    """ "callees" for "what does X call?", otherwise "callers" ("who calls X?")."""

    return "callees" if _matches(CALLEES_PATTERNS, question.lower()) else "callers"


def extract_symbol(question: str) -> str | None:
    """Best guess at the code symbol a question is about.

    Order: `backticks` > code-looking tokens (snake_case, camelCase, a.b) > word after a verb.
    """

    backticked = BACKTICKED.search(question)
    if backticked:
        return backticked.group(1).strip().removesuffix("()")
    code_like = CODE_LIKE.search(question)
    if code_like:
        return code_like.group(1)
    for match in AFTER_VERB.finditer(question):
        word = match.group(1).rstrip(".")
        if word.lower() not in STOPWORDS:
            return word
    return None
```


### Step 6.3: Context budget (`graph/context.py`)

**What:** number the best results `[1]..[n]` and keep them under a token budget.

**Why:** small models get *worse* with long contexts. The budget (`MAX_CONTEXT_TOKENS`,
~6,000) is split equally among sources; a long source is cut **from the middle**, which
keeps its signature and docstring (the head) and its return statements (the tail).

<!-- file: src/codeqa/graph/context.py -->
**`src/codeqa/graph/context.py`**

````python
from codeqa.graph.state import Source
from codeqa.retrieval.search import SearchResult

CHARS_PER_TOKEN = 4


def truncate_middle(text: str, max_chars: int, keep_head_lines: int = 6) -> str:
    """Cut from the middle, keeping the head (signature, docstring) and the tail."""

    if len(text) <= max_chars:
        return text
    lines = text.split("\n")
    head = "\n".join(lines[:keep_head_lines])
    budget = max(max_chars - len(head) - 40, 0)
    tail = text[-budget:] if budget else ""
    return f"{head}\n    # ... ({len(text) - len(head) - len(tail)} chars omitted) ...\n{tail}"


def sources_from_results(
    results: list[SearchResult], max_tokens: int, max_sources: int
) -> list[Source]:
    """Number the best results [1..n] while staying under a token budget.

    Small models get worse, not better, with long contexts. Every source gets an equal
    share of the budget; a source over its share is truncated from the middle.
    """

    selected = results[:max_sources]
    if not selected:
        return []
    per_source_chars = (max_tokens * CHARS_PER_TOKEN) // len(selected)
    return [
        Source(
            index=i,
            chunk_id=r.chunk_id,
            path=r.path,
            start_line=r.start_line,
            end_line=r.end_line,
            label=r.label,
            content=truncate_middle(r.content, per_source_chars),
            score=r.score,
        )
        for i, r in enumerate(selected, start=1)
    ]


def format_sources(sources: list[Source]) -> str:
    """Render the numbered blocks exactly as the LLM sees them."""

    blocks = []
    for s in sources:
        lines = f" L{s['start_line']}-L{s['end_line']}" if s["start_line"] else ""
        blocks.append(f"[{s['index']}] {s['path']}{lines} ({s['label']})\n```\n{s['content']}\n```")
    return "\n\n".join(blocks)
````


### Step 6.4: Citation validator (`graph/citations.py`)

**What:** keep valid `[n]` markers, drop invalid ones, build one citation per source used
(in order of first use), with a permalink.

**Why the regex accepts `[1, 4]`:** models often group citations. We normalise them to
`[1][4]`.

<!-- file: src/codeqa/graph/citations.py -->
**`src/codeqa/graph/citations.py`**

```python
import re

from codeqa.graph.state import Citation, RepoContext, Source
from codeqa.ingest.source import github_permalink

# Matches [3] and also grouped forms like [1, 4] or [2][5].
MARKER = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")
NOT_FOUND_PHRASES = ("couldn't find", "could not find", "not found in the", "no information")


def validate_citations(
    answer: str, sources: list[Source], repo: RepoContext
) -> tuple[str, list[Citation], bool]:
    """Keep only markers that point at a real source; build one citation per source used.

    Returns (cleaned_answer, citations, grounded). `grounded` is False when the answer
    cites nothing valid. Regex parsing is used instead of asking a small model for
    JSON: it is far more robust.
    """

    by_index = {s["index"]: s for s in sources}
    used: list[int] = []

    def keep_valid(match: re.Match[str]) -> str:
        numbers = [int(n) for n in re.split(r"\s*,\s*", match.group(1))]
        valid = [n for n in numbers if n in by_index]
        for n in valid:
            if n not in used:
                used.append(n)
        return "".join(f"[{n}]" for n in valid)

    cleaned = MARKER.sub(keep_valid, answer)
    citations = [
        Citation(
            index=n,
            chunk_id=by_index[n]["chunk_id"],
            path=by_index[n]["path"],
            start_line=by_index[n]["start_line"],
            end_line=by_index[n]["end_line"],
            label=by_index[n]["label"],
            permalink=github_permalink(
                repo.source_url,
                repo.commit_sha,
                by_index[n]["path"],
                by_index[n]["start_line"],
                by_index[n]["end_line"],
            )
            if by_index[n]["start_line"]
            else None,
        )
        for n in used
    ]
    return cleaned, citations, bool(citations)


def looks_like_abstention(answer: str) -> bool:
    lowered = answer.lower()
    return any(phrase in lowered for phrase in NOT_FOUND_PHRASES)
```


### Step 6.5: Versioned prompts (`graph/prompts/`)

**What:** prompts live in Markdown files, split into system and user parts by a line with
`---`.

**Why files, not strings in code:** a prompt change becomes a reviewable diff, and each
query log records `prompt_version`, so you can compare v1 and v2 answers later. To try a
new prompt, copy `answer_v1.md` to `answer_v2.md` and set `PROMPT_VERSION=v2`.

**Why the answer prompt says what it says:** use *only* the sources (grounding); cite after
every claim (traceability); prefer real identifiers (precise, searchable answers); reply
with an exact "not found" sentence (so abstention can be detected in code).

<!-- file: src/codeqa/graph/prompts/__init__.py -->
**`src/codeqa/graph/prompts/__init__.py`**

```python
from functools import lru_cache
from pathlib import Path

PROMPT_DIR = Path(__file__).parent
SEPARATOR = "\n---\n"


@lru_cache
def load_prompt(name: str, version: str = "v1") -> tuple[str, str]:
    """Load `{name}_{version}.md` and split it into (system, user_template).

    Prompts live in files, not inline strings, so each change is a reviewable diff and
    every query log records which version produced the answer.
    """

    text = (PROMPT_DIR / f"{name}_{version}.md").read_text(encoding="utf-8")
    system, _, user = text.partition(SEPARATOR)
    return system.strip(), user.strip()
```


<!-- file: src/codeqa/graph/prompts/answer_v1.md -->
**`src/codeqa/graph/prompts/answer_v1.md`**

```markdown
You are CodeQA, an assistant that answers questions about one code repository.

Rules:
1. Use ONLY the numbered sources below. Do not use outside knowledge about this code.
2. After every factual claim, cite the source it came from, like [2] or [1][3].
3. Prefer quoting real identifiers (`function_name`, `ClassName.method`) over paraphrasing.
4. If the sources do not contain the answer, reply exactly:
   "I couldn't find this in the indexed code."
5. Be concise: a short explanation, then details or a small code excerpt if useful.
---
Repository: {repo_name}
Question: {question}

Sources:
{sources}

Answer (with [n] citations):
```


<!-- file: src/codeqa/graph/prompts/rewrite_v1.md -->
**`src/codeqa/graph/prompts/rewrite_v1.md`**

```markdown
You rewrite questions about a code repository into better search queries.
Use the words a programmer would put in code: likely function, class and variable
names (snake_case and CamelCase), library names, and technical terms.
Reply with ONE line: the rewritten query. No explanation.
---
Original question: {question}

Rewritten search query:
```


> The prompt templates are filled with `str.format`. Code inside `{sources}` may contain
> `{` and `}`; that is fine, because `format` only interprets braces in the *template*,
> not in the values inserted into it.

### Step 6.6: LLM provider factory (`graph/llm.py`)

**What:** a tiny `LLM` protocol (`complete`, `stream`, `name`), an adapter for any LangChain
chat model, a `FakeLLM`, and `get_llm()` that builds Groq, Gemini or Ollama from config.

**Why:**

- The graph depends on our 3-method protocol, not on LangChain. Tests use `FakeLLM`; no
  network call ever happens in the test suite.
- **Timeout** on every provider, and **one retry** (`with_retry(stop_after_attempt=2)`)
  for transient failures such as a 429 or a timeout. Errors become `UpstreamError`, which
  the API returns as a 502 instead of a stack trace.
- Provider SDKs are imported inside `get_llm()`, so an unused provider is never loaded.
- `DEFAULT_MODELS` are starting points. **Hosted models get retired:** check the provider's
  model list and set `LLM_MODEL` if a default no longer exists.

<!-- file: src/codeqa/graph/llm.py -->
**`src/codeqa/graph/llm.py`**

```python
from collections.abc import Callable, Iterator
from typing import Any, Protocol

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from codeqa.config import Settings, get_settings
from codeqa.errors import InvalidInputError, UpstreamError

# Check each provider's model list before relying on these: hosted models get retired.
DEFAULT_MODELS = {
    "groq": "llama-3.3-70b-versatile",
    "gemini": "gemini-2.5-flash",
    "ollama": "qwen2.5-coder:7b",
    "fake": "fake",
}


class LLM(Protocol):
    """The only LLM surface the graph knows about. Easy to fake in tests."""

    @property
    def name(self) -> str: ...

    def complete(self, system: str, user: str) -> str: ...

    def stream(self, system: str, user: str) -> Iterator[str]: ...


def _content_to_text(content: Any) -> str:
    """LangChain content is a str, or a list of parts for some providers."""

    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            part if isinstance(part, str) else str(part.get("text", "")) for part in content
        )
    return str(content)


class LangChainLLM:
    """Adapter from any LangChain chat model to our small LLM protocol."""

    def __init__(self, model: BaseChatModel, name: str) -> None:
        self._model = model
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    def complete(self, system: str, user: str) -> str:
        messages = [SystemMessage(system), HumanMessage(user)]
        try:
            # One retry on transient failures (timeouts, 429s, 5xx).
            reply = self._model.with_retry(stop_after_attempt=2).invoke(messages)
        except Exception as exc:
            raise UpstreamError(f"LLM call failed: {exc}") from exc
        return _content_to_text(reply.content)

    def stream(self, system: str, user: str) -> Iterator[str]:
        messages = [SystemMessage(system), HumanMessage(user)]
        try:
            for chunk in self._model.stream(messages):
                text = _content_to_text(chunk.content)
                if text:
                    yield text
        except Exception as exc:
            raise UpstreamError(f"LLM stream failed: {exc}") from exc


class FakeLLM:
    """Deterministic LLM for tests and offline demos.

    By default it answers by citing source [1]; pass `responder` to script replies.
    """

    def __init__(self, responder: Callable[[str, str], str] | None = None) -> None:
        self._responder = responder or _default_fake_reply
        self.calls: list[tuple[str, str]] = []

    @property
    def name(self) -> str:
        return "fake"

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        return self._responder(system, user)

    def stream(self, system: str, user: str) -> Iterator[str]:
        for word in self.complete(system, user).split(" "):
            yield word + " "


def _default_fake_reply(system: str, user: str) -> str:
    if "Rewritten search query" in user:
        return user.split("Original question:", 1)[-1].split("\n", 1)[0].strip()
    if "[1]" not in user:
        return "I couldn't find this in the indexed code."
    return "Based on the code, see the first source [1]."


def get_llm(settings: Settings | None = None) -> LLM:
    """Build the configured provider. Imports are local so unused SDKs never load."""

    settings = settings or get_settings()
    provider = settings.llm_provider
    model = settings.llm_model or DEFAULT_MODELS[provider]
    timeout = settings.llm_timeout_s

    chat: BaseChatModel
    if provider == "fake":
        return FakeLLM()
    if provider == "groq":
        from langchain_groq import ChatGroq

        if settings.groq_api_key is None:
            raise InvalidInputError("GROQ_API_KEY is not set")
        chat = ChatGroq(
            model=model,
            api_key=settings.groq_api_key,
            temperature=settings.llm_temperature,
            timeout=timeout,
            max_retries=1,
        )
    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        if settings.google_api_key is None:
            raise InvalidInputError("GOOGLE_API_KEY is not set")
        chat = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=settings.google_api_key,
            temperature=settings.llm_temperature,
            timeout=timeout,
            max_retries=1,
        )
    else:
        from langchain_ollama import ChatOllama

        chat = ChatOllama(
            model=model,
            base_url=settings.ollama_base_url,
            temperature=settings.llm_temperature,
            client_kwargs={"timeout": timeout},
        )
    return LangChainLLM(chat, name=f"{provider}:{model}")
```


**Setting up a provider (pick one):**

- **Groq** (fast, free tier): create a key at `console.groq.com`, then in `.env`:
  `LLM_PROVIDER=groq` and `GROQ_API_KEY=...`.
- **Gemini** (free tier): create a key in Google AI Studio, then `LLM_PROVIDER=gemini` and
  `GOOGLE_API_KEY=...`.
- **Ollama** (fully local, offline): install Ollama, run `ollama pull qwen2.5-coder:7b`
  (or a 3-4B model on CPU only; check the Ollama library for current tags), then
  `LLM_PROVIDER=ollama` and `LLM_MODEL=<tag>`.

### Step 6.7: The nodes (`graph/nodes.py`)

**What:** every step of the pipeline, as a method on `QueryNodes`, plus the three edge
functions.

**Node by node:**

- `route_question`: sets `route`, `symbol`, `queries=[question]`, `retries=0`.
- `retrieve_hybrid`: hybrid search with the *latest* query (the rewrite, if any), top 30.
- `rerank_and_gate`: with a reranker, re-sort by cross-encoder score and compare the top
  score with `EVIDENCE_THRESHOLD`; without one, "sufficient" means "anything came back".
  Then decide `sufficient`, `retry` (if `retries < MAX_RETRIES`) or `abstain`, and build
  the numbered context. `dataclasses.replace` creates re-scored copies instead of mutating
  shared objects.
- `rewrite_query`: one LLM call that rephrases the question with code vocabulary;
  increments `retries`. **`MAX_RETRIES = 1`**: the loop is bounded on purpose, so cost and
  latency are bounded too.
- `lookup_dependencies`: SQL over `symbol_edges`. For "who calls X": the definition of X,
  its callers, and their callers (depth 2). For "what does X call": the callees and their
  callees. If no symbol is found or nothing comes back, it switches the route to
  `code_search` and the graph falls back to normal retrieval.
- `build_repo_map`: file list with top-level symbols per file, plus up to four README
  sections, size-capped. Source `[1]` is the map itself (no line numbers).
- `generate_answer`: fills the prompt, streams tokens (each one is also emitted to the
  graph's `custom` stream), returns the full answer.
- `validate_citations`: cleans markers, builds citations, sets `grounded` and `abstained`.
- `respond_not_found`: the fixed abstention answer, with no LLM call at all.

<!-- file: src/codeqa/graph/nodes.py -->
**`src/codeqa/graph/nodes.py`**

```python
"""Graph nodes. Each node is a plain method: state in, partial state update out.

No node knows about LangGraph, which keeps them testable with fakes and simple dicts.
"""

import uuid
from dataclasses import dataclass, replace
from typing import Any

from codeqa.config import Settings
from codeqa.db import repositories as repo_dao
from codeqa.db.session import SessionFactory, session_scope
from codeqa.graph.citations import looks_like_abstention, validate_citations
from codeqa.graph.context import format_sources, sources_from_results, truncate_middle
from codeqa.graph.llm import LLM
from codeqa.graph.prompts import load_prompt
from codeqa.graph.router import dependency_direction, extract_symbol, route_question
from codeqa.graph.state import GraphState, Source
from codeqa.models import Chunk
from codeqa.retrieval.reranker import Reranker
from codeqa.retrieval.search import SearchService

MAX_RETRIES = 1  # the corrective loop is bounded on purpose
NOT_FOUND_ANSWER = "I couldn't find this in the indexed code."
REPO_MAP_MAX_CHARS = 6000


@dataclass
class GraphDeps:
    search: SearchService
    llm: LLM
    settings: Settings
    reranker: Reranker | None = None
    session_factory: SessionFactory | None = None


def _emit_token(text: str) -> None:
    """Stream a token to whoever runs the graph with stream_mode="custom".

    Outside a running graph (e.g. unit tests calling a node directly) there is no
    stream to write to, so we skip silently.
    """

    try:
        from langgraph.config import get_stream_writer

        get_stream_writer()({"token": text})
    except RuntimeError:
        pass


class QueryNodes:
    def __init__(self, deps: GraphDeps) -> None:
        self.deps = deps

    # ------------------------------------------------------------------ routing

    def route_question(self, state: GraphState) -> dict[str, Any]:
        question = state["question"]
        return {
            "route": route_question(question),
            "symbol": extract_symbol(question),
            "queries": [question],
            "retries": 0,
        }

    # ---------------------------------------------------------- code_search path

    def retrieve_hybrid(self, state: GraphState) -> dict[str, Any]:
        repo = state["repo"]
        query = state.get("queries", [state["question"]])[-1]
        response = self.deps.search.search(
            query,
            repo.search_target(),
            mode="hybrid",
            top_k=self.deps.settings.retrieval_top_k,
        )
        return {"candidates": response.results}

    def rerank_and_gate(self, state: GraphState) -> dict[str, Any]:
        settings = self.deps.settings
        candidates = list(state.get("candidates", []))
        query = state.get("queries", [state["question"]])[-1]
        top_score: float | None = None

        if candidates and self.deps.reranker is not None:
            scores = self.deps.reranker.score(query, [c.content[:2000] for c in candidates])
            ranked = sorted(zip(scores, candidates, strict=True), key=lambda p: p[0], reverse=True)
            candidates = [
                replace(c, score=score, rank=rank)
                for rank, (score, c) in enumerate(ranked, start=1)
            ]
            top_score = ranked[0][0]
            sufficient = top_score >= settings.evidence_threshold
        else:
            # Without a reranker we only know "something came back"; the answer prompt
            # still tells the LLM to abstain when the sources do not contain the answer.
            sufficient = bool(candidates)

        if sufficient:
            gate = "sufficient"
        elif state.get("retries", 0) < MAX_RETRIES:
            gate = "retry"
        else:
            gate = "abstain"

        context = sources_from_results(
            candidates, settings.max_context_tokens, settings.final_context_k
        )
        return {"gate": gate, "context": context, "top_score": top_score}

    def rewrite_query(self, state: GraphState) -> dict[str, Any]:
        system, template = load_prompt("rewrite", self.deps.settings.prompt_version)
        rewritten = self.deps.llm.complete(system, template.format(question=state["question"]))
        rewritten = rewritten.strip().split("\n")[0].strip() or state["question"]
        return {
            "queries": [*state.get("queries", []), rewritten],
            "retries": state.get("retries", 0) + 1,
        }

    # ----------------------------------------------------------- dependency path

    def lookup_dependencies(self, state: GraphState) -> dict[str, Any]:
        """SQL over `symbol_edges`: who calls X (or what X calls), up to depth 2."""

        symbol = state.get("symbol")
        if not symbol:
            return {"context": [], "route": "code_search"}

        repo_id = uuid.UUID(state["repo"].id)
        direction = dependency_direction(state["question"])
        short_name = symbol.split(".")[-1]
        with session_scope(self.deps.session_factory) as session:
            targets = repo_dao.find_symbol_chunks(session, repo_id, symbol)
            related: list[tuple[str, Chunk]] = []
            if direction == "callers":
                level1 = repo_dao.callers_of(session, repo_id, [short_name])
                related += [("caller", c) for c in level1]
                names = sorted({c.symbol_name for c in level1 if c.symbol_name})
                level2 = repo_dao.callers_of(session, repo_id, names) if names else []
                related += [("caller of caller", c) for c in level2]
            else:
                level1 = repo_dao.callees_of(session, [c.id for c in targets])
                related += [("callee", c) for c in level1]
                level2 = repo_dao.callees_of(session, [c.id for c in level1]) if level1 else []
                related += [("callee of callee", c) for c in level2]

            chunks = [("definition", c) for c in targets] + related
            paths = repo_dao.paths_for_chunks(session, [c for _, c in chunks])

        if not chunks:
            return {"context": [], "route": "code_search"}  # fall back to search

        seen: set[uuid.UUID] = set()
        context: list[Source] = []
        budget = (self.deps.settings.max_context_tokens * 4) // max(len(chunks), 1)
        for relation, chunk in chunks:
            if chunk.id in seen or len(context) >= self.deps.settings.final_context_k * 2:
                continue
            seen.add(chunk.id)
            context.append(
                Source(
                    index=len(context) + 1,
                    chunk_id=str(chunk.id),
                    path=paths.get(chunk.file_id, "?"),
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    label=f"{chunk.qualified_name or chunk.kind}, {relation}",
                    content=truncate_middle(chunk.content, budget),
                    score=None,
                )
            )
        return {"context": context}

    # ------------------------------------------------------------- overview path

    def build_repo_map(self, state: GraphState) -> dict[str, Any]:
        """Directory tree + top-level symbols + README sections, size-capped."""

        repo_id = uuid.UUID(state["repo"].id)
        with session_scope(self.deps.session_factory) as session:
            paths, symbols, readme = repo_dao.repo_outline(session, repo_id)

        lines: list[str] = []
        for path in paths:
            names = symbols.get(path, [])
            shown = ", ".join(names[:8]) + (" ..." if len(names) > 8 else "")
            lines.append(f"{path}" + (f"  ->  {shown}" if shown else ""))
        repo_map = truncate_middle("\n".join(lines), REPO_MAP_MAX_CHARS, keep_head_lines=60)

        context: list[Source] = [
            Source(
                index=1,
                chunk_id=None,
                path="(repository map)",
                start_line=0,
                end_line=0,
                label="files and top-level symbols",
                content=repo_map,
                score=None,
            )
        ]
        for section in readme[:4]:
            context.append(
                Source(
                    index=len(context) + 1,
                    chunk_id=str(section.id),
                    path="README.md",
                    start_line=section.start_line,
                    end_line=section.end_line,
                    label=section.qualified_name or "README",
                    content=truncate_middle(section.content, 1500),
                    score=None,
                )
            )
        return {"context": context}

    # --------------------------------------------------------------- generation

    def generate_answer(self, state: GraphState) -> dict[str, Any]:
        system, template = load_prompt("answer", self.deps.settings.prompt_version)
        user = template.format(
            repo_name=state["repo"].name,
            question=state["question"],
            sources=format_sources(state.get("context", [])),
        )
        parts: list[str] = []
        for token in self.deps.llm.stream(system, user):
            parts.append(token)
            _emit_token(token)
        return {"answer": "".join(parts).strip()}

    def validate_citations(self, state: GraphState) -> dict[str, Any]:
        answer, citations, grounded = validate_citations(
            state.get("answer", ""), state.get("context", []), state["repo"]
        )
        return {
            "answer": answer,
            "citations": citations,
            "grounded": grounded,
            "abstained": looks_like_abstention(answer),
        }

    def respond_not_found(self, state: GraphState) -> dict[str, Any]:
        _emit_token(NOT_FOUND_ANSWER)
        return {
            "answer": NOT_FOUND_ANSWER,
            "citations": [],
            "grounded": False,
            "abstained": True,
            "context": [],
        }


# -------------------------------------------------------------- edge functions


def after_route(state: GraphState) -> str:
    return {
        "code_search": "retrieve_hybrid",
        "dependency": "lookup_dependencies",
        "overview": "build_repo_map",
        "out_of_scope": "respond_not_found",
    }[state["route"]]


def after_gate(state: GraphState) -> str:
    return {
        "sufficient": "generate_answer",
        "retry": "rewrite_query",
        "abstain": "respond_not_found",
    }[state["gate"]]


def after_dependencies(state: GraphState) -> str:
    return "generate_answer" if state.get("context") else "retrieve_hybrid"
```


### Step 6.8: Wiring the graph (`graph/pipeline.py`)

**What:** add nodes, connect edges, compile.

**Why `_timed`:** every node is wrapped so it also returns `{"<node>_ms": elapsed}`. The
reducer in `state.py` adds these up. You get a per-stage latency breakdown for free,
stored in `query_logs.stage_latency_ms`.

<!-- file: src/codeqa/graph/pipeline.py -->
**`src/codeqa/graph/pipeline.py`**

```python
import time
from typing import Any, Protocol

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from codeqa.graph.nodes import (
    GraphDeps,
    QueryNodes,
    after_dependencies,
    after_gate,
    after_route,
)
from codeqa.graph.state import GraphState


class NodeFn(Protocol):
    def __call__(self, state: GraphState) -> dict[str, Any]: ...


def _timed(name: str, fn: NodeFn) -> NodeFn:
    """Wrap a node so it also reports how long it took (merged into `timings_ms`)."""

    def wrapper(state: GraphState) -> dict[str, Any]:
        started = time.perf_counter()
        update = fn(state)
        elapsed = round((time.perf_counter() - started) * 1000, 2)
        return {**update, "timings_ms": {f"{name}_ms": elapsed}}

    return wrapper


def build_graph(deps: GraphDeps) -> CompiledStateGraph:  # type: ignore[type-arg]
    nodes = QueryNodes(deps)
    graph = StateGraph(GraphState)

    for name in (
        "route_question",
        "retrieve_hybrid",
        "rerank_and_gate",
        "rewrite_query",
        "lookup_dependencies",
        "build_repo_map",
        "generate_answer",
        "validate_citations",
        "respond_not_found",
    ):
        graph.add_node(name, _timed(name, getattr(nodes, name)))

    graph.add_edge(START, "route_question")
    graph.add_conditional_edges(
        "route_question",
        after_route,
        ["retrieve_hybrid", "lookup_dependencies", "build_repo_map", "respond_not_found"],
    )
    graph.add_edge("retrieve_hybrid", "rerank_and_gate")
    graph.add_conditional_edges(
        "rerank_and_gate", after_gate, ["generate_answer", "rewrite_query", "respond_not_found"]
    )
    graph.add_edge("rewrite_query", "retrieve_hybrid")  # the bounded corrective loop
    graph.add_conditional_edges(
        "lookup_dependencies", after_dependencies, ["generate_answer", "retrieve_hybrid"]
    )
    graph.add_edge("build_repo_map", "generate_answer")
    graph.add_edge("generate_answer", "validate_citations")
    graph.add_edge("validate_citations", END)
    graph.add_edge("respond_not_found", END)
    return graph.compile()
```


### Step 6.9: The query service (`services/query_service.py`)

**What:** load the repo, run the graph with streaming, collect the final state into a
`QueryResult`, and log it to `query_logs`.

**Why a service around the graph:** interfaces (CLI, API) should not know about LangGraph
stream modes or database logging. They call `ask()`.

<!-- file: src/codeqa/services/query_service.py -->
**`src/codeqa/services/query_service.py`**

```python
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, cast

from codeqa.db import repositories as repo_dao
from codeqa.db.session import session_scope
from codeqa.graph.nodes import GraphDeps
from codeqa.graph.pipeline import build_graph
from codeqa.graph.state import Citation, GraphState, RepoContext, Source
from codeqa.logging import get_logger
from codeqa.models import QueryLog
from codeqa.services.repos import load_repo_context

log = get_logger(__name__)

TokenCallback = Callable[[str], None]


@dataclass
class QueryResult:
    question: str
    answer: str
    route: str
    grounded: bool
    abstained: bool
    citations: list[Citation]
    sources: list[Source]
    timings_ms: dict[str, float]
    query_log_id: uuid.UUID | None = None
    queries: list[str] = field(default_factory=list)


class QueryService:
    """Runs the LangGraph pipeline for one question and logs the result."""

    def __init__(self, deps: GraphDeps) -> None:
        self._deps = deps
        self._graph = build_graph(deps)

    def ask(
        self, question: str, repo_name: str, *, on_token: TokenCallback | None = None
    ) -> QueryResult:
        repo = load_repo_context(self._deps.session_factory, repo_name)
        started = time.perf_counter()

        final: GraphState = {}
        inputs: GraphState = {"question": question, "repo": repo, "timings_ms": {}}
        # stream_mode=["custom", "values"] yields (mode, payload) pairs: "custom" carries
        # tokens from generate_answer, "values" the full state after each step.
        for item in self._graph.stream(inputs, stream_mode=["custom", "values"]):
            mode, payload = cast(tuple[str, Any], item)
            if mode == "custom" and on_token is not None:
                on_token(payload["token"])
            elif mode == "values":
                final = payload

        timings = dict(final.get("timings_ms", {}))
        timings["total_ms"] = round((time.perf_counter() - started) * 1000, 2)
        result = QueryResult(
            question=question,
            answer=final.get("answer", ""),
            route=final.get("route", "code_search"),
            grounded=final.get("grounded", False),
            abstained=final.get("abstained", False),
            citations=final.get("citations", []),
            sources=final.get("context", []),
            timings_ms=timings,
            queries=final.get("queries", []),
        )
        result.query_log_id = self._log(repo, result)
        log.info(
            "query_answered",
            route=result.route,
            grounded=result.grounded,
            total_ms=timings["total_ms"],
        )
        return result

    def _log(self, repo: RepoContext, result: QueryResult) -> uuid.UUID:
        with session_scope(self._deps.session_factory) as session:
            return repo_dao.add_query_log(
                session,
                QueryLog(
                    repository_id=uuid.UUID(repo.id),
                    question=result.question,
                    route=result.route,
                    retrieved_chunk_ids=[s["chunk_id"] for s in result.sources if s["chunk_id"]],
                    answer=result.answer,
                    citations=[dict(c) for c in result.citations],
                    grounded=result.grounded,
                    stage_latency_ms=result.timings_ms,
                    model=self._deps.llm.name,
                    prompt_version=self._deps.settings.prompt_version,
                ),
            )
```


### Step 6.10: Final container

Replace `container.py` with the final version (adds `get_query_service`):

<!-- file: src/codeqa/container.py -->
**`src/codeqa/container.py`**

```python
"""Builds the real services once per process. CLI and API both get services from here.

Tests do not use this module: they construct services with fakes directly.
"""

from functools import lru_cache

from codeqa.config import get_settings
from codeqa.graph.llm import get_llm
from codeqa.graph.nodes import GraphDeps
from codeqa.ingest.pipeline import IndexingService
from codeqa.retrieval.embedder import get_embedder
from codeqa.retrieval.reranker import get_reranker
from codeqa.retrieval.search import SearchService
from codeqa.retrieval.sparse import get_sparse_encoder
from codeqa.retrieval.store import QdrantStore, get_qdrant_client
from codeqa.services.query_service import QueryService


def store_for(collection: str) -> QdrantStore:
    return QdrantStore(get_qdrant_client(), collection)


@lru_cache
def get_indexing_service() -> IndexingService:
    return IndexingService(
        store_for=store_for,
        embedder_for=get_embedder,
        sparse=get_sparse_encoder(get_settings().sparse_model),
    )


@lru_cache
def get_search_service() -> SearchService:
    return SearchService(
        store_for=store_for,
        embedder_for=get_embedder,
        sparse=get_sparse_encoder(get_settings().sparse_model),
    )


@lru_cache
def get_query_service() -> QueryService:
    settings = get_settings()
    return QueryService(
        GraphDeps(
            search=get_search_service(),
            llm=get_llm(settings),
            settings=settings,
            reranker=get_reranker() if settings.reranker_enabled else None,
        )
    )
```


### Step 6.11: CLI `ask` (`cli/ask.py`)

**What:** stream the answer, then print a citations table and the route, grounded flag,
latency and query log id.

<!-- file: src/codeqa/cli/ask.py -->
**`src/codeqa/cli/ask.py`**

```python
from dataclasses import asdict

from rich.markup import escape
from rich.table import Table

from codeqa.cli.app import JsonOption, RepoOption, app, console, print_json


@app.command()
def ask(question: str, repo: RepoOption, as_json: JsonOption = False) -> None:
    """Ask a question; get an answer with file:line citations."""

    from codeqa.container import get_query_service

    service = get_query_service()
    on_token = None if as_json else (lambda t: console.print(t, end="", markup=False))
    result = service.ask(question, repo, on_token=on_token)

    if as_json:
        print_json(asdict(result))
        return
    console.print()
    if result.citations:
        table = Table(title="Citations")
        for column in ("#", "location", "symbol", "link"):
            table.add_column(column)
        for c in result.citations:
            location = f"{c['path']}:{c['start_line']}-{c['end_line']}"
            table.add_row(str(c["index"]), location, escape(c["label"]), c["permalink"] or location)
        console.print(table)
    grounded = "[green]yes[/green]" if result.grounded else "[yellow]no[/yellow]"
    console.print(
        f"[dim]route={result.route} grounded=[/dim]{grounded} "
        f"[dim]total={result.timings_ms.get('total_ms')} ms "
        f"log_id={result.query_log_id}[/dim]"
    )
```


### Step 6.12: Measuring the router (`evaluation/routing.py`, `cli/eval_routing.py`)

**What:** accuracy of `route_question` against the `route` you labelled, and the list of
misses.

**Why:** it needs no LLM, so run it after every change to `router.py`. Each miss tells you
which pattern to add.

<!-- file: src/codeqa/evaluation/routing.py -->
**`src/codeqa/evaluation/routing.py`**

```python
from codeqa.evaluation.dataset import EvalDataset
from codeqa.graph.router import route_question


def routing_report(dataset: EvalDataset) -> tuple[float, list[tuple[str, str, str]]]:
    """Accuracy of the rule router, plus every miss as (id, expected, got).

    Needs no LLM, so run it on every change to router.py. Upgrade to an LLM router only
    if this number is too low to live with.
    """

    misses: list[tuple[str, str, str]] = [
        (q.id, q.route, got)
        for q in dataset.questions
        if (got := route_question(q.question)) != q.route
    ]
    total = len(dataset.questions)
    accuracy = round((total - len(misses)) / total, 3) if total else 0.0
    return accuracy, misses
```


<!-- file: src/codeqa/cli/eval_routing.py -->
**`src/codeqa/cli/eval_routing.py`**

```python
from pathlib import Path

from codeqa.cli.app import console, eval_app


@eval_app.command("routing")
def eval_routing(dataset: Path = Path("eval/datasets/dev_questions.yaml")) -> None:
    """Accuracy of the rule-based router against the labelled `route` of each question."""

    from codeqa.evaluation.dataset import load_dataset
    from codeqa.evaluation.routing import routing_report

    accuracy, misses = routing_report(load_dataset(dataset))
    console.print(f"Routing accuracy: [bold]{accuracy}[/bold]")
    for question_id, expected, got in misses:
        console.print(f"  {question_id}: expected {expected}, got {got}")
```


<!-- file: src/codeqa/cli/main.py -->
**`src/codeqa/cli/main.py`**

```python
from rich.markup import escape

# Importing a command module registers its commands on `app` (decorators run on import).
from codeqa.cli import (  # noqa: F401
    ask,
    chunk,
    eval_calibrate,
    eval_retrieval,
    eval_routing,
    index,
    search,
)
from codeqa.cli.app import app, console
from codeqa.errors import CodeQAError


def main() -> None:
    try:
        app()
    except CodeQAError as exc:
        console.print(f"[red]Error:[/red] {escape(exc.message)}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
```


### Step 6.13: Tests

Unit tests for the router, citations and context budget:

<!-- file: tests/unit/test_router.py -->
**`tests/unit/test_router.py`**

```python
import pytest

from codeqa.graph.router import dependency_direction, extract_symbol, route_question


@pytest.mark.parametrize(
    ("question", "route"),
    [
        ("Who calls get_user_by_id?", "dependency"),
        ("Where is `RetryPolicy` used?", "dependency"),
        ("What does Client.send call?", "dependency"),
        ("How is this repo organized?", "overview"),
        ("Give me an overview of the architecture", "overview"),
        ("How are retries handled?", "code_search"),
        ("What does get_user_by_id do?", "code_search"),
        ("hello!", "out_of_scope"),
        ("tell me a joke", "out_of_scope"),
        ("", "out_of_scope"),
    ],
)
def test_route_question(question: str, route: str) -> None:
    assert route_question(question) == route


@pytest.mark.parametrize(
    ("question", "symbol"),
    [
        ("Who calls `send()`?", "send"),
        ("Who calls get_user_by_id?", "get_user_by_id"),
        ("What does Client.send call?", "Client.send"),
        ("Where is RetryPolicy used?", "RetryPolicy"),
        ("who calls helper", "helper"),
        ("how does it work", None),
    ],
)
def test_extract_symbol(question: str, symbol: str | None) -> None:
    assert extract_symbol(question) == symbol


def test_dependency_direction() -> None:
    assert dependency_direction("What does Client.send call?") == "callees"
    assert dependency_direction("Who calls send?") == "callers"
```


<!-- file: tests/unit/test_citations_and_context.py -->
**`tests/unit/test_citations_and_context.py`**

```python
from codeqa.graph.citations import looks_like_abstention, validate_citations
from codeqa.graph.context import format_sources, truncate_middle
from codeqa.graph.state import RepoContext, Source

REPO = RepoContext("r", "shop", "c", "m", "https://github.com/acme/shop", "abc123")


def _source(index: int) -> Source:
    return Source(
        index=index,
        chunk_id=f"id{index}",
        path="shop/client.py",
        start_line=10 * index,
        end_line=10 * index + 5,
        label=f"f{index}",
        content="code",
        score=None,
    )


def test_invalid_markers_are_dropped_and_valid_ones_cited() -> None:
    answer, citations, grounded = validate_citations(
        "Retries use backoff [2] and send loops [1, 7] [9].", [_source(1), _source(2)], REPO
    )
    assert answer == "Retries use backoff [2] and send loops [1] ."
    assert [c["index"] for c in citations] == [2, 1]
    assert grounded
    assert citations[0]["permalink"] == (
        "https://github.com/acme/shop/blob/abc123/shop/client.py#L20-L25"
    )


def test_answer_without_citations_is_not_grounded() -> None:
    _, citations, grounded = validate_citations("It just works.", [_source(1)], REPO)
    assert citations == [] and not grounded


def test_abstention_detection() -> None:
    assert looks_like_abstention("I couldn't find this in the indexed code.")
    assert not looks_like_abstention("The client retries [1].")


def test_truncate_middle_keeps_head_and_tail() -> None:
    text = "def f():\n" + "\n".join(f"    x = {i}" for i in range(500)) + "\n    return x"
    cut = truncate_middle(text, 300)
    assert cut.startswith("def f():") and cut.endswith("return x")
    assert "omitted" in cut and len(cut) < 400


def test_format_sources_numbers_blocks() -> None:
    rendered = format_sources([_source(1)])
    assert rendered.startswith("[1] shop/client.py L10-L15 (f1)")
```


<!-- file: tests/unit/test_routing_eval.py -->
**`tests/unit/test_routing_eval.py`**

```python
from codeqa.evaluation.dataset import load_dataset
from codeqa.evaluation.routing import routing_report
from tests.conftest import FIXTURES


def test_rule_router_matches_the_labelled_routes() -> None:
    dataset = load_dataset(FIXTURES / "eval" / "shop_questions.yaml")
    assert routing_report(dataset) == (1.0, [])
```


Integration tests run the **whole graph** with `FakeLLM`, the fake embedders and in-memory
stores: all three routes, logging, the bounded retry, and abstention without an LLM call:

<!-- file: tests/integration/test_query_graph.py -->
**`tests/integration/test_query_graph.py`**

```python
import shutil
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from codeqa.config import get_settings
from codeqa.graph.llm import FakeLLM
from codeqa.graph.nodes import GraphDeps
from codeqa.ingest.pipeline import IndexingService
from codeqa.models import QueryLog
from codeqa.retrieval.reranker import OverlapReranker
from codeqa.retrieval.search import SearchService
from codeqa.services.query_service import QueryService
from tests.conftest import SAMPLE_REPO


@pytest.fixture
def indexed(tmp_path: Path, indexer: IndexingService) -> str:
    repo = tmp_path / "shop_repo"
    shutil.copytree(SAMPLE_REPO, repo)
    indexer.index(str(repo), "shop", collection="graph_test")
    return "shop"


def _service(
    search_service: SearchService,
    session_factory: sessionmaker[Session],
    llm: FakeLLM | None = None,
    reranker: OverlapReranker | None = None,
    threshold: float = 0.0,
) -> QueryService:
    settings = get_settings().model_copy(update={"evidence_threshold": threshold})
    return QueryService(
        GraphDeps(
            search=search_service,
            llm=llm or FakeLLM(),
            settings=settings,
            reranker=reranker,
            session_factory=session_factory,
        )
    )


def test_code_search_answers_with_citations_and_logs(
    indexed: str, search_service: SearchService, session_factory: sessionmaker[Session]
) -> None:
    tokens: list[str] = []
    result = _service(search_service, session_factory).ask(
        "How are retries handled?", indexed, on_token=tokens.append
    )
    assert result.route == "code_search"
    assert result.grounded and result.citations[0]["index"] == 1
    assert "".join(tokens).strip() == result.answer
    assert {"retrieve_hybrid_ms", "generate_answer_ms", "total_ms"} <= set(result.timings_ms)

    with session_factory() as session:
        log = session.scalar(select(QueryLog))
        assert log is not None and log.route == "code_search" and log.grounded


def test_dependency_route_uses_the_call_graph(
    indexed: str, search_service: SearchService, session_factory: sessionmaker[Session]
) -> None:
    result = _service(search_service, session_factory).ask("Who calls get_user_by_id?", indexed)
    assert result.route == "dependency"
    labels = [s["label"] for s in result.sources]
    assert "get_user_by_id, definition" in labels
    assert "Client.current_user, caller" in labels


def test_overview_route_uses_the_repo_map(
    indexed: str, search_service: SearchService, session_factory: sessionmaker[Session]
) -> None:
    result = _service(search_service, session_factory).ask("How is this repo organized?", indexed)
    assert result.route == "overview"
    assert result.sources[0]["path"] == "(repository map)"
    assert "shop/client.py" in result.sources[0]["content"]


def test_weak_evidence_retries_once_then_abstains(
    indexed: str, search_service: SearchService, session_factory: sessionmaker[Session]
) -> None:
    llm = FakeLLM()
    service = _service(
        search_service, session_factory, llm=llm, reranker=OverlapReranker(), threshold=0.99
    )
    result = service.ask("Which kubernetes operator deploys the frontend?", indexed)

    assert result.abstained and not result.grounded
    assert len(result.queries) == 2  # original + exactly one rewrite
    assert result.answer == "I couldn't find this in the indexed code."


def test_out_of_scope_abstains_without_calling_the_llm(
    indexed: str, search_service: SearchService, session_factory: sessionmaker[Session]
) -> None:
    llm = FakeLLM()
    result = _service(search_service, session_factory, llm=llm).ask("tell me a joke", indexed)
    assert result.route == "out_of_scope" and result.abstained
    assert llm.calls == []
```


**Check:** `make lint && make test` (74 passed).

### Step 6.14: Try it for real

```bash
uv run codeqa ask "How does the client follow redirects?" -r httpx
uv run codeqa ask "Who calls send?" -r httpx
uv run codeqa ask "How is this repository organized?" -r httpx
uv run codeqa ask "Which Kubernetes operator deploys this?" -r httpx   # should abstain
uv run codeqa eval routing --dataset eval/datasets/dev_questions.yaml
```

Check the log table filled up:

```bash
docker compose exec postgres psql -U codeqa -c \
  "select route, grounded, model, stage_latency_ms->>'total_ms' from query_logs order by created_at desc limit 5;"
```

**Export the graph diagram** for your README:

```bash
uv run python - <<'EOF' > docs/images/graph.mmd
from codeqa.config import get_settings
from codeqa.graph.llm import FakeLLM
from codeqa.graph.nodes import GraphDeps
from codeqa.graph.pipeline import build_graph

graph = build_graph(GraphDeps(search=None, llm=FakeLLM(), settings=get_settings()))  # type: ignore[arg-type]
print(graph.get_graph().draw_mermaid())
EOF
```

GitHub renders Mermaid inside a Markdown ```` ```mermaid ```` block, so you can paste the
file's content straight into the README.

### Phase 6: Definition of Done

- All three routes produce grounded answers with valid citations on the dev repo.
- An unanswerable question reliably abstains.
- `query_logs` fills correctly (route, latencies, model, prompt version).
- Every node is covered by a test that uses fakes; the test suite makes no network calls.


---

## Phase 7. REST API and web UI

**Goal:** a stranger can open `localhost:8501`, index a repo and ask a question without
reading your code; developers get OpenAPI docs at `localhost:8000/docs`.

```bash
git checkout -b phase-7-api-ui
```

### 7.0 Concepts you need first

- **Sync vs async endpoints in FastAPI.** Our services are synchronous and CPU/IO heavy.
  A route declared with plain `def` runs in a worker thread, so it does not block the event
  loop. (Declaring it `async def` and calling blocking code inside would freeze the whole
  server during every request. That is the plan's "blocking the event loop" pitfall.)
- **Background tasks.** `POST /repositories` returns `202 Accepted` with a `job_id`
  immediately; FastAPI runs indexing after the response is sent. The client polls
  `GET /jobs/{id}`. For one user this is enough; a queue (Celery, Redis) is out of scope.
- **Dependencies (`Depends`).** Routes receive services through small functions in
  `deps.py`. Tests replace those functions with `app.dependency_overrides`, which is how
  the API tests run with fakes.
- **One error envelope.** Every error has the shape
  `{"error": {"code", "message", "request_id"}}`. Known errors (`CodeQAError`) map to their
  status code; validation errors to 422; anything else to a generic 500 whose stack trace
  is **logged, never returned**.
- **Request ids.** A middleware tags every log line of a request with one id and returns
  it in the `x-request-id` header. When a user reports an error, that id finds all related
  log lines.

### Step 7.1: Request and response models (`api/schemas.py`)

**What:** Pydantic models for every request and response.

**Why:** FastAPI validates input against them (a `top_k` of 500 is rejected with a 422
before your code runs) and generates the OpenAPI docs from them. Note the constraints:
`name` must match `^[\w.-]+$`, questions are 1 to 2,000 characters, `top_k` is 1 to 50,
`rating` is exactly -1 or 1.

<!-- file: src/codeqa/api/__init__.py -->
**`src/codeqa/api/__init__.py`** (empty file: create it with no content)


<!-- file: src/codeqa/api/schemas.py -->
**`src/codeqa/api/schemas.py`**

```python
import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    code: str
    message: str
    request_id: str | None = None


class ErrorResponse(BaseModel):
    """Every error has this shape, so clients handle one format."""

    error: ErrorBody


class IndexRequest(BaseModel):
    source: str = Field(description="Local folder (inside LOCAL_INDEX_ROOT) or git URL")
    name: str = Field(min_length=1, max_length=100, pattern=r"^[\w.-]+$")
    chunker: Literal["ast", "fixed"] = "ast"
    embedding_model: str | None = None


class IndexAccepted(BaseModel):
    repository_id: uuid.UUID
    job_id: uuid.UUID


class RepositoryOut(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    source_url: str | None
    commit_sha: str
    chunker: str
    embedding_model: str
    files: int
    chunks: int
    last_indexed_at: datetime | None


class JobOut(BaseModel):
    id: uuid.UUID
    repository_id: uuid.UUID
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    files_processed: int
    chunks_created: int
    error: str | None


class SearchRequest(BaseModel):
    repo: str
    query: str = Field(min_length=1, max_length=2000)
    mode: Literal["dense", "sparse", "hybrid", "hybrid_local"] = "hybrid"
    top_k: int = Field(default=10, ge=1, le=50)
    path_prefix: str | None = None
    language: str | None = None
    kind: str | None = None


class SearchHit(BaseModel):
    chunk_id: str
    rank: int
    score: float
    path: str
    start_line: int
    end_line: int
    kind: str
    qualified_name: str | None
    content: str


class SearchResponseOut(BaseModel):
    results: list[SearchHit]
    timings_ms: dict[str, float]


class QueryRequest(BaseModel):
    repo: str
    question: str = Field(min_length=1, max_length=2000)


class QueryResponseOut(BaseModel):
    answer: str
    route: str
    grounded: bool
    abstained: bool
    citations: list[dict[str, Any]]
    sources: list[dict[str, Any]]
    timings_ms: dict[str, float]
    query_log_id: uuid.UUID | None


class FeedbackRequest(BaseModel):
    query_log_id: uuid.UUID
    rating: Literal[-1, 1]
    comment: str | None = Field(default=None, max_length=2000)


class HealthOut(BaseModel):
    status: Literal["ok", "degraded"]
    checks: dict[str, str]
```


### Step 7.2: Dependencies (`api/deps.py`)

<!-- file: src/codeqa/api/deps.py -->
**`src/codeqa/api/deps.py`**

```python
"""FastAPI dependencies. Tests swap these with `app.dependency_overrides[...] = ...`."""

from codeqa import container
from codeqa.db.session import SessionFactory
from codeqa.ingest.pipeline import IndexingService
from codeqa.retrieval.search import SearchService
from codeqa.services.query_service import QueryService


def get_session_factory() -> SessionFactory | None:
    return None  # None = the default factory built from settings


def get_indexing_service() -> IndexingService:
    return container.get_indexing_service()


def get_search_service() -> SearchService:
    return container.get_search_service()


def get_query_service() -> QueryService:
    return container.get_query_service()
```


### Step 7.3: Routes (`api/routes/`)

**`/health`** checks Postgres (`SELECT 1`) and Qdrant, and reports whether the LLM is
configured. It returns 503 when a database is down, which Docker uses to decide whether
the container is healthy. It does **not** call the LLM: a health check that spends API
quota every 10 seconds is a bad idea.

<!-- file: src/codeqa/api/routes/__init__.py -->
**`src/codeqa/api/routes/__init__.py`** (empty file: create it with no content)


<!-- file: src/codeqa/api/routes/health.py -->
**`src/codeqa/api/routes/health.py`**

```python
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text

from codeqa.api.deps import get_session_factory
from codeqa.api.schemas import HealthOut
from codeqa.config import get_settings
from codeqa.db.session import SessionFactory, session_scope
from codeqa.retrieval.store import get_qdrant_client

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut)
def health(
    response: Response,
    session_factory: Annotated[SessionFactory | None, Depends(get_session_factory)],
) -> HealthOut:
    checks: dict[str, str] = {}
    try:
        with session_scope(session_factory) as session:
            session.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except Exception:
        checks["postgres"] = "unreachable"
    try:
        get_qdrant_client().get_collections()
        checks["qdrant"] = "ok"
    except Exception:
        checks["qdrant"] = "unreachable"

    settings = get_settings()
    key = {"groq": settings.groq_api_key, "gemini": settings.google_api_key}.get(
        settings.llm_provider, "n/a"
    )
    checks["llm"] = f"{settings.llm_provider}: " + ("missing api key" if key is None else "ok")

    healthy = checks["postgres"] == "ok" and checks["qdrant"] == "ok"
    if not healthy:
        response.status_code = 503
    return HealthOut(status="ok" if healthy else "degraded", checks=checks)
```


**`/repositories` and `/jobs/{id}`.** `create_repository` validates a local path against
`LOCAL_INDEX_ROOT` *before* creating anything (fail fast with a 422), calls `prepare()`,
schedules `run()` in the background, and returns the ids.

<!-- file: src/codeqa/api/routes/repositories.py -->
**`src/codeqa/api/routes/repositories.py`**

```python
import contextlib
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, status

from codeqa.api.deps import get_indexing_service, get_session_factory
from codeqa.api.schemas import IndexAccepted, IndexRequest, JobOut, RepositoryOut
from codeqa.config import get_settings
from codeqa.db import repositories as repo_dao
from codeqa.db.session import SessionFactory, session_scope
from codeqa.errors import NotFoundError
from codeqa.ingest.pipeline import IndexingService
from codeqa.ingest.source import is_remote, resolve_source

router = APIRouter(tags=["repositories"])


@router.post("/repositories", response_model=IndexAccepted, status_code=status.HTTP_202_ACCEPTED)
def create_repository(
    body: IndexRequest,
    background: BackgroundTasks,
    service: Annotated[IndexingService, Depends(get_indexing_service)],
) -> IndexAccepted:
    """Register a repo and start indexing in the background. Poll `/jobs/{job_id}`."""

    allowed_root = get_settings().local_index_root
    if not is_remote(body.source):
        resolve_source(body.source, allowed_root=allowed_root)  # fail fast with a 422
    repo_id, job_id = service.prepare(
        body.source, body.name, chunker=body.chunker, embedding_model=body.embedding_model
    )
    # Runs after the response is sent, in a worker thread (the endpoint is sync).
    background.add_task(_run_job, service, repo_id, job_id, allowed_root)
    return IndexAccepted(repository_id=repo_id, job_id=job_id)


def _run_job(
    service: IndexingService, repo_id: uuid.UUID, job_id: uuid.UUID, root: Path | None
) -> None:
    # Errors are already stored on the job row and logged by the service. Swallow them
    # here so a failed background job does not print a second traceback.
    with contextlib.suppress(Exception):
        service.run(repo_id, job_id, allowed_root=root)


@router.get("/repositories", response_model=list[RepositoryOut])
def list_repositories(
    session_factory: Annotated[SessionFactory | None, Depends(get_session_factory)],
) -> list[RepositoryOut]:
    with session_scope(session_factory) as session:
        return [
            RepositoryOut(
                id=repo.id,
                name=repo.name,
                status=repo.status,
                source_url=repo.source_url,
                commit_sha=repo.commit_sha,
                chunker=repo.chunker,
                embedding_model=repo.embedding_model,
                files=n_files,
                chunks=n_chunks,
                last_indexed_at=repo.last_indexed_at,
            )
            for repo, n_files, n_chunks in repo_dao.list_repositories(session)
        ]


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(
    job_id: uuid.UUID,
    session_factory: Annotated[SessionFactory | None, Depends(get_session_factory)],
) -> JobOut:
    with session_scope(session_factory) as session:
        job = repo_dao.get_job(session, job_id)
        if job is None:
            raise NotFoundError(f"job {job_id} not found")
        return JobOut.model_validate(job, from_attributes=True)
```


**`/search`**: raw retrieval with no LLM. Great for demos and debugging.

<!-- file: src/codeqa/api/routes/search.py -->
**`src/codeqa/api/routes/search.py`**

```python
from typing import Annotated

from fastapi import APIRouter, Depends

from codeqa.api.deps import get_search_service, get_session_factory
from codeqa.api.schemas import SearchHit, SearchRequest, SearchResponseOut
from codeqa.db.session import SessionFactory
from codeqa.retrieval.search import SearchService
from codeqa.retrieval.store import SearchFilters
from codeqa.services.repos import load_repo_context

router = APIRouter(tags=["search"])


@router.post("/search", response_model=SearchResponseOut)
def search(
    body: SearchRequest,
    service: Annotated[SearchService, Depends(get_search_service)],
    session_factory: Annotated[SessionFactory | None, Depends(get_session_factory)],
) -> SearchResponseOut:
    """Raw retrieval without the LLM: shows exactly what the retriever returns."""

    target = load_repo_context(session_factory, body.repo).search_target()
    filters = SearchFilters(path_prefix=body.path_prefix, language=body.language, kind=body.kind)
    response = service.search(body.query, target, body.mode, body.top_k, filters)
    return SearchResponseOut(
        results=[
            SearchHit(
                chunk_id=r.chunk_id,
                rank=r.rank,
                score=r.score,
                path=r.path,
                start_line=r.start_line,
                end_line=r.end_line,
                kind=r.kind,
                qualified_name=r.qualified_name,
                content=r.content,
            )
            for r in response.results
        ],
        timings_ms=response.timings_ms,
    )
```


**`/query` and `/query/stream`.** `/query` returns the full answer as JSON. `/query/stream`
returns **NDJSON** (one JSON object per line): `{"type":"token"}` lines while the answer is
generated, then one `{"type":"final", ...}` line with citations and timings, or one
`{"type":"error"}` line.

How the streaming works: `ask()` is synchronous and reports tokens through a callback. A
worker thread runs `ask()` and puts each token on a `queue.Queue`; the response generator
takes tokens off the queue and yields them. A `None` sentinel means "finished".

<!-- file: src/codeqa/api/routes/query.py -->
**`src/codeqa/api/routes/query.py`**

```python
import json
import queue
import threading
from collections.abc import Iterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from codeqa.api.deps import get_query_service
from codeqa.api.schemas import QueryRequest, QueryResponseOut
from codeqa.errors import CodeQAError
from codeqa.services.query_service import QueryResult, QueryService

router = APIRouter(tags=["query"])


def _to_out(result: QueryResult) -> QueryResponseOut:
    return QueryResponseOut(
        answer=result.answer,
        route=result.route,
        grounded=result.grounded,
        abstained=result.abstained,
        citations=[dict(c) for c in result.citations],
        sources=[dict(s) for s in result.sources],
        timings_ms=result.timings_ms,
        query_log_id=result.query_log_id,
    )


@router.post("/query", response_model=QueryResponseOut)
def query(
    body: QueryRequest, service: Annotated[QueryService, Depends(get_query_service)]
) -> QueryResponseOut:
    """Full RAG answer with citations (not streamed)."""

    return _to_out(service.ask(body.question, body.repo))


@router.post("/query/stream")
def query_stream(
    body: QueryRequest, service: Annotated[QueryService, Depends(get_query_service)]
) -> StreamingResponse:
    """Streamed answer as NDJSON: {"type":"token"}..., then one {"type":"final"} or error."""

    tokens: queue.Queue[str | None] = queue.Queue()
    outcome: dict[str, Any] = {}

    def worker() -> None:
        try:
            outcome["result"] = service.ask(body.question, body.repo, on_token=tokens.put)
        except CodeQAError as exc:
            outcome["error"] = {"code": exc.code, "message": exc.message}
        except Exception:
            outcome["error"] = {"code": "internal_error", "message": "Internal server error"}
        finally:
            tokens.put(None)  # sentinel: generation finished

    def events() -> Iterator[str]:
        threading.Thread(target=worker, daemon=True).start()
        while (token := tokens.get()) is not None:
            yield json.dumps({"type": "token", "text": token}) + "\n"
        if "error" in outcome:
            yield json.dumps({"type": "error", **outcome["error"]}) + "\n"
        else:
            final = _to_out(outcome["result"]).model_dump(mode="json")
            yield json.dumps({"type": "final", **final}) + "\n"

    return StreamingResponse(events(), media_type="application/x-ndjson")
```


**`/feedback`**: thumbs up/down on a logged answer. Mining the thumbs-down answers later is
a stretch goal in the plan.

<!-- file: src/codeqa/api/routes/feedback.py -->
**`src/codeqa/api/routes/feedback.py`**

```python
from typing import Annotated

from fastapi import APIRouter, Depends, status

from codeqa.api.deps import get_session_factory
from codeqa.api.schemas import FeedbackRequest
from codeqa.db import repositories as repo_dao
from codeqa.db.session import SessionFactory, session_scope
from codeqa.errors import NotFoundError

router = APIRouter(tags=["feedback"])


@router.post("/feedback", status_code=status.HTTP_201_CREATED)
def feedback(
    body: FeedbackRequest,
    session_factory: Annotated[SessionFactory | None, Depends(get_session_factory)],
) -> dict[str, str]:
    with session_scope(session_factory) as session:
        saved = repo_dao.add_feedback(session, body.query_log_id, body.rating, body.comment)
        if saved is None:
            raise NotFoundError(f"query log {body.query_log_id} not found")
        return {"id": str(saved.id)}
```


### Step 7.4: The application (`api/main.py`)

**What:** `create_app()` with the lifespan hook (logging setup), the request-id
middleware, the three exception handlers, and the routers.

**Why a factory function:** each test can build a fresh app with its own dependency
overrides.

<!-- file: src/codeqa/api/main.py -->
**`src/codeqa/api/main.py`**

```python
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from codeqa import __version__
from codeqa.api.routes import feedback, health, query, repositories, search
from codeqa.errors import CodeQAError
from codeqa.logging import configure_logging, get_logger

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    log.info("api_started", version=__version__)
    yield


def _error(status: int, code: str, message: str) -> JSONResponse:
    request_id = structlog.contextvars.get_contextvars().get("request_id")
    body = {"error": {"code": code, "message": message, "request_id": request_id}}
    return JSONResponse(status_code=status, content=body)


def create_app() -> FastAPI:
    app = FastAPI(title="CodeQA", version=__version__, lifespan=lifespan)

    @app.middleware("http")
    async def request_id_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Tag every log line of this request with one id, and return it as a header."""

        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id, path=request.url.path)
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response

    @app.exception_handler(CodeQAError)
    async def handle_known(_: Request, exc: CodeQAError) -> JSONResponse:
        return _error(exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        first = exc.errors()[0] if exc.errors() else {"msg": "invalid request"}
        where = ".".join(str(p) for p in first.get("loc", []))
        return _error(422, "invalid_request", f"{where}: {first.get('msg')}")

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        # Log the full traceback for us; never leak it to the client.
        log.exception("unhandled_error", error=str(exc))
        return _error(500, "internal_error", "Internal server error")

    for module in (health, repositories, search, query, feedback):
        app.include_router(module.router)
    return app


app = create_app()
```


### Step 7.5: API tests (`tests/integration/test_api.py`)

**What:** FastAPI's `TestClient` runs the app in-process. The fixture overrides every
dependency with the test services, so the full HTTP flow (index in the background, poll
the job, search, query, stream, feedback, errors, health) runs offline.

<!-- file: tests/integration/test_api.py -->
**`tests/integration/test_api.py`**

```python
import shutil
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from codeqa.api import deps
from codeqa.api.main import create_app
from codeqa.config import get_settings
from codeqa.graph.llm import FakeLLM
from codeqa.graph.nodes import GraphDeps
from codeqa.ingest.pipeline import IndexingService
from codeqa.retrieval.search import SearchService
from codeqa.services.query_service import QueryService
from tests.conftest import SAMPLE_REPO


@pytest.fixture
def client(
    tmp_path: Path,
    indexer: IndexingService,
    search_service: SearchService,
    session_factory: sessionmaker[Session],
) -> Iterator[TestClient]:
    app = create_app()
    query_service = QueryService(
        GraphDeps(
            search=search_service,
            llm=FakeLLM(),
            settings=get_settings(),
            session_factory=session_factory,
        )
    )
    app.dependency_overrides[deps.get_session_factory] = lambda: session_factory
    app.dependency_overrides[deps.get_indexing_service] = lambda: indexer
    app.dependency_overrides[deps.get_search_service] = lambda: search_service
    app.dependency_overrides[deps.get_query_service] = lambda: query_service
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def indexed_repo(tmp_path: Path, client: TestClient) -> str:
    repo = tmp_path / "shop_repo"
    shutil.copytree(SAMPLE_REPO, repo)
    response = client.post("/repositories", json={"source": str(repo), "name": "shop"})
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    for _ in range(50):  # TestClient runs background tasks before returning, but be safe
        job = client.get(f"/jobs/{job_id}").json()
        if job["status"] in ("completed", "failed"):
            break
        time.sleep(0.1)
    assert job["status"] == "completed"
    return "shop"


def test_list_repositories(client: TestClient, indexed_repo: str) -> None:
    repos = client.get("/repositories").json()
    assert repos[0]["name"] == "shop" and repos[0]["chunks"] > 0


def test_search_endpoint(client: TestClient, indexed_repo: str) -> None:
    body = {"repo": indexed_repo, "query": "get_user_by_id", "mode": "sparse", "top_k": 3}
    response = client.post("/search", json=body)
    assert response.status_code == 200
    assert response.json()["results"][0]["qualified_name"] == "get_user_by_id"


def test_query_and_feedback(client: TestClient, indexed_repo: str) -> None:
    response = client.post(
        "/query", json={"repo": indexed_repo, "question": "How do retries work?"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["grounded"] and data["citations"]

    feedback = {"query_log_id": data["query_log_id"], "rating": 1}
    assert client.post("/feedback", json=feedback).status_code == 201


def test_query_stream_ends_with_final_event(client: TestClient, indexed_repo: str) -> None:
    with client.stream(
        "POST", "/query/stream", json={"repo": indexed_repo, "question": "How do retries work?"}
    ) as response:
        lines = [line for line in response.iter_lines() if line]
    assert '"type": "token"' in lines[0]
    assert '"type": "final"' in lines[-1]


def test_errors_use_one_envelope(client: TestClient) -> None:
    missing = client.post("/query", json={"repo": "nope", "question": "hi there friend"})
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "not_found"
    assert missing.headers["x-request-id"]

    invalid = client.post("/search", json={"repo": "x", "query": ""})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "invalid_request"


def test_health_reports_checks(client: TestClient) -> None:
    body = client.get("/health").json()
    assert body["checks"]["postgres"] == "ok"
    assert body["checks"]["qdrant"] == "ok"
```


**Check:** `make lint && make test` (80 passed).

### Step 7.6: Run the API

```bash
make up
make api                                    # uvicorn with auto-reload on :8000
```

Open `http://localhost:8000/docs` for interactive docs. From a second terminal:

```bash
curl -s localhost:8000/health
curl -s -X POST localhost:8000/search -H 'content-type: application/json' \
     -d '{"repo": "httpx", "query": "follow redirects", "mode": "hybrid", "top_k": 3}'
curl -s -X POST localhost:8000/query -H 'content-type: application/json' \
     -d '{"repo": "httpx", "question": "How are redirects followed?"}'
curl -N -X POST localhost:8000/query/stream -H 'content-type: application/json' \
     -d '{"repo": "httpx", "question": "How are redirects followed?"}'
```

To index a **local** folder through the API, set `LOCAL_INDEX_ROOT` in `.env` to a folder
that contains your repos (for example `LOCAL_INDEX_ROOT=/tmp`), restart the API, and
POST `{"source": "/tmp/httpx", "name": "httpx"}` to `/repositories`. Git URLs work without
it.

### Step 7.7: The Streamlit UI (`ui/app.py`)

**What:** a thin client: repo picker and "index a repo" form in the sidebar; an *Ask* tab
with a streamed answer, expandable source cards (cited ones marked), GitHub links, a
latency chart and feedback buttons; and a *Search* tab with a dense/sparse/hybrid switch so
a viewer can *see* hybrid search working.

**Why it only talks HTTP:** the plan's rule, "no business logic in the Streamlit file".
If the UI imported services directly, you would have two copies of the app's behaviour
to keep in sync. `@st.cache_data(ttl=5)` avoids calling `/repositories` on every rerun
(Streamlit re-executes the whole script on every click).

<!-- file: src/codeqa/ui/__init__.py -->
**`src/codeqa/ui/__init__.py`** (empty file: create it with no content)


<!-- file: src/codeqa/ui/app.py -->
**`src/codeqa/ui/app.py`**

```python
"""Streamlit client. It talks to the API over HTTP only: no business logic here.

Run: streamlit run src/codeqa/ui/app.py
"""

import json
import os
import time
from collections.abc import Iterator
from typing import Any

import httpx
import streamlit as st

API = os.environ.get("API_BASE_URL", "http://localhost:8000")
client = httpx.Client(base_url=API, timeout=httpx.Timeout(120.0, connect=5.0))

st.set_page_config(page_title="CodeQA", page_icon="🔎", layout="wide")


def api_error(response: httpx.Response) -> str:
    try:
        return str(response.json()["error"]["message"])
    except Exception:
        return f"HTTP {response.status_code}"


@st.cache_data(ttl=5)
def list_repos() -> list[dict[str, Any]]:
    response = client.get("/repositories")
    return list(response.json()) if response.is_success else []


# ---------------------------------------------------------------- sidebar: repos

with st.sidebar:
    st.header("Repositories")
    repos = list_repos()
    ready = [r["name"] for r in repos if r["status"] == "ready"]
    repo = st.selectbox("Ask about", ready, index=0 if ready else None)
    for r in repos:
        st.caption(f"**{r['name']}** · {r['status']} · {r['files']} files · {r['chunks']} chunks")

    with st.form("index"):
        st.subheader("Index a repository")
        source = st.text_input("Git URL or local path", placeholder="https://github.com/org/repo")
        name = st.text_input("Name", placeholder="repo")
        if st.form_submit_button("Index") and source and name:
            response = client.post("/repositories", json={"source": source, "name": name})
            if not response.is_success:
                st.error(api_error(response))
            else:
                job_id = response.json()["job_id"]
                with st.status("Indexing...", expanded=True) as status:
                    while True:
                        job = client.get(f"/jobs/{job_id}").json()
                        done = f"{job['files_processed']} files, {job['chunks_created']} chunks"
                        status.write(done)
                        if job["status"] not in ("pending", "running"):
                            break
                        time.sleep(1.5)
                    status.update(label=f"Job {job['status']}", state="complete")
                list_repos.clear()

# ------------------------------------------------------------------------- tabs

ask_tab, search_tab = st.tabs(["Ask", "Search (no LLM)"])


def render_sources(sources: list[dict[str, Any]], citations: list[dict[str, Any]]) -> None:
    links = {c["index"]: c.get("permalink") for c in citations}
    cited = set(links)
    for s in sources:
        marker = "✅" if s["index"] in cited else "▫️"
        lines = f":L{s['start_line']}-L{s['end_line']}" if s["start_line"] else ""
        with st.expander(f"{marker} [{s['index']}] {s['path']}{lines} — {s['label']}"):
            if links.get(s["index"]):
                st.markdown(f"[Open on GitHub]({links[s['index']]})")
            st.code(s["content"], language="python", line_numbers=True)


with ask_tab:
    question = st.text_input("Question", placeholder="How are retries handled?")
    if st.button("Ask", disabled=not (repo and question)):
        final: dict[str, Any] = {}

        def tokens() -> Iterator[str]:
            with client.stream(
                "POST", "/query/stream", json={"repo": repo, "question": question}
            ) as response:
                for line in response.iter_lines():
                    if not line:
                        continue
                    event = json.loads(line)
                    if event["type"] == "token":
                        yield event["text"]
                    else:
                        final.update(event)

        st.write_stream(tokens())
        if final.get("type") == "error":
            st.error(final["message"])
        elif final:
            badge = "grounded ✅" if final["grounded"] else "not grounded ⚠️"
            st.caption(f"route: {final['route']} · {badge}")
            render_sources(final["sources"], final["citations"])
            with st.expander("Latency breakdown (ms)"):
                st.bar_chart(final["timings_ms"], horizontal=True)
            up, down, _ = st.columns([1, 1, 8])
            if up.button("👍"):
                client.post("/feedback", json={"query_log_id": final["query_log_id"], "rating": 1})
            if down.button("👎"):
                client.post("/feedback", json={"query_log_id": final["query_log_id"], "rating": -1})

with search_tab:
    query = st.text_input("Search query", placeholder="get_user_by_id")
    mode = st.radio("Mode", ["hybrid", "dense", "sparse"], horizontal=True)
    if st.button("Search", disabled=not (repo and query)):
        response = client.post(
            "/search", json={"repo": repo, "query": query, "mode": mode, "top_k": 10}
        )
        if not response.is_success:
            st.error(api_error(response))
        else:
            data = response.json()
            st.caption(f"timings: {data['timings_ms']}")
            for hit in data["results"]:
                title = f"#{hit['rank']} {hit['path']}:L{hit['start_line']}-L{hit['end_line']}"
                with st.expander(f"{title} — {hit['qualified_name'] or hit['kind']}"):
                    st.code(hit["content"], language="python")
```


```bash
make ui          # opens http://localhost:8501 (keep `make api` running)
```

### Phase 7: Definition of Done

- UI at `localhost:8501` and API docs at `localhost:8000/docs` both work locally.
- A friend can index a repo and ask a question in the UI without your help. (Phase 8 makes
  this work with a single `docker compose up`.)


---

## Phase 8. Docker, CI and hardening

**Goal:** `git clone` + `docker compose up` works on a clean machine; CI is green and also
builds the image; editing one file and re-indexing touches only that file.

```bash
git checkout -b phase-8-hardening
```

### Step 8.1: What is already hardened (verify, do not rebuild)

Most hardening from the plan was built into earlier phases. Check each item and be able to
point at the code:

| Plan requirement | Where it lives | How to verify |
|---|---|---|
| Incremental re-index by content hash | `IndexingService._run` compares SHA-256 | Edit one file, re-run `codeqa index`: output says `1 updated`, the rest `unchanged` |
| Delete orphans of removed files | `_delete_removed` | Delete a file, re-index: `1 deleted`, counts still match |
| Per-file error isolation | `try/except` around `_prepare_file` | `test_one_bad_file_does_not_kill_the_job` |
| Retries with backoff on the LLM | `LangChainLLM.complete` (`with_retry`) + provider `max_retries` | |
| Request timeouts | `LLM_TIMEOUT_S`, Qdrant client `timeout=30`, git `timeout=300` | |
| Per-repo chunk cap | `MAX_REPO_CHUNKS` in `_run` | |
| Crash safety | Qdrant first, Postgres commit last | Kill `codeqa index` with Ctrl+C half-way, run it again: counts match |
| Path traversal blocked | `resolve_source(allowed_root=...)` | `test_local_path_outside_allowed_root_is_rejected` |
| Secrets never indexed | `walker._looks_like_secret` | `test_walker_filters` |

**Coverage:** `make cov` prints coverage per file. When this guide was verified the total
was about 87%, with `ingest/` and `retrieval/` well above the plan's 70% target. The
lowest-covered code is the real-model adapters (fastembed, providers), which the offline
test suite deliberately does not load.

### Step 8.2: The Dockerfile (multi-stage)

**What:** stage 1 (`builder`) creates the virtualenv with uv; stage 2 (`runtime`) copies
only that virtualenv into a clean slim image.

**Why each line:**

- **Multi-stage:** uv, caches and build tools stay in the builder; the runtime image is
  smaller and has less to attack.
- **Dependencies before code:** the `uv sync --no-install-project` layer only rebuilds when
  `pyproject.toml` or `uv.lock` change. Editing code rebuilds only the last, fast layer.
- **`--mount=type=cache`:** uv's download cache survives between builds.
- **`--locked`:** fail if `uv.lock` is out of date, instead of silently resolving new
  versions: the image gets exactly the versions you tested.
- **`--no-editable`:** install the package *into* the virtualenv, so the runtime stage does
  not need `src/`. (The prompt `.md` files are package data and are included.)
- **Non-root user `app`:** if the process is ever compromised, it is not root in the
  container.
- **`git`** is needed to clone repos; **`curl`** for the healthcheck.
- **`MODEL_CACHE_DIR=/models`:** Compose mounts a volume there, so the ~640 MB embedding
  model is downloaded once, not on every start.
- **`ui_app.py`:** the Streamlit script is copied as a plain file, because `streamlit run`
  needs a file path.

<!-- file: Dockerfile -->
**`Dockerfile`**

```dockerfile
# syntax=docker/dockerfile:1

# ---------- stage 1: build the virtualenv (has uv, compilers, caches) ----------
FROM python:3.12-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.12.8 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0
WORKDIR /app

# Dependencies first: this layer is cached until pyproject.toml / uv.lock change.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project --no-dev

# Then our code (changes often, so it comes last).
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable

# ---------- stage 2: small runtime image (no uv, no build tools) ----------
FROM python:3.12-slim AS runtime

# git: clone repos to index. curl: container healthchecks.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 app \
    && mkdir -p /models /data /repos \
    && chown app:app /models /data /repos

WORKDIR /app
COPY --from=builder --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app alembic.ini ./
COPY --chown=app:app migrations ./migrations
COPY --chown=app:app src/codeqa/ui/app.py ./ui_app.py

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    MODEL_CACHE_DIR=/models \
    CACHE_DIR=/data

USER app
EXPOSE 8000 8501
CMD ["uvicorn", "codeqa.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```


**`.dockerignore`** keeps the build context small and secret-free: without it, `COPY`
would send `.venv`, `.git`, caches and your `.env` (API keys!) into the build.

<!-- file: .dockerignore -->
**`.dockerignore`**

```gitignore
.git
.venv
.cache
.env
**/__pycache__
.mypy_cache
.ruff_cache
.pytest_cache
.coverage
htmlcov
eval/results
docs/images
repos
data
```


**Check:**

```bash
docker build -t codeqa .
docker run --rm codeqa id        # uid=1000(app): not root
```

### Step 8.3: The full Compose stack (`docker-compose.yml`)

**What:** Postgres, Qdrant, a one-shot `migrate` job, the API and the UI.

**Why the startup order is expressed with conditions:**

```
postgres (healthy) ──► migrate (completed successfully) ──► api (healthy) ──► ui
qdrant   (healthy) ─────────────────────────────────────────┘
```

- `migrate` runs `alembic upgrade head` once and exits. The API only starts after it
  succeeded, so the API never runs against an old schema.
- Inside Compose, services reach each other by **service name** (`postgres:5432`,
  `qdrant:6333`), not `localhost`. That is why `DATABASE_URL` and `QDRANT_HOST` are set
  here, overriding `.env`.
- `env_file` with `required: false` passes your API keys from `.env` if it exists.
- `./repos:/repos:ro` + `LOCAL_INDEX_ROOT=/repos`: put a local repo in `./repos/<name>` and
  index it through the UI as `/repos/<name>`. Read-only, and nothing outside it.
- `QDRANT_LOCATION: ""` makes sure an embedded-mode setting in your `.env` cannot leak
  into the container.

<!-- file: docker-compose.yml -->
**`docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:16.15
    environment:
      POSTGRES_USER: codeqa
      POSTGRES_PASSWORD: codeqa
      POSTGRES_DB: codeqa
    ports: ["5433:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U codeqa -d codeqa"]
      interval: 5s
      timeout: 3s
      retries: 20

  qdrant:
    image: qdrant/qdrant:v1.19.1   # keep in step with the qdrant-client version
    ports: ["6333:6333"]
    volumes: ["qdrantdata:/qdrant/storage"]
    healthcheck:
      test: ["CMD-SHELL", "bash -c ':> /dev/tcp/127.0.0.1/6333' || exit 1"]
      interval: 5s
      timeout: 3s
      retries: 20

  migrate:
    build: .
    command: ["alembic", "upgrade", "head"]
    environment:
      DATABASE_URL: postgresql+psycopg://codeqa:codeqa@postgres:5432/codeqa
    depends_on:
      postgres: {condition: service_healthy}

  api:
    build: .
    env_file:
      - path: .env
        required: false
    environment:
      APP_ENV: production
      DATABASE_URL: postgresql+psycopg://codeqa:codeqa@postgres:5432/codeqa
      QDRANT_HOST: qdrant
      QDRANT_PORT: "6333"
      QDRANT_LOCATION: ""
      LOCAL_INDEX_ROOT: /repos
    ports: ["8000:8000"]
    volumes:
      - models:/models           # embedding models survive restarts (no re-download)
      - clones:/data             # cloned repos
      - ./repos:/repos:ro        # put local repos here to index them as /repos/<name>
    depends_on:
      migrate: {condition: service_completed_successfully}
      qdrant: {condition: service_healthy}
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 12
      start_period: 20s

  ui:
    build: .
    command: ["streamlit", "run", "ui_app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
    environment:
      API_BASE_URL: http://api:8000
    ports: ["8501:8501"]
    depends_on:
      api: {condition: service_healthy}

volumes:
  pgdata:
  qdrantdata:
  models:
  clones:
```


**Check (the plan's "single most common portfolio failure"):**

```bash
docker compose up -d --build
docker compose ps                       # api and postgres/qdrant "healthy"
curl -s localhost:8000/health           # {"status":"ok",...}
# then visit http://localhost:8501 in your browser
```

Then do the real test: clone your repo into a *new* folder (or better, on another machine
or a fresh VM), copy `.env.example` to `.env`, add a key, run `docker compose up -d
--build`, and index + ask from the UI. Fix anything that needed a step you did not write
down. When this guide was verified, the stack came up with a healthy API, indexed a repo
from `/repos` in the background, rejected `/etc` with a 422, and answered with citations.

### Step 8.4: CI builds the image too (`.github/workflows/ci.yml`)

**What:** add a `docker` job that builds the image (without pushing) on every push and PR.

**Why:** a broken Dockerfile is otherwise only discovered by the next person who tries to
run your project. `cache-from/cache-to: type=gha` reuses layers between CI runs.

<!-- file: .github/workflows/ci.yml -->
**`.github/workflows/ci.yml`**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16.15
        env:
          POSTGRES_USER: codeqa
          POSTGRES_PASSWORD: codeqa
          POSTGRES_DB: codeqa
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U codeqa"
          --health-interval 5s
          --health-timeout 3s
          --health-retries 20
    env:
      DATABASE_URL: postgresql+psycopg://codeqa:codeqa@localhost:5432/codeqa
    steps:
      - uses: actions/checkout@v7
      - uses: astral-sh/setup-uv@v10
        with:
          enable-cache: true
      - run: uv sync --locked
      - name: Lint
        run: |
          uv run ruff check .
          uv run ruff format --check .
      - name: Type-check
        run: uv run mypy src
      - name: Migrations apply cleanly and match the models
        run: |
          uv run alembic upgrade head
          uv run alembic check
      - name: Tests (against Postgres)
        env:
          TEST_DATABASE_URL: postgresql+psycopg://codeqa:codeqa@localhost:5432/codeqa
        run: uv run pytest --cov --cov-report=term-missing

  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v7
      - uses: docker/setup-buildx-action@v4
      - uses: docker/build-push-action@v7
        with:
          context: .
          push: false
          cache-from: type=gha
          cache-to: type=gha,mode=max
```


### Step 8.5: Protect `main`

On GitHub: *Settings > Branches > Add branch protection rule* for `main`: require a pull
request, and require the `test` and `docker` checks to pass. Now even you cannot merge red
code, which is exactly what a reviewer wants to see.

### Phase 8: Definition of Done

- Editing one file and re-indexing touches only that file's chunks.
- CI is green (both jobs).
- A fresh clone + `docker compose up` works on a clean machine.


---

## Phase 9. Held-out evaluation, generation evaluation and documentation

**Goal:** honest final numbers on a repo you never tuned on, an evaluation of the
*answers* (not just retrieval), and documentation where every claim is backed by a number.

```bash
git checkout -b phase-9-evaluation-docs
```

### Step 9.1: Generation evaluation (`evaluation/generation.py`)

**What:** ask every dataset question end to end and score the answers.

**The metrics, and why each one exists:**

| Metric | How it is computed | Why |
|---|---|---|
| `route_accuracy` | predicted route == labelled route | Wrong route = wrong kind of context |
| `correct_abstention_rate` | unanswerable questions that abstained | Hallucination control |
| `false_abstention_rate` | answerable questions that abstained | The cost of that control |
| `grounded_flag_rate` | answers with at least one valid citation | Cheap, automatic proxy |
| `cites_ground_truth_rate` | answers citing a ground-truth symbol | Did it use the *right* evidence? |
| `citation_validity` | cited file exists, lines in range, cited symbol name appears in those lines | Catches citations that point at the wrong place |
| `judge_groundedness` | an LLM judge grades GROUNDED (1) / PARTIAL (0.5) / UNGROUNDED (0) | The only metric that reads the answer's claims |

**About the LLM judge (the "mature position" from the plan):** an LLM judge is useful but
biased: it may favour long answers, answers in its own style, or be fooled by confident
text. So the judge prompt is strict and narrow (only "are claims supported by the cited
sources?"), and you **spot-check at least 10 verdicts by hand** and report how often you
agreed with the judge. The code uses the configured LLM as the judge. A judge that is the
same model as the answerer tends to approve its own style, so a worthwhile extension is a
separate `JUDGE_PROVIDER`/`JUDGE_MODEL` setting pointing at a stronger model; if you add it,
say so in `docs/evaluation.md`.

<!-- file: src/codeqa/graph/prompts/judge_v1.md -->
**`src/codeqa/graph/prompts/judge_v1.md`**

```markdown
You are a strict reviewer checking whether an answer about source code is supported by
the numbered sources it cites. You do not know anything about this code beyond the sources.

Grade:
- GROUNDED: every factual claim is supported by the cited sources.
- PARTIAL: some claims are supported, at least one is not.
- UNGROUNDED: the main claims are not supported by the sources.

Reply with the verdict on the first line (GROUNDED, PARTIAL or UNGROUNDED), then one
sentence explaining why.
---
Question: {question}

Sources:
{sources}

Answer to check:
{answer}

Verdict:
```


<!-- file: src/codeqa/evaluation/generation.py -->
**`src/codeqa/evaluation/generation.py`**

```python
from pathlib import Path
from typing import Any

from codeqa.evaluation.dataset import EvalDataset
from codeqa.evaluation.metrics import percentile, truth_spans
from codeqa.graph.context import format_sources
from codeqa.graph.llm import LLM
from codeqa.graph.prompts import load_prompt
from codeqa.graph.state import Citation
from codeqa.services.query_service import QueryResult, QueryService

JUDGE_SCORES = {"GROUNDED": 1.0, "PARTIAL": 0.5, "UNGROUNDED": 0.0}


def citation_is_valid(citation: Citation, repo_root: Path) -> bool:
    """Automatic check: the cited file exists, the line range is inside it, and the
    cited symbol's name actually appears in those lines."""

    if citation["start_line"] == 0:
        return True  # the repo map is a synthetic source without lines
    file = repo_root / citation["path"]
    if not file.exists():
        return False
    lines = file.read_text(encoding="utf-8", errors="replace").split("\n")
    if citation["end_line"] > len(lines) or citation["start_line"] < 1:
        return False
    name = citation["label"].split(",")[0].split(".")[-1].strip()
    window = "\n".join(lines[citation["start_line"] - 1 : citation["end_line"]])
    return name in window or not name.isidentifier()


def judge(llm: LLM, result: QueryResult) -> tuple[float, str]:
    system, template = load_prompt("judge", "v1")
    cited = {c["index"] for c in result.citations}
    sources = [s for s in result.sources if s["index"] in cited]
    reply = llm.complete(
        system,
        template.format(
            question=result.question, sources=format_sources(sources), answer=result.answer
        ),
    )
    verdict = reply.strip().split()[0].upper().strip(".:") if reply.strip() else "UNGROUNDED"
    return JUDGE_SCORES.get(verdict, 0.0), reply.strip()


def run_generation_eval(
    dataset: EvalDataset,
    repo_root: Path,
    service: QueryService,
    judge_llm: LLM | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    for q in dataset.questions:
        result = service.ask(q.question, dataset.repo)
        truth = [truth_spans(repo_root, item) for item in q.relevant]
        cited_truth = any(
            c["path"] == span.path and (span.name is None or c["label"].split(",")[0] == span.name)
            for c in result.citations
            for spans in truth
            for span in spans
        )
        row: dict[str, Any] = {
            "id": q.id,
            "type": q.type,
            "answerable": q.answerable,
            "route_expected": q.route,
            "route": result.route,
            "abstained": result.abstained,
            "grounded_flag": result.grounded,
            "citations": len(result.citations),
            "valid_citations": sum(citation_is_valid(c, repo_root) for c in result.citations),
            "cites_ground_truth": cited_truth,
            "latency_ms": result.timings_ms.get("total_ms", 0.0),
            "answer": result.answer,
        }
        if judge_llm is not None and q.answerable and not result.abstained:
            row["judge_score"], row["judge_reply"] = judge(judge_llm, result)
        rows.append(row)
    return summarize(rows), rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def rate(items: list[dict[str, Any]], key: str) -> float:
        return round(sum(bool(r[key]) for r in items) / len(items), 3) if items else 0.0

    answerable = [r for r in rows if r["answerable"]]
    unanswerable = [r for r in rows if not r["answerable"]]
    total_citations = sum(r["citations"] for r in rows)
    judged = [r["judge_score"] for r in rows if "judge_score" in r]
    return {
        "n": len(rows),
        "route_accuracy": round(sum(r["route"] == r["route_expected"] for r in rows) / len(rows), 3)
        if rows
        else 0.0,
        "correct_abstention_rate": rate(unanswerable, "abstained"),
        "false_abstention_rate": rate(answerable, "abstained"),
        "grounded_flag_rate": rate(answerable, "grounded_flag"),
        "cites_ground_truth_rate": rate(answerable, "cites_ground_truth"),
        "citation_validity": round(sum(r["valid_citations"] for r in rows) / total_citations, 3)
        if total_citations
        else 0.0,
        "judge_groundedness": round(sum(judged) / len(judged), 3) if judged else None,
        "p50_latency_ms": percentile([r["latency_ms"] for r in rows], 50),
    }


def to_markdown(metrics: dict[str, Any]) -> str:
    lines = ["| Metric | Value |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in metrics.items()]
    return "\n".join(lines) + "\n"
```


<!-- file: src/codeqa/cli/eval_generation.py -->
**`src/codeqa/cli/eval_generation.py`**

```python
from pathlib import Path
from typing import Annotated

import typer

from codeqa.cli.app import console, eval_app


@eval_app.command("generation")
def eval_generation(
    dataset: Path = Path("eval/datasets/dev_questions.yaml"),
    out: Path = Path("eval/results"),
    judge: Annotated[bool, typer.Option(help="Use the LLM as a groundedness judge")] = True,
    record: bool = True,
) -> None:
    """Ask every question end to end; score abstention, citations and groundedness."""

    from codeqa.config import get_settings
    from codeqa.container import get_query_service
    from codeqa.evaluation import generation
    from codeqa.evaluation.dataset import load_dataset
    from codeqa.evaluation.runs import save_results
    from codeqa.graph.llm import get_llm
    from codeqa.services.repos import load_repo_context

    data = load_dataset(dataset)
    repo_root = Path(load_repo_context(None, data.repo).local_path)
    metrics, rows = generation.run_generation_eval(
        data, repo_root, get_query_service(), get_llm() if judge else None
    )
    markdown = generation.to_markdown(metrics)
    settings = get_settings()
    config = {
        "llm": settings.llm_provider,
        "model": settings.llm_model,
        "reranker": settings.reranker_enabled,
        "threshold": settings.evidence_threshold,
        "prompt_version": settings.prompt_version,
    }
    path = save_results(
        out, "generation", str(dataset), config, metrics, rows, markdown, record=record
    )
    console.print(markdown)
    console.print(f"[dim]saved {path}[/dim]")
```


The final `cli/main.py`:

<!-- file: src/codeqa/cli/main.py -->
**`src/codeqa/cli/main.py`**

```python
from rich.markup import escape

# Importing a command module registers its commands on `app` (decorators run on import).
from codeqa.cli import (  # noqa: F401
    ask,
    chunk,
    eval_calibrate,
    eval_generation,
    eval_retrieval,
    eval_routing,
    index,
    search,
)
from codeqa.cli.app import app, console
from codeqa.errors import CodeQAError


def main() -> None:
    try:
        app()
    except CodeQAError as exc:
        console.print(f"[red]Error:[/red] {escape(exc.message)}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
```


<!-- file: tests/unit/test_generation_eval.py -->
**`tests/unit/test_generation_eval.py`**

```python
from codeqa.evaluation.generation import citation_is_valid, summarize
from codeqa.graph.state import Citation
from tests.conftest import SAMPLE_REPO


def _citation(label: str, start: int, end: int) -> Citation:
    return Citation(
        index=1,
        chunk_id=None,
        path="shop/retry.py",
        start_line=start,
        end_line=end,
        label=label,
        permalink=None,
    )


def test_citation_validity_checks_lines_and_symbol() -> None:
    assert citation_is_valid(_citation("RetryPolicy._backoff", 14, 16), SAMPLE_REPO)
    assert not citation_is_valid(_citation("RetryPolicy._backoff", 1, 3), SAMPLE_REPO)
    assert not citation_is_valid(_citation("RetryPolicy._backoff", 14, 999), SAMPLE_REPO)


def test_summary_separates_answerable_and_unanswerable() -> None:
    base = {
        "route": "code_search",
        "route_expected": "code_search",
        "grounded_flag": True,
        "citations": 1,
        "valid_citations": 1,
        "cites_ground_truth": True,
        "latency_ms": 10.0,
    }
    rows = [
        {**base, "answerable": True, "abstained": False},
        {**base, "answerable": True, "abstained": True},
        {**base, "answerable": False, "abstained": True},
    ]
    summary = summarize(rows)
    assert summary["false_abstention_rate"] == 0.5
    assert summary["correct_abstention_rate"] == 1.0
```


**Check:** `make lint && make test` (82 passed).

### Step 9.2: Run the generation evaluation on the dev repo

```bash
make eval-generation
```

This makes one LLM call per question plus one judge call per answered question. On a free
tier, watch the rate limits: run it once, not in a loop, and keep the JSON. Open the JSON in
`eval/results/` and read at least 10 answers with their judge verdicts. Record your
agreement rate with the judge.

### Step 9.3: The held-out repository (touch it exactly once)

1. Clone the held-out repo, pin its commit, index it:
   ```bash
   git clone https://github.com/<org>/<heldout> /tmp/heldout
   git -C /tmp/heldout rev-parse HEAD
   uv run codeqa index /tmp/heldout -n heldout
   ```
2. Write ~20 questions in `eval/datasets/heldout_questions.yaml` (same format, `repo:
   heldout`), labelled by hand as before.
3. Create `eval/configs/heldout.yaml` containing **only your winning configuration**:
   ```yaml
   dataset: eval/datasets/heldout_questions.yaml
   configs:
     - {name: "winning config", repo: heldout, mode: hybrid, rerank: false}
   ```
4. Run it **once**:
   ```bash
   uv run codeqa eval retrieval --config eval/configs/heldout.yaml
   uv run codeqa eval generation --dataset eval/datasets/heldout_questions.yaml
   ```
5. Compare dev vs held-out. A drop is normal (you tuned on dev) and worth explaining.
   Hiding it is not. Do not go back and tune on the held-out results.

### Step 9.4: `docs/evaluation.md`

Use this skeleton. Fill every `...` with real numbers from `eval/results/`.

````markdown
# Evaluation

## Method
- Dev repo: <name> @ <commit>, <N> hand-labelled questions (<mix by type>).
- Held-out repo: <name> @ <commit>, <N> questions, evaluated once with the winning config.
- Retrieval metrics: Recall@5/10, MRR, nDCG@10; a result matches if it has the same
  qualified name or covers >= 50% of the ground-truth symbol's lines.
- Generation metrics: abstention, citation validity, LLM-judge groundedness
  (judge: <model>; I agreed with <x>/<n> hand-checked verdicts).

## Retrieval results (dev)
<paste eval/results/retrieval-latest.md>

## Reranker decision
<before/after table incl. latency, threshold sweep, decision>

## Generation results
<paste eval/results/generation-latest.md>

## Dev vs held-out
| Metric | Dev | Held-out |
|---|---|---|

## What didn't work
1. <finding + number> (e.g. "The reranker lowered Recall@5 on conceptual questions by ...")
2. <finding + number>
3. <finding + number>

## Limitations
- Call graph is name-based, not type-based; ambiguous names stay unresolved.
- Python only. ...
````

### Step 9.5: Architecture Decision Records (`docs/adr/`)

One short file per big decision. Suggested list: `0001-ast-chunking.md`,
`0002-qdrant.md`, `0003-rrf-fusion.md`, `0004-reranker-and-gate.md`,
`0005-rule-router.md`, `0006-postgres-source-of-truth.md`. Template:

````markdown
# 0001. AST-based chunking with tree-sitter

- Status: accepted
- Date: 2026-10-01

## Context
Code must be split into retrievable units. Fixed windows cut functions in half.

## Options
1. Fixed-size windows: trivial; breaks functions.
2. Regex splitting on `def`/`class`: breaks on decorators and nesting.
3. AST (tree-sitter): complete semantic units with names; more code.

## Decision
Option 3, keeping option 1 as the evaluation baseline.

## Consequences
+ Chunks are whole functions/methods with metadata (names, lines, docstrings).
+ Measured: AST + dense Recall@5 = ... vs fixed + dense = ... (eval/results/...).
- More code to maintain; one chunker per language.
````

### Step 9.6: The README

The README is the deliverable most reviewers actually read. Structure (from the plan's
section 12), with the evidence first:

````markdown
# CodeQA

Ask questions about any Python repo and get answers with exact `file:line` citations.
Hybrid search (BM25 + embeddings, fused with RRF) over AST-aware code chunks.

![demo](docs/images/demo.gif)

## Results
<the main retrieval table + one sentence per question type>

## Quickstart
```bash
git clone https://github.com/<you>/codeqa && cd codeqa
cp .env.example .env            # add GROQ_API_KEY (or use LLM_PROVIDER=ollama)
docker compose up -d --build    # UI: http://localhost:8501  API: http://localhost:8000/docs
```

## How it works
<architecture diagram> <LangGraph diagram (mermaid)>

## Key engineering decisions
- AST chunking with tree-sitter ([ADR 0001](docs/adr/0001-ast-chunking.md))
- ... (five bullets, each linking to an ADR)

## Evaluation
<method in 3 lines, dataset size, held-out result> - details in docs/evaluation.md

## What didn't work
<three findings with numbers>

## Limitations and next steps
<cross-file resolution, single language, ...>
````

**Demo GIF (60 to 90 seconds):** index a repo, ask a conceptual question, show the
citations, click a permalink. Record the terminal with `asciinema` + `agg`, or the browser
with any screen recorder, and keep it under ~10 MB.

### Phase 9: Definition of Done

- Every claim in the README is backed by a number in `eval/results/`.
- The "What didn't work" section has at least three real findings.
- Held-out numbers are reported next to dev numbers.

**You have finished the project.** Tag the release:

```bash
git tag -a v1.0.0 -m "CodeQA v1" && git push --tags
```


---

## Appendix A. Final file tree

Files you create or change in this guide, with the phase that introduces them (a later
phase number in brackets means the file is replaced again there).

```
.dockerignore                                                            phase 8
.env.example                                                             phase 0
.github/workflows/ci.yml                                                 phase 0 [8]
.gitignore                                                               phase 0
Dockerfile                                                               phase 8
Makefile                                                                 phase 0
docker-compose.yml                                                       phase 0 [8]
eval/configs/retrieval.yaml                                              phase 4
migrations/versions/9b1e2f3a4c5d_add_edges_logs_feedback_eval_runs.py    phase 0
pyproject.toml                                                           phase 0
src/codeqa/__init__.py                                                   phase 0
src/codeqa/api/__init__.py                                               phase 7
src/codeqa/api/deps.py                                                   phase 7
src/codeqa/api/main.py                                                   phase 7
src/codeqa/api/routes/__init__.py                                        phase 7
src/codeqa/api/routes/feedback.py                                        phase 7
src/codeqa/api/routes/health.py                                          phase 7
src/codeqa/api/routes/query.py                                           phase 7
src/codeqa/api/routes/repositories.py                                    phase 7
src/codeqa/api/routes/search.py                                          phase 7
src/codeqa/api/schemas.py                                                phase 7
src/codeqa/cli/__init__.py                                               phase 1
src/codeqa/cli/app.py                                                    phase 1
src/codeqa/cli/ask.py                                                    phase 6
src/codeqa/cli/chunk.py                                                  phase 1
src/codeqa/cli/eval_calibrate.py                                         phase 5
src/codeqa/cli/eval_generation.py                                        phase 9
src/codeqa/cli/eval_retrieval.py                                         phase 4
src/codeqa/cli/eval_routing.py                                           phase 6
src/codeqa/cli/index.py                                                  phase 2
src/codeqa/cli/main.py                                                   phase 1 [2, 3, 4, 5, 6, 9]
src/codeqa/cli/search.py                                                 phase 3
src/codeqa/config.py                                                     phase 0
src/codeqa/container.py                                                  phase 2 [3, 6]
src/codeqa/db/repositories.py                                            phase 2
src/codeqa/db/session.py                                                 phase 0
src/codeqa/errors.py                                                     phase 0
src/codeqa/evaluation/__init__.py                                        phase 4
src/codeqa/evaluation/calibrate.py                                       phase 5
src/codeqa/evaluation/dataset.py                                         phase 4
src/codeqa/evaluation/generation.py                                      phase 9
src/codeqa/evaluation/metrics.py                                         phase 4
src/codeqa/evaluation/retrieval.py                                       phase 4
src/codeqa/evaluation/routing.py                                         phase 6
src/codeqa/evaluation/runs.py                                            phase 4
src/codeqa/graph/__init__.py                                             phase 6
src/codeqa/graph/citations.py                                            phase 6
src/codeqa/graph/context.py                                              phase 6
src/codeqa/graph/llm.py                                                  phase 6
src/codeqa/graph/nodes.py                                                phase 6
src/codeqa/graph/pipeline.py                                             phase 6
src/codeqa/graph/prompts/__init__.py                                     phase 6
src/codeqa/graph/prompts/answer_v1.md                                    phase 6
src/codeqa/graph/prompts/judge_v1.md                                     phase 9
src/codeqa/graph/prompts/rewrite_v1.md                                   phase 6
src/codeqa/graph/router.py                                               phase 6
src/codeqa/graph/state.py                                                phase 6
src/codeqa/ingest/__init__.py                                            phase 1
src/codeqa/ingest/chunkers/__init__.py                                   phase 1
src/codeqa/ingest/chunkers/base.py                                       phase 1
src/codeqa/ingest/chunkers/fixed.py                                      phase 1
src/codeqa/ingest/chunkers/markdown.py                                   phase 1
src/codeqa/ingest/chunkers/python_ast.py                                 phase 1
src/codeqa/ingest/edges.py                                               phase 1
src/codeqa/ingest/ids.py                                                 phase 1
src/codeqa/ingest/pipeline.py                                            phase 2
src/codeqa/ingest/source.py                                              phase 1
src/codeqa/ingest/walker.py                                              phase 1
src/codeqa/logging.py                                                    phase 0
src/codeqa/models/__init__.py                                            phase 0
src/codeqa/models/base.py                                                phase 0
src/codeqa/models/chunk.py                                               phase 0
src/codeqa/models/eval_run.py                                            phase 0
src/codeqa/models/feedback.py                                            phase 0
src/codeqa/models/file.py                                                phase 0
src/codeqa/models/index_job.py                                           phase 0
src/codeqa/models/query_log.py                                           phase 0
src/codeqa/models/repository.py                                          phase 0
src/codeqa/models/symbol_edge.py                                         phase 0
src/codeqa/retrieval/__init__.py                                         phase 2
src/codeqa/retrieval/embedder.py                                         phase 2
src/codeqa/retrieval/fusion.py                                           phase 2
src/codeqa/retrieval/reranker.py                                         phase 4
src/codeqa/retrieval/search.py                                           phase 3
src/codeqa/retrieval/sparse.py                                           phase 2
src/codeqa/retrieval/store.py                                            phase 2
src/codeqa/retrieval/texts.py                                            phase 2
src/codeqa/services/__init__.py                                          phase 3
src/codeqa/services/query_service.py                                     phase 6
src/codeqa/services/repos.py                                             phase 3
src/codeqa/ui/__init__.py                                                phase 7
src/codeqa/ui/app.py                                                     phase 7
tests/__init__.py                                                        phase 2
tests/conftest.py                                                        phase 2 [3]
tests/fixtures/eval/shop_questions.yaml                                  phase 4
tests/fixtures/sample_code/nested.py                                     phase 1
tests/fixtures/sample_repo/README.md                                     phase 1
tests/fixtures/sample_repo/shop/__init__.py                              phase 1
tests/fixtures/sample_repo/shop/client.py                                phase 1
tests/fixtures/sample_repo/shop/retry.py                                 phase 1
tests/fixtures/sample_repo/shop/users.py                                 phase 1
tests/integration/__init__.py                                            phase 2
tests/integration/test_api.py                                            phase 7
tests/integration/test_indexing_pipeline.py                              phase 2
tests/integration/test_query_graph.py                                    phase 6
tests/integration/test_search.py                                         phase 3
tests/unit/__init__.py                                                   phase 2
tests/unit/test_calibrate.py                                             phase 5
tests/unit/test_citations_and_context.py                                 phase 6
tests/unit/test_edges.py                                                 phase 1
tests/unit/test_eval_metrics.py                                          phase 4
tests/unit/test_fusion.py                                                phase 3
tests/unit/test_generation_eval.py                                       phase 9
tests/unit/test_other_chunkers.py                                        phase 1
tests/unit/test_python_ast_chunker.py                                    phase 1
tests/unit/test_router.py                                                phase 6
tests/unit/test_routing_eval.py                                          phase 6
tests/unit/test_source.py                                                phase 1
tests/unit/test_sparse.py                                                phase 2
tests/unit/test_walker.py                                                phase 1
```

Plus, written by you (not code): `eval/datasets/dev_questions.yaml`,
`eval/datasets/heldout_questions.yaml`, `eval/configs/heldout.yaml`, `eval/results/*`,
`docs/chunking-comparison.md`, `docs/retrieval-observations.md`, `docs/evaluation.md`,
`docs/adr/*.md`, `README.md`, `LICENSE`.

## Appendix B. Command cheat sheet

| Task | Command |
|---|---|
| Install everything | `make install` |
| Start databases | `make up` |
| Apply migrations | `make migrate` |
| New migration after a model change | `uv run alembic revision --autogenerate -m "..."`, then **review it** |
| Check models match migrations | `uv run alembic check` |
| Lint + types / auto-fix | `make lint` / `make format` |
| Tests / coverage | `make test` / `make cov` |
| One test file / one test | `uv run pytest tests/unit/test_router.py` / `uv run pytest -k extract_symbol` |
| Tests against Postgres | `docker compose exec postgres createdb -U codeqa codeqa_test` once, then `TEST_DATABASE_URL=postgresql+psycopg://codeqa:codeqa@localhost:5433/codeqa_test uv run pytest` |
| Inspect chunks | `uv run codeqa chunk path/to/file.py` / `uv run codeqa chunk path/to/folder` |
| Index / re-index | `uv run codeqa index <path-or-url> -n <name>` |
| Index an ablation variant | `... --chunker fixed --collection codeqa_fixed` / `--embedding-model BAAI/bge-small-en-v1.5 --collection codeqa_bge` |
| Repos and jobs | `uv run codeqa status` / `uv run codeqa job <job-id>` |
| Search without LLM | `uv run codeqa search "..." -r <name> --mode hybrid --top-k 10` |
| Ask | `uv run codeqa ask "..." -r <name>` (add `--json` for scripts) |
| Retrieval ablation | `make eval-retrieval` |
| Router accuracy | `uv run codeqa eval routing --dataset eval/datasets/dev_questions.yaml` |
| Calibrate the gate | `make calibrate` |
| Generation eval | `make eval-generation` |
| API / UI (dev) | `make api` / `make ui` |
| Whole stack in Docker | `make stack`, logs with `make logs` |

## Appendix C. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `connection refused` on port 5433 | Postgres not running | `make up`, then `docker compose ps` |
| `password authentication failed` | `.env` differs from the compose file | Use `codeqa`/`codeqa`, or change both |
| `relation "chunks" does not exist` | Migrations not applied | `make migrate` |
| Alembic autogenerate sees nothing | Model not imported in `models/__init__.py` | Import it there |
| `alembic check` fails in CI | You changed a model without a migration | Autogenerate one, review, commit |
| `collection ... has dim 768, model gives 384` | Two models in one collection | Use `--collection <another-name>` for the other model |
| `repository 'x' is not indexed` | Wrong name or indexing failed | `codeqa status`; `codeqa job <id>` shows the error |
| First `codeqa index` seems stuck | The embedding model is downloading (~640 MB) | Wait; it is cached in `.cache/models` afterwards |
| Indexing is very slow | Big repo on CPU with jina-code | Try `BAAI/bge-small-en-v1.5` while iterating; exclude folders via `.gitignore` |
| `GROQ_API_KEY is not set` | Key missing in `.env` | Add it, or `LLM_PROVIDER=ollama` / `fake` |
| Provider error "model not found / decommissioned" | Default model was retired | Set `LLM_MODEL` to a current model name |
| Answers never cite anything | Model ignores the format | Try a stronger model; check the context is not empty (`--json` shows `sources`) |
| Everything abstains | Threshold too high, or reranker scores on a different scale | Re-run `make calibrate`; check `EVIDENCE_THRESHOLD` |
| Qdrant client warns about version mismatch | Server and client minor versions differ | Keep `qdrant/qdrant:vX.Y` in step with `qdrant-client==X.Y.*` |
| `missing separator` from make | Spaces instead of a tab in the Makefile | Indent recipes with a tab |
| mypy: `module is installed, but missing library stubs` | A library without type hints | `ignore_missing_imports = true` is set; for others add a `types-...` package |
| Streamlit shows "Connection refused" | API not running or wrong URL | Start `make api`; in Docker `API_BASE_URL=http://api:8000` |
| UI index form fails for a local path | Path outside `LOCAL_INDEX_ROOT` | In Docker put the repo in `./repos/<name>` and index `/repos/<name>` |

## Appendix D. Concepts glossary

- **AST / CST:** a tree representation of source code. tree-sitter produces a concrete
  syntax tree that keeps every token, which is why byte positions map back to the file.
- **Chunk:** the unit of retrieval. Here: a function, method, class skeleton, module part,
  doc section or fixed window.
- **Embedding (dense vector):** numbers that place text in a space where similar meaning is
  close. Compared with cosine similarity.
- **BM25 (sparse vector):** keyword relevance from term frequency and inverse document
  frequency.
- **IDF:** how rare a term is across all chunks; rare terms matter more.
- **Hybrid search:** combining dense and sparse retrieval.
- **RRF:** fusing ranked lists with `sum 1/(k + rank)`.
- **Bi-encoder vs cross-encoder:** encode separately and compare (fast) vs read the pair
  together (accurate, slow).
- **Evidence gate:** a check on retrieval quality before generating; below the threshold we
  retry once, then abstain.
- **Abstention:** answering "not found" instead of guessing.
- **Grounded answer:** every claim is supported by a cited source.
- **Recall@k, MRR, nDCG:** ranking metrics (Phase 4.0).
- **Ablation:** changing one component at a time to measure its effect.
- **Held-out set:** data never used for tuning, used once to estimate real performance.
- **Idempotent:** running twice gives the same result as running once.
- **Upsert:** insert, or update if the id already exists.
- **Migration:** a versioned, reviewable change to the database schema.
- **Dependency injection:** passing a class its collaborators instead of creating them
  inside, so tests can pass fakes.
- **Protocol:** a Python interface defined by method names and types (structural typing).
- **Reducer (LangGraph):** how a state key that several nodes update is merged.
- **NDJSON:** newline-delimited JSON, one object per line; easy to stream.

## Appendix E. Interview preparation

Short answers you can expand, each tied to something you built and measured:

- **Why AST chunking over recursive splitting?** Chunks are whole functions with names,
  signatures and exact lines, so retrieval returns complete units and citations are
  precise. Evidence: the fixed vs AST rows of your table.
- **Explain RRF.** Walk through the Phase 3.0 example. Ranks, not scores; k = 60; no tuning.
- **When does BM25 beat embeddings?** Exact identifiers and rare tokens; show the
  per-type breakdown.
- **How do you know retrieval is good?** A hand-labelled dataset, Recall@5/MRR/nDCG,
  per-type breakdown, and a held-out repo evaluated once.
- **What is your abstention strategy?** Cross-encoder evidence gate with a calibrated
  threshold, one bounded query rewrite, an exact "not found" answer, and measured
  false/correct abstention rates.
- **Why LangGraph instead of a for-loop?** Branches plus a bounded loop, explicit and
  testable; nodes are plain functions, the framework only wires them.
- **Why Postgres and Qdrant?** Postgres is the source of truth (metadata, call graph, logs,
  eval runs); Qdrant is a rebuildable index for dense + sparse vectors with server-side
  fusion.
- **How would you scale to 100 repos?** One collection with a `repo_id` payload index (as
  now) or collection-per-tenant; a real job queue for indexing; GPU or hosted embeddings;
  caching of query embeddings; horizontal API replicas.
- **What would you do differently?** Pick from your "What didn't work" section.

Practise a two-minute walkthrough: **problem, approach, evidence, limitation.**
