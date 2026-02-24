# Candidate Scoring Service

Scores job candidates against vacancy descriptions using Google Gemini. Candidates arrive via Pub/Sub events from the Carv event bus, are processed in parallel by Cloud Run, and results are stored in Firestore.

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

### Data Flow (Claim Check Pattern)

The Pub/Sub message carries the UATS event envelope with only IDs — no PII travels through the event bus. The service fetches full candidate and vacancy data from Firestore at processing time.

```json
{
  "eventName": "uats.application.created",
  "workspaceId": "workspace-123",
  "integrationId": "integration-456",
  "timestamp": "2025-01-15T10:30:00Z",
  "data": {
    "id": "app-1",
    "candidateId": "candidate-001",
    "vacancyId": "vacancy-001"
  }
}
```

## Project Structure

```
src/scoring/
├── main.py                    # FastAPI app, lifespan (init clients)
├── config.py                  # pydantic-settings: all env vars
├── models.py                  # Pydantic models (events, documents, results)
├── api/
│   ├── routes.py              # POST /process-candidate, GET /health
│   └── dependencies.py        # FastAPI Depends factories
├── services/
│   ├── scoring.py             # Orchestrator: fetch → prompt → LLM → store → publish
│   ├── llm.py                 # Gemini client (google-genai SDK)
│   ├── prompt.py              # Prompt templates for scoring
│   └── publisher.py           # Pub/Sub publisher for score events
├── repositories/
│   └── firestore.py           # get_candidate, get_vacancy, save_result
└── observability/
    ├── setup.py               # OTel SDK init (tracer, meter, GCP exporters)
    └── metrics.py             # Custom metric definitions
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
# Edit .env with your GCP project ID
```

### Run locally

```bash
# Disable OTel for local development (no GCP exporters needed)
OTEL_ENABLED=false GCP_PROJECT_ID=your-project uvicorn scoring.main:app --port 8080
```

### Test with a mock Pub/Sub message

```bash
# Encode a uats.application.created event
DATA=$(echo -n '{"eventName":"uats.application.created","workspaceId":"ws-1","integrationId":"int-1","timestamp":"2025-01-01T00:00:00Z","data":{"id":"app-1","candidateId":"candidate-001","vacancyId":"vacancy-001"}}' | base64)

curl -X POST http://localhost:8080/process-candidate \
  -H "Content-Type: application/json" \
  -d "{\"message\":{\"data\":\"$DATA\",\"messageId\":\"test-1\",\"publishTime\":\"2025-01-01T00:00:00Z\"},\"subscription\":\"projects/test/subscriptions/test\"}"
```

### Run tests

```bash
pytest tests/ -v
```

### Lint

```bash
ruff check src/ tests/
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
# Set variables
PROJECT_ID=your-project-id
REGION=europe-west1
REPO=$REGION-docker.pkg.dev/$PROJECT_ID/scoring

# Authenticate Docker with Artifact Registry
gcloud auth configure-docker $REGION-docker.pkg.dev

# Build and push
docker build -t $REPO/scoring-worker:latest .
docker push $REPO/scoring-worker:latest
```

### 3. Deploy Cloud Run (first time / image update)

After pushing a new image, Cloud Run picks it up if using `:latest`. To force a new revision:

```bash
gcloud run services update scoring-worker \
  --region=$REGION \
  --image=$REPO/scoring-worker:latest
```

### 4. Seed Firestore with sample data

```bash
python scripts/seed_firestore.py your-project-id
```

This loads `sources.json` as `candidates/candidate-001` and `dentist.txt` as `vacancies/vacancy-001`.

### 5. Trigger a test scoring via Pub/Sub

```bash
python scripts/publish_test_message.py your-project-id
# Defaults: candidate-001, vacancy-001, workspace-001
# Custom: python scripts/publish_test_message.py your-project-id cand-123 vac-456 ws-789
```

### 6. Verify results

```bash
# Check Cloud Run logs
gcloud run services logs read scoring-worker --region=$REGION --limit=20

# Check Firestore for scoring results
gcloud firestore documents list scoring_results --project=your-project-id
```

## Terraform Details

### Backend state

State is stored in `gs://carv-os-scoring-tfstate/terraform/state`. Update the bucket name in `terraform/main.tf` if using a different bucket.

### Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `project_id` | Yes | - | GCP project ID |
| `region` | No | `europe-west1` | GCP region |
| `scoring_image` | Yes | - | Full container image path |
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

## Observability

### Traces (Cloud Trace)

Every request generates a trace with spans for each processing stage:

