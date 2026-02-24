# Candidate Scoring Service

Scores job candidates against vacancy descriptions using Google Gemini. Candidates arrive via Pub/Sub events from the Carv event bus, are processed by Cloud Run, and results are stored in Firestore.

## Architecture

```
carv-ats publishes
  uats.application.created
        │
        ▼
  [Pub/Sub topic]  ──push──▶  [Cloud Run: scoring-worker]
                                       │
                          ┌────────────┼───────────────┐
                          ▼            ▼               ▼
                     [Firestore]   [Gemini API]   [Cloud Trace +
                     read/write    score call      Monitoring]
                          │
                          ▼
                    [Pub/Sub: carv.score.calculated]  ──▶  CarvOS (ATS egress)

On failure: HTTP 500 → Pub/Sub retries (exponential backoff 10s → 600s)
After 5 failures: auto-routes to scoring-dlq topic
```

### Event Bus Integration

This service participates in the Carv event bus (see `event-bus-events.mdx`):

| Direction | Event | Description |
|-----------|-------|-------------|
| **Subscribe** | `uats.application.created` | Triggers scoring when a candidate applies for a vacancy |
| **Publish** | `carv.score.calculated` | Score computed successfully |
| **Publish** | `carv.score.failed` | Scoring permanently failed |

### Data Flow

The Pub/Sub message carries a UATS event envelope with an array of applications. Each application contains only reference IDs — no PII travels through the event bus. The service fetches full candidate, vacancy, and document data from workspace-scoped Firestore collections at processing time.

```json
{
  "eventName": "uats.application.created",
  "workspaceId": "JSiKKjiSDmZoX7Zfk2qG",
  "integrationId": "TFVrXu0yLFyTMWkUztsw",
  "timestamp": "2026-01-27T13:52:56Z",
  "data": [
    {
      "id": "1910930",
      "candidateReferenceId": "aUFe1f8g84GGORCL",
      "vacancyReferenceId": "aIil3cRwkMsuC-pC",
      "status": "05. Interview",
      "workspaceId": "JSiKKjiSDmZoX7Zfk2qG"
    }
  ]
}
```

### Firestore Data Model

Data lives in workspace-scoped collections matching the Carv platform ATS model. All documents use camelCase field names.

| Data | Firestore Path |
|------|----------------|
| Candidate | `/Workspaces/{workspaceId}/Candidates/{candidateReferenceId}` |
| Vacancy | `/Workspaces/{workspaceId}/ATSVacancies/{vacancyReferenceId}` |
| ATS Documents | `/Workspaces/{workspaceId}/Candidate/{candidateReferenceId}/AtsDocuments` |
| Scoring Results | `scoring_results` (flat collection, auto-generated IDs) |

The scoring flow fetches candidate, vacancy, and ATS documents (resume, job description, assessment) in parallel via `asyncio.gather`, then passes everything to Gemini for scoring.

## Project Structure

```
src/scoring/
├── main.py                    # FastAPI app, lifespan (init clients)
├── config.py                  # pydantic-settings: all env vars
├── models.py                  # Pydantic models (events, ATS models, results)
├── api/
│   ├── routes.py              # POST /process-candidate, GET /health
│   └── dependencies.py        # FastAPI Depends factories
├── services/
│   ├── scoring.py             # Orchestrator: fetch → prompt → LLM → store → publish
│   ├── llm.py                 # Gemini client (google-genai SDK)
│   ├── prompt.py              # Prompt templates for scoring
│   └── publisher.py           # Pub/Sub publisher for score events
├── repositories/
│   └── firestore.py           # get_candidate, get_vacancy, get_ats_documents, save_result
└── observability/
    ├── setup.py               # OTel SDK init (tracer, meter, GCP exporters)
    └── metrics.py             # Custom metric definitions

scripts/
├── test_local.py              # Test locally (hardcoded, from Firestore, or explicit IDs)
├── seed_firestore.py          # Seed sample data into workspace-scoped paths
└── publish_test_message.py    # Publish test event to real Pub/Sub topic
```

## Prerequisites

- Python 3.11+
- A GCP project with billing enabled
- `gcloud` CLI installed and authenticated
- Terraform >= 1.5
- Docker (for building container images)

## Local Development

### Install dependencies

```bash
pip install -e ".[dev]"
```

### Configure environment

```bash
cp .env.example .env
# Edit .env with your values (defaults point to carv-app-dev)
```

