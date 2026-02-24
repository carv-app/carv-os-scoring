from opentelemetry import metrics

from scoring.models import ScoringResult

meter = metrics.get_meter("scoring")

messages_processed = meter.create_counter(
    "scoring.messages.processed",
    description="Number of successfully processed scoring requests",
)

messages_failed = meter.create_counter(
    "scoring.messages.failed",
    description="Number of failed scoring requests",
)

processing_duration = meter.create_histogram(
    "scoring.processing.duration",
    description="End-to-end processing duration in milliseconds",
    unit="ms",
)

llm_duration = meter.create_histogram(
    "scoring.llm.duration",
    description="LLM call duration in milliseconds",
    unit="ms",
)

score_distribution = meter.create_histogram(
    "scoring.score.distribution",
    description="Distribution of candidate scores",
)

active_processings = meter.create_up_down_counter(
    "scoring.active_processings",
    description="Number of concurrent scoring operations",
)


def record_scoring(result: ScoringResult, llm_latency_ms: int) -> None:
    messages_processed.add(1)
    processing_duration.record(result.latency_ms)
    llm_duration.record(llm_latency_ms)
    score_distribution.record(result.score)


def record_failure(error_type: str) -> None:
    messages_failed.add(1, {"error_type": error_type})
