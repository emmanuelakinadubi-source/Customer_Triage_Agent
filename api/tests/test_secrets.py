import pytest
from botocore.exceptions import ClientError

from app.core import secrets as secrets_module


def _clear_secret_loader_env(monkeypatch):
    for key in [
        "AWS_SECRET_NAME",
        "AWS_REGION",
        "AWS_DEFAULT_REGION",
        "AWS_SECRETS_REQUIRED",
        "AWS_SECRETS_OVERRIDE_ENV",
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_OPENAI_API_VERSION",
        "AZURE_OPENAI_DEPLOYMENT_NAME",
    ]:
        monkeypatch.delenv(key, raising=False)


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


def test_aws_secret_load_sets_azure_openai_env(monkeypatch):
    _clear_secret_loader_env(monkeypatch)
    monkeypatch.setenv("AWS_SECRET_NAME", "dev-mayds-triage-agent")
    monkeypatch.setenv("AWS_REGION", "eu-west-2")
    monkeypatch.setattr(
        secrets_module,
        "get_aws_secret",
        lambda secret_name, region_name: {
            "AZURE_OPENAI_ENDPOINT": "https://secret-resource.openai.azure.com/",
            "AZURE_OPENAI_API_KEY": "secret-api-key",
            "AZURE_OPENAI_API_VERSION": "2025-01-01-preview",
            "AZURE_OPENAI_DEPLOYMENT_NAME": "secret-deployment",
        },
    )

    secrets_module.load_aws_secrets_into_env()

    assert secrets_module.os.environ["AZURE_OPENAI_ENDPOINT"] == "https://secret-resource.openai.azure.com/"
    assert secrets_module.os.environ["AZURE_OPENAI_API_KEY"] == "secret-api-key"
    assert secrets_module.os.environ["AZURE_OPENAI_API_VERSION"] == "2025-01-01-preview"
    assert secrets_module.os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"] == "secret-deployment"


def test_aws_secret_load_overrides_local_azure_openai_env_by_default(monkeypatch):
    _clear_secret_loader_env(monkeypatch)
    monkeypatch.setenv("AWS_SECRET_NAME", "dev-mayds-triage-agent")
    monkeypatch.setenv("AWS_REGION", "eu-west-2")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://local-resource.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "local-api-key")
    monkeypatch.setattr(
        secrets_module,
        "get_aws_secret",
        lambda secret_name, region_name: {
            "AZURE_OPENAI_ENDPOINT": "https://secret-resource.openai.azure.com/",
            "AZURE_OPENAI_API_KEY": "secret-api-key",
        },
    )

    secrets_module.load_aws_secrets_into_env()

    assert secrets_module.os.environ["AZURE_OPENAI_ENDPOINT"] == "https://secret-resource.openai.azure.com/"
    assert secrets_module.os.environ["AZURE_OPENAI_API_KEY"] == "secret-api-key"


def test_aws_secret_load_can_keep_local_azure_openai_env(monkeypatch):
    _clear_secret_loader_env(monkeypatch)
    monkeypatch.setenv("AWS_SECRET_NAME", "dev-mayds-triage-agent")
    monkeypatch.setenv("AWS_REGION", "eu-west-2")
    monkeypatch.setenv("AWS_SECRETS_OVERRIDE_ENV", "false")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://local-resource.openai.azure.com/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "local-api-key")
    monkeypatch.setattr(
        secrets_module,
        "get_aws_secret",
        lambda secret_name, region_name: {
            "AZURE_OPENAI_ENDPOINT": "https://secret-resource.openai.azure.com/",
            "AZURE_OPENAI_API_KEY": "secret-api-key",
        },
    )

    secrets_module.load_aws_secrets_into_env()

    assert secrets_module.os.environ["AZURE_OPENAI_ENDPOINT"] == "https://local-resource.openai.azure.com/"
    assert secrets_module.os.environ["AZURE_OPENAI_API_KEY"] == "local-api-key"


def test_optional_aws_secret_load_continues_with_local_env(monkeypatch):
    _clear_secret_loader_env(monkeypatch)
    monkeypatch.setenv("AWS_SECRET_NAME", "dev-mayds-triage-agent")
    monkeypatch.setenv("AWS_REGION", "eu-west-2")
    monkeypatch.setenv("AWS_SECRETS_REQUIRED", "false")
    monkeypatch.setattr(
        secrets_module,
        "get_aws_secret",
        lambda secret_name, region_name: (_ for _ in ()).throw(_expired_token_error()),
    )

    secrets_module.load_aws_secrets_into_env()


def test_required_aws_secret_load_raises_on_expired_token(monkeypatch):
    _clear_secret_loader_env(monkeypatch)
    monkeypatch.setenv("AWS_SECRET_NAME", "dev-mayds-triage-agent")
    monkeypatch.setenv("AWS_REGION", "eu-west-2")
    monkeypatch.setenv("AWS_SECRETS_REQUIRED", "true")
    monkeypatch.setattr(
        secrets_module,
        "get_aws_secret",
        lambda secret_name, region_name: (_ for _ in ()).throw(_expired_token_error()),
    )

    with pytest.raises(RuntimeError, match="Failed to load AWS secret"):
        secrets_module.load_aws_secrets_into_env()
