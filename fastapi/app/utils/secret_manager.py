import os
from google.cloud import secretmanager_v1
from google.api_core.exceptions import NotFound, PermissionDenied
from .logging_config import logger

SECRET_NAME_SUFFIX = os.environ.get("SECRET_NAME_SUFFIX", "postgres-password")


def access_regional_secret(
    project_id: str, instance_name: str, region: str, version: str = "latest"
) -> str:
    """
    Retrieve a secret from Secret Manager (global or regional)

    Args:
        project_id: GCP project ID
        instance_name: Cloud SQL instance name
        region: Region of the secret
        version: Secret version (default: "latest")

    Returns:
        The decoded secret value

    Raises:
        ValueError: If the secret cannot be retrieved
    """
    try:
        # Regional secret
        secret_id = f"{instance_name}-{SECRET_NAME_SUFFIX}"

        # Endpoint to call the regional secret manager server
        api_endpoint = f"secretmanager.{region}.rep.googleapis.com"

        # Create the Secret Manager client
        client = secretmanager_v1.SecretManagerServiceClient(
            client_options={"api_endpoint": api_endpoint},
        )

        # Build the resource name of the secret version
        name = f"projects/{project_id}/locations/{region}/secrets/{secret_id}/versions/{version}"

        logger.info(f"Retrieving secret: {name}")
        # Retrieve the secret
        response = client.access_secret_version(request={"name": name})
        # Decode the secret
        secret_value = response.payload.data.decode("UTF-8")
        logger.info(f"Successfully retrieved secret: {secret_id}")

        return secret_value

    except NotFound:
        error_message = (
            f"Error: Secret '{secret_id}' or its version '{version}' not found "
            f"in region '{region}' of project '{project_id}'.\n"
        )
        logger.error(error_message)
        raise ValueError(error_message) from NotFound

    except PermissionDenied:
        error_message = (
            f"Error: Permission denied when accessing secret '{secret_id}'.\n"
            f"Please verify that the account executing this code has the IAM role "
            "'roles/secretmanager.secretAccessor'."
        )
        logger.error(error_message)
        raise ValueError(error_message) from PermissionDenied

    except Exception as e:
        error_message = f"An unexpected error occurred: {e}"
        logger.error(error_message)
        raise ValueError(error_message) from e
