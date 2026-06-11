import json
import logging
import os
from functools import lru_cache

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_aws_secret(secret_name: str, region_name: str) -> dict:
    client = boto3.client("secretsmanager", region_name=region_name)

    response = client.get_secret_value(SecretId=secret_name)
    secret_string = response.get("SecretString")

    if not secret_string:
        raise RuntimeError(f"Secret {secret_name} has no SecretString value")

    return json.loads(secret_string)


def load_aws_secrets_into_env() -> None:
    secret_name = os.getenv("AWS_SECRET_NAME")
    region_name = os.getenv("AWS_REGION", "us-east-1")

    if not secret_name:
        logger.info("AWS_SECRET_NAME not set; using local environment/.env values")
        return

    try:
        secrets = get_aws_secret(secret_name, region_name)
    except (ClientError, BotoCoreError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Failed to load AWS secret {secret_name}: {exc}") from exc

    for key, value in secrets.items():
        if value is None:
            continue

        # Existing real environment variables win over Secrets Manager.
        os.environ.setdefault(key, str(value))

    logger.info("Loaded application secrets from AWS Secrets Manager")