The `.env` file is loaded automatically by pydantic-settings. Environment variables always override `.env` values, so you can still use inline env vars or export them in your shell.

### Start the Pub/Sub emulator

The Pub/Sub emulator avoids 500 errors when publishing score events locally. Topics are auto-created on startup.

```bash
# Install components (one-time)
gcloud components install beta pubsub-emulator

# Start the emulator (leave running in a separate terminal)
gcloud beta emulators pubsub start --host-port=localhost:8085
```

### Run the scoring service

```bash
# With Pub/Sub emulator (recommended — full end-to-end, no publish errors)
PUBSUB_EMULATOR_HOST=localhost:8085 uvicorn scoring.main:app --port 8080

# Without emulator (publish step will fail with 404, but scoring still works)
uvicorn scoring.main:app --port 8080
```

Config is read from `.env`. Override any value with an env var on the command line.

### Test locally

Three ways to send a test event to the running service:

```bash
# 1. Hardcoded fake data (needs Firestore seeded first)
python scripts/test_local.py

# 2. From a real Firestore application (reads candidate/vacancy refs automatically)
python scripts/test_local.py --application JSiKKjiSDmZoX7Zfk2qG/1910930

# 3. From explicit IDs
python scripts/test_local.py \
  --workspace JSiKKjiSDmZoX7Zfk2qG \
  --candidate aUFe1f8g84GGORCL \
  --vacancy aIil3cRwkMsuC-pC
```

### Seed sample data

```bash
python scripts/seed_firestore.py carv-app-dev
```

Seeds workspace-scoped documents at `/Workspaces/workspace-001/Candidates/candidate-001`, `/Workspaces/workspace-001/ATSVacancies/vacancy-001`, and ATS documents.

### Run tests

```bash
pytest tests/ -v                        # all tests
pytest tests/unit/ -v                   # unit only
pytest tests/integration/ -v            # integration only
```

### Lint

```bash
ruff check src/ tests/
ruff check --fix src/ tests/
```

## Deployment

### 1. Provision infrastructure with Terraform

```bash
cd terraform

# Create a GCS bucket for Terraform state (one-time)
gcloud storage buckets create gs://carv-os-scoring-tfstate \
  --location=europe-west1 \
  --project=your-project-id

# Configure variables
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars:
#   project_id    = "your-project-id"
#   region        = "europe-west1"
#   scoring_image = "europe-west1-docker.pkg.dev/your-project-id/scoring/scoring-worker:latest"

terraform init
terraform plan
terraform apply
```

This creates:

| Resource | Purpose |
|----------|---------|
| **Pub/Sub topics** | `uats.application.created` (input), `carv.score.calculated` / `carv.score.failed` (output), `scoring-dlq` (dead letter) |
| **Pub/Sub subscription** | `scoring-worker-push` — pushes to Cloud Run with OIDC auth, retry backoff 10s-600s, DLQ after 5 attempts |
| **Cloud Run** | `scoring-worker` — 2 CPU, 1Gi memory, 1-20 instances, concurrency 10, 300s timeout |
| **Firestore** | Native mode database with composite indexes on `scoring_results` |
| **Artifact Registry** | Docker repository for container images |
| **IAM** | `scoring-service` SA (Firestore, Trace, Monitoring, Vertex AI, Pub/Sub publisher), `pubsub-invoker` SA (Cloud Run invoker) |
| **Monitoring** | Alert on DLQ messages > 0 for 5 min, error rate > 10% for 5 min |

### 2. Build and push the container image

```bash
PROJECT_ID=your-project-id
REGION=europe-west1
REPO=$REGION-docker.pkg.dev/$PROJECT_ID/scoring

gcloud auth configure-docker $REGION-docker.pkg.dev

docker build -t $REPO/scoring-worker:latest .
docker push $REPO/scoring-worker:latest
```

### 3. Deploy Cloud Run

After pushing a new image, Cloud Run picks it up if using `:latest`. To force a new revision:

```bash
gcloud run services update scoring-worker \
  --region=$REGION \
  --image=$REPO/scoring-worker:latest
```

### 4. Trigger a test scoring via Pub/Sub

```bash
python scripts/publish_test_message.py carv-app-dev aUFe1f8g84GGORCL aIil3cRwkMsuC-pC JSiKKjiSDmZoX7Zfk2qG
```

### 5. Verify results

