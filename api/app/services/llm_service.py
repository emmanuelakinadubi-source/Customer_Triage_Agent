import json
from openai import AzureOpenAI
from app.core.config import settings
from app.prompts.system_prompt import SYSTEM_PROMPT_V1, build_user_message

class LLMService:
    def __init__(self):
        self.client = AzureOpenAI(
            api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY
        )
        self.deployment_name = settings.AZURE_OPENAI_DEPLOYMENT_NAME

    async def extract_triage(self, text_message: str) -> dict:
        response = self.client.chat.completions.create(
            model=self.deployment_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT_V1},
                {"role": "user", "content": build_user_message(text_message)}
            ],
            temperature=0.0,
            response_format={"type": "json_object"}
        )
        
        raw_output = response.choices[0].message.content
        print(f"LLM Raw Output: {raw_output}")
        return json.loads(raw_output)

llm_service = LLMService()