import openai
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import AzureChatOpenAI
from openai import AzureOpenAI
from fastapi import HTTPException
from app.core.config import settings
from app.prompts.system_prompt import SYSTEM_PROMPT_V1, build_user_message
from app.schemas.triage import TriageResponse
from app.services.langfuse_service import langfuse_service
from app.services.rag_service import rag_service
from app.services.ragas_service import RAGAS_CONTEXTS_KEY

class LLMService:
    def __init__(self):
        self.client = AzureOpenAI(
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY
        )
        self.deployment_name = settings.AZURE_OPENAI_DEPLOYMENT_NAME
        self.chat_model = AzureChatOpenAI(
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            azure_deployment=self.deployment_name,
            temperature=0.0,
        )
        self.triage_chain = self.chat_model.with_structured_output(TriageResponse)

    async def extract_triage(self, text_message: str) -> dict:
        retrieved_chunks = rag_service.retrieve(text_message)
        retrieved_contexts = [
            f"Source: {chunk.source}\nSection: {chunk.section}\n{chunk.text.strip()}"
            for chunk in retrieved_chunks
        ]
        policy_context = "\n\n".join(retrieved_contexts)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT_V1},
            {"role": "user", "content": build_user_message(text_message, policy_context)}
        ]
        langchain_messages = [
            SystemMessage(content=messages[0]["content"]),
            HumanMessage(content=messages[1]["content"]),
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
                    "document_paths": rag_service.document_paths,
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
                    metadata={
                        "framework": "langchain",
                        "response_format": "TriageResponse",
                    },
                )
                parsed = await self.triage_chain.ainvoke(langchain_messages)
                generation.update(output=parsed.model_dump())
        except openai.APIConnectionError as exc:
            raise HTTPException(status_code=503, detail=f"Cannot reach Azure OpenAI endpoint: {exc}") from exc
        except openai.AuthenticationError as exc:
            raise HTTPException(status_code=502, detail=f"Azure OpenAI authentication failed — check AZURE_OPENAI_API_KEY") from exc
        except openai.RateLimitError as exc:
            raise HTTPException(status_code=429, detail=f"Azure OpenAI rate limit exceeded") from exc
        except openai.APIStatusError as exc:
            raise HTTPException(status_code=502, detail=f"Azure OpenAI returned {exc.status_code}: {exc.message}") from exc

        print(f"LLM Parsed Output: {parsed}")
        triage_output = parsed.model_dump()
        triage_output[RAGAS_CONTEXTS_KEY] = retrieved_contexts
        return triage_output

llm_service = LLMService()