- `scoring.process` — end-to-end orchestration
- `firestore.get_candidate` — Firestore read
- `firestore.get_vacancy` — Firestore read
- `llm.score` — Gemini API call (includes `llm.model` and `llm.tokens.total` attributes)
- `firestore.save_result` — Firestore write
- `publisher.score_calculated` — Pub/Sub publish

FastAPI request spans are auto-instrumented via `opentelemetry-instrumentation-fastapi`.

**View traces:**
```bash
# Open Cloud Trace in the console
gcloud console --open https://console.cloud.google.com/traces/list?project=your-project-id
```

### Metrics (Cloud Monitoring)

#### Custom application metrics

| Metric | Type | Description |
|--------|------|-------------|
| `scoring.messages.processed` | Counter | Successful scorings |
| `scoring.messages.failed` | Counter (label: `error_type`) | Failed attempts |
| `scoring.processing.duration` | Histogram (ms) | End-to-end processing time |
| `scoring.llm.duration` | Histogram (ms) | Gemini API call time |
| `scoring.score.distribution` | Histogram | Score values (0-100) |
| `scoring.active_processings` | UpDownCounter | Concurrent operations gauge |

Custom metrics export to Cloud Monitoring every 60 seconds.

#### Native Pub/Sub metrics (no code needed)

| Metric | Use |
|--------|-----|
| `subscription/num_undelivered_messages` | Queue depth / backlog |
| `subscription/oldest_unacked_message_age` | Processing lag |

These are available in Cloud Monitoring for both the main subscription and the DLQ subscription.

### Alerts

Terraform provisions two alert policies:

1. **DLQ Undelivered Messages** — fires when `scoring-dlq-pull` has undelivered messages for 5+ minutes
2. **High Error Rate** — fires when Cloud Run 5xx rate exceeds 10% for 5+ minutes

To receive notifications, set `alert_notification_channel` in `terraform.tfvars` to an existing notification channel ID (email, Slack, PagerDuty, etc.).

### Dashboards

Create a custom Cloud Monitoring dashboard combining:

- `scoring.processing.duration` (p50, p95, p99) — latency
- `scoring.messages.processed` vs `scoring.messages.failed` — success rate
- `scoring.score.distribution` — score histogram
- `subscription/num_undelivered_messages` on `scoring-worker-push` — queue depth
- `subscription/oldest_unacked_message_age` on `scoring-worker-push` — processing lag
- Cloud Run built-in metrics (instance count, request latency, CPU/memory utilization)

## Firestore Collections

| Collection | Doc ID | Key Fields |
|------------|--------|------------|
| `candidates` | `{candidate_id}` | `name`, `sources[]` (label, content, metadata) |
| `vacancies` | `{vacancy_id}` | `title`, `description` |
| `scoring_results` | auto-generated | `application_id`, `candidate_id`, `vacancy_id`, `workspace_id`, `score`, `reasoning`, `model`, `latency_ms`, `scored_at` |

Composite indexes on `scoring_results`:
- `vacancy_id` ASC + `score` DESC — rank candidates per vacancy
- `candidate_id` ASC + `scored_at` DESC — candidate scoring history

## Configuration

All configuration is via environment variables (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `GCP_PROJECT_ID` | *required* | GCP project ID |
| `GCP_REGION` | `europe-west1` | GCP region |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Gemini model name |
| `GEMINI_TEMPERATURE` | `0.1` | LLM temperature (low for consistent scoring) |
| `GEMINI_MAX_TOKENS` | `1024` | Max output tokens |
| `CANDIDATES_COLLECTION` | `candidates` | Firestore collection for candidates |
| `VACANCIES_COLLECTION` | `vacancies` | Firestore collection for vacancies |
| `SCORING_RESULTS_COLLECTION` | `scoring_results` | Firestore collection for results |
| `SCORE_CALCULATED_TOPIC` | `carv.score.calculated` | Pub/Sub topic for score events |
| `SCORE_FAILED_TOPIC` | `carv.score.failed` | Pub/Sub topic for failed scores |
| `OTEL_ENABLED` | `true` | Enable OpenTelemetry (disable locally) |

## Retry and Dead-Letter Strategy

The service uses **native Pub/Sub retry + DLQ** — no custom retry code in the application:

1. On success: return HTTP 200 (Pub/Sub acks the message)
2. On failure: return HTTP 500 (Pub/Sub nacks and retries)
3. Pub/Sub retries with exponential backoff: 10s → 20s → 40s → ... → 600s max
4. After 5 failed delivery attempts: message auto-routes to `scoring-dlq`
5. Malformed messages (bad JSON, missing fields): return HTTP 200 to avoid infinite retries

This approach is simpler and safer than custom retry logic — Pub/Sub handles backoff, attempt counting, and DLQ routing natively.
