import pytest
from botocore.exceptions import ClientError

from app.core import secrets as secrets_module


def _expired_token_error() -> ClientError:
    return ClientError(
        {
            "Error": {
                "Code": "ExpiredTokenException",
                "Message": "The security token included in the request is expired",
            }
        },
        "GetSecretValue",
    )


def test_optional_aws_secret_load_continues_with_local_env(monkeypatch):
    monkeypatch.setenv("AWS_SECRET_NAME", "dev-mayds-triage-agent")
    monkeypatch.setenv("AWS_REGION", "eu-west-2")
    monkeypatch.setenv("AWS_SECRETS_REQUIRED", "false")
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        secrets_module,
        "get_aws_secret",
        lambda secret_name, region_name: (_ for _ in ()).throw(_expired_token_error()),
    )

    secrets_module.load_aws_secrets_into_env()


def test_required_aws_secret_load_raises_on_expired_token(monkeypatch):
    monkeypatch.setenv("AWS_SECRET_NAME", "dev-mayds-triage-agent")
    monkeypatch.setenv("AWS_REGION", "eu-west-2")
    monkeypatch.setenv("AWS_SECRETS_REQUIRED", "true")
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(
        secrets_module,
        "get_aws_secret",
        lambda secret_name, region_name: (_ for _ in ()).throw(_expired_token_error()),
    )

    with pytest.raises(RuntimeError, match="Failed to load AWS secret"):
        secrets_module.load_aws_secrets_into_env()
