import json
import logging
import os
from functools import lru_cache
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)

REQUIRED_SECRET_KEYS = {
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
}


@lru_cache(maxsize=1)
def get_aws_secret(secret_name: str, region_name: str) -> dict:
    client = boto3.client("secretsmanager", region_name=region_name)

    response = client.get_secret_value(SecretId=secret_name)
    secret_string = response.get("SecretString")

    if not secret_string:
        raise RuntimeError(f"Secret {secret_name} has no SecretString value")

    return json.loads(secret_string)


def _set_env_if_missing_or_empty(key: str, value: Any) -> None:
    if value is None:
        return

    current_value = os.environ.get(key)
    if current_value:
        return

    os.environ[key] = str(value)


def load_aws_secrets_into_env() -> None:
    secret_name = os.getenv("AWS_SECRET_NAME")
    region_name = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"

    if all(os.getenv(key) for key in REQUIRED_SECRET_KEYS):
        logger.info("Required Azure OpenAI settings already present; skipping AWS Secrets Manager")
        return

    if not secret_name:
        logger.info("AWS_SECRET_NAME not set; using local environment/.env values")
        return

    try:
        secrets = get_aws_secret(secret_name, region_name)
    except (ClientError, BotoCoreError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Failed to load AWS secret {secret_name}: {exc}") from exc

    missing_keys = sorted(REQUIRED_SECRET_KEYS - set(secrets))
    if missing_keys:
        available_keys = ", ".join(sorted(secrets))
        raise RuntimeError(
            f"AWS secret {secret_name} is missing required keys: {', '.join(missing_keys)}. "
            f"Available keys are: {available_keys}"
        )

    for key, value in secrets.items():
        # Existing non-empty environment variables win over Secrets Manager.
        _set_env_if_missing_or_empty(key, value)

    logger.info(
        "Loaded application secrets from AWS Secrets Manager secret %s in %s",
        secret_name,
        region_name,
    )
