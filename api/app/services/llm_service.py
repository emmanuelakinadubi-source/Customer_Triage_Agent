import openai
from openai import AzureOpenAI
from fastapi import HTTPException
from app.core.config import settings
from app.prompts.system_prompt import SYSTEM_PROMPT_V1, build_user_message
from app.schemas.triage import TriageResponse
from app.services.langfuse_service import langfuse_service
from app.services.rag_service import rag_service

class LLMService:
    def __init__(self):
        self.client = AzureOpenAI(
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY
        )
        self.deployment_name = settings.AZURE_OPENAI_DEPLOYMENT_NAME

    async def extract_triage(self, text_message: str) -> dict:
        retrieved_chunks = rag_service.retrieve(text_message)
        policy_context = "\n\n".join(
            f"Source: {chunk.source}\nSection: {chunk.section}\n{chunk.text.strip()}"
            for chunk in retrieved_chunks
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_V1},
            {"role": "user", "content": build_user_message(text_message, policy_context)}
        ]

        with langfuse_service.observation(
            name="rag-retrieval",
            as_type="retriever",
        ) as retrieval_span:
            retrieval_span.update(
                input=text_message,
                output=[
                    {
                        "section": chunk.section,
                        "source": chunk.source,
                        "score": chunk.score,
                        "text": chunk.text,
                    }
                    for chunk in retrieved_chunks
                ],
                metadata={
                    "top_k": rag_service.top_k,
                    "document_path": rag_service.document_path,
                },
            )

        try:
            with langfuse_service.observation(
                name="azure-openai-triage",
                as_type="generation",
                model=self.deployment_name,
            ) as generation:
                generation.update(
                    input=messages,
                    model_parameters={"temperature": 0.0},
                    metadata={"response_format": "TriageResponse"},
                )
                response = self.client.beta.chat.completions.parse(
                    model=self.deployment_name,
                    messages=messages,
                    temperature=0.0,
                    response_format=TriageResponse
                )
                generation.update(
                    output=response.choices[0].message.parsed.model_dump()
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
