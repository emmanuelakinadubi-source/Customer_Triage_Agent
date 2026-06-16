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

AZURE_OPENAI_SECRET_KEYS = {
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_API_VERSION",
    "AZURE_OPENAI_DEPLOYMENT_NAME",
}


def _is_falsey_env_value(value: str | None) -> bool:
    return value is not None and value.strip().lower() in {"0", "false", "no", "off"}


def _is_truthy_env_value(value: str | None) -> bool:
    return value is not None and value.strip().lower() in {"1", "true", "yes", "on"}


@lru_cache(maxsize=1)
def get_aws_secret(secret_name: str, region_name: str) -> dict:
    client = boto3.client("secretsmanager", region_name=region_name)

    response = client.get_secret_value(SecretId=secret_name)
    secret_string = response.get("SecretString")

    if not secret_string:
        raise RuntimeError(f"Secret {secret_name} has no SecretString value")

    return json.loads(secret_string)


def _set_env_value(key: str, value: Any, *, overwrite: bool) -> None:
    if value is None:
        return

    current_value = os.environ.get(key)
    if current_value and not overwrite:
        return

    os.environ[key] = str(value)


def load_aws_secrets_into_env() -> None:
    secret_name = os.getenv("AWS_SECRET_NAME")
    region_name = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"
    secrets_required = not _is_falsey_env_value(os.getenv("AWS_SECRETS_REQUIRED"))
    overwrite_env = not _is_falsey_env_value(os.getenv("AWS_SECRETS_OVERRIDE_ENV"))

    if all(os.getenv(key) for key in REQUIRED_SECRET_KEYS):
        if not secret_name or not overwrite_env:
            logger.info("Required Azure OpenAI settings already present; skipping AWS Secrets Manager")
            return

    if not secret_name:
        logger.info("AWS_SECRET_NAME not set; using local environment/.env values")
        return

    try:
        secrets = get_aws_secret(secret_name, region_name)
    except (ClientError, BotoCoreError, json.JSONDecodeError) as exc:
        if isinstance(exc, ClientError):
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code == "ExpiredTokenException":
                raise RuntimeError(
                    f"Failed to load AWS secret {secret_name}: AWS credentials are expired. "
                    "Refresh AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_SESSION_TOKEN "
                    "in the project-root .env or in your shell, then restart Docker Compose."
                ) from exc

        if not secrets_required:
            logger.warning(
                "Could not load AWS secret %s from %s; continuing with local environment values: %s",
                secret_name,
                region_name,
                exc,
            )
            return
        raise RuntimeError(f"Failed to load AWS secret {secret_name}: {exc}") from exc

    missing_keys = sorted(REQUIRED_SECRET_KEYS - set(secrets))
    if missing_keys:
        available_keys = ", ".join(sorted(secrets))
        raise RuntimeError(
            f"AWS secret {secret_name} is missing required keys: {', '.join(missing_keys)}. "
            f"Available keys are: {available_keys}"
        )

    for key, value in secrets.items():
        # Azure OpenAI credentials should come from Secrets Manager when configured.
        _set_env_value(
            key,
            value,
            overwrite=overwrite_env and key in AZURE_OPENAI_SECRET_KEYS,
        )

    logger.info(
        "Loaded Azure OpenAI settings from AWS Secrets Manager secret %s in %s",
        secret_name,
        region_name,
    )
