import structlog
from google import genai
from google.genai import types
from opentelemetry import trace

from scoring.config import Settings
from scoring.models import CandidateDocument, LLMScoringResponse, VacancyDocument
from scoring.services.prompt import SYSTEM_PROMPT, build_user_prompt

logger = structlog.get_logger()
tracer = trace.get_tracer(__name__)


class LLMService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = genai.Client(
            vertexai=True,
            project=settings.gcp_project_id,
            location=settings.gcp_region,
        )

    async def score_candidate(
        self, candidate: CandidateDocument, vacancy: VacancyDocument
    ) -> tuple[LLMScoringResponse, dict]:
        with tracer.start_as_current_span("llm.score") as span:
            span.set_attribute("llm.model", self._settings.gemini_model)

            user_prompt = build_user_prompt(candidate, vacancy)

            response = await self._client.aio.models.generate_content(
                model=self._settings.gemini_model,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=self._settings.gemini_temperature,
                    max_output_tokens=self._settings.gemini_max_tokens,
                    response_mime_type="application/json",
                    response_schema=LLMScoringResponse,
                ),
            )

            token_usage = {}
            if response.usage_metadata:
                token_usage = {
                    "prompt_tokens": response.usage_metadata.prompt_token_count,
                    "completion_tokens": response.usage_metadata.candidates_token_count,
                    "total_tokens": response.usage_metadata.total_token_count,
                }
                span.set_attribute("llm.tokens.total", token_usage.get("total_tokens", 0))

            result = LLMScoringResponse.model_validate_json(response.text)

            logger.info(
                "llm_scoring_complete",
                score=result.score,
                tokens=token_usage,
            )

            return result, token_usage