```bash
# Check Cloud Run logs
gcloud run services logs read scoring-worker --region=europe-west1 --limit=20
```

## Configuration

All configuration is via environment variables, managed by pydantic-settings in `config.py`. Values are loaded from `.env` (see `.env.example`), and can always be overridden by setting the env var directly.

| Variable | Default | Description |
|----------|---------|-------------|
| `GCP_PROJECT_ID` | *required* | GCP project ID |
| `GCP_REGION` | `europe-west1` | GCP region |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model name |
| `GEMINI_TEMPERATURE` | `0.1` | LLM temperature (low for consistent scoring) |
| `GEMINI_MAX_TOKENS` | `16384` | Max output tokens |
| `SCORING_RESULTS_COLLECTION` | `scoring_results` | Firestore collection for results |
| `SCORE_CALCULATED_TOPIC` | `carv.score.calculated` | Pub/Sub topic for score events |
| `SCORE_FAILED_TOPIC` | `carv.score.failed` | Pub/Sub topic for failed scores |
| `OTEL_ENABLED` | `true` | Enable OpenTelemetry (disable locally) |
| `PUBSUB_EMULATOR_HOST` | — | Set to `localhost:8085` to use the Pub/Sub emulator |

## Retry and Dead-Letter Strategy

The service uses **native Pub/Sub retry + DLQ** — no custom retry code in the application:

1. On success: return HTTP 200 (Pub/Sub acks the message)
2. On failure: return HTTP 500 (Pub/Sub nacks and retries)
3. Pub/Sub retries with exponential backoff: 10s → 20s → 40s → ... → 600s max
4. After 5 failed delivery attempts: message auto-routes to `scoring-dlq`
5. Malformed messages (bad JSON, missing fields): return HTTP 200 to avoid infinite retries

## Observability

### Traces (Cloud Trace)

Every request generates a trace with spans for each processing stage:

- `scoring.process` — end-to-end orchestration
- `firestore.get_candidate` — Firestore read
- `firestore.get_vacancy` — Firestore read
- `firestore.get_ats_documents` — Firestore read
- `llm.score` — Gemini API call (includes `llm.model` and `llm.tokens.total` attributes)
- `firestore.save_result` — Firestore write
- `publisher.score_calculated` — Pub/Sub publish

FastAPI request spans are auto-instrumented via `opentelemetry-instrumentation-fastapi`.

### Metrics (Cloud Monitoring)

| Metric | Type | Description |
|--------|------|-------------|
| `scoring.messages.processed` | Counter | Successful scorings |
| `scoring.messages.failed` | Counter (label: `error_type`) | Failed attempts |
| `scoring.processing.duration` | Histogram (ms) | End-to-end processing time |
| `scoring.llm.duration` | Histogram (ms) | Gemini API call time |
| `scoring.score.distribution` | Histogram | Score values (0-100) |
| `scoring.active_processings` | UpDownCounter | Concurrent operations gauge |

### Alerts

Terraform provisions two alert policies:

1. **DLQ Undelivered Messages** — fires when `scoring-dlq-pull` has undelivered messages for 5+ minutes
2. **High Error Rate** — fires when Cloud Run 5xx rate exceeds 10% for 5+ minutes

## Terraform Details

### Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `project_id` | Yes | — | GCP project ID |
| `region` | No | `europe-west1` | GCP region |
| `scoring_image` | Yes | — | Full container image path |
| `alert_notification_channel` | No | `""` | Notification channel ID for monitoring alerts |

### Service Accounts

| Account | Roles | Purpose |
|---------|-------|---------|
| `scoring-service` | `datastore.user`, `cloudtrace.agent`, `monitoring.metricWriter`, `aiplatform.user`, `pubsub.publisher` (on score topics) | Cloud Run service identity |
| `pubsub-invoker` | `run.invoker` | OIDC auth for Pub/Sub push to Cloud Run |

### Cloud Run Scaling

| Setting | Value | Rationale |
|---------|-------|-----------|
| Min instances | 1 | Avoid cold starts |
| Max instances | 20 | Up to 200 concurrent candidates (20 x 10) |
| Concurrency | 10 | I/O-bound (Firestore + Gemini API), async handles well |
| Timeout | 300s | Gemini calls take 10-30s, plenty of headroom |
| CPU | 2 | Enough for async concurrency |
| Memory | 1Gi | Mostly I/O, moderate footprint |
| CPU idle | false | Always-on for OTel background export |
