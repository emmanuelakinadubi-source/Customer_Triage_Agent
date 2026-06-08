import openai
from openai import AzureOpenAI
from fastapi import HTTPException
from app.core.config import settings
from app.prompts.system_prompt import SYSTEM_PROMPT_V1, build_user_message
from app.schemas.triage import TriageResponse

class LLMService:
    def __init__(self):
        self.client = AzureOpenAI(
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY
        )
        self.deployment_name = settings.AZURE_OPENAI_DEPLOYMENT_NAME

    async def extract_triage(self, text_message: str) -> dict:
        try:
            response = self.client.beta.chat.completions.parse(
                model=self.deployment_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT_V1},
                    {"role": "user", "content": build_user_message(text_message)}
                ],
                temperature=0.0,
                response_format=TriageResponse
            )
        except openai.APIConnectionError as exc:
            raise HTTPException(status_code=503, detail=f"Cannot reach Azure OpenAI endpoint: {exc}") from exc
        except openai.AuthenticationError as exc:
            raise HTTPException(status_code=502, detail=f"Azure OpenAI authentication failed — check AZURE_OPENAI_API_KEY") from exc
        except openai.RateLimitError as exc:
            raise HTTPException(status_code=429, detail=f"Azure OpenAI rate limit exceeded") from exc
        except openai.APIStatusError as exc:
            raise HTTPException(status_code=502, detail=f"Azure OpenAI returned {exc.status_code}: {exc.message}") from exc

        choice = response.choices[0].message
        if choice.refusal:
            raise HTTPException(status_code=422, detail=f"LLM refused to process this message: {choice.refusal}")

        parsed = choice.parsed
        print(f"LLM Parsed Output: {parsed}")
        return parsed.model_dump()

llm_service = LLMService()