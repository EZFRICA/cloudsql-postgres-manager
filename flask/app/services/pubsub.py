import base64
import json

from ..utils.logging_config import logger


class PubSubMessageParser:
    """Parser for Pub/Sub messages with schema validation"""

    @staticmethod
    def parse_pubsub_message(request_json: dict) -> dict:
        """
        Parse a Pub/Sub message and extract the data

        Args:
            request_json: The JSON payload of the request

        Returns:
            The parsed message data with metadata

        Raises:
            ValueError: If the message format is invalid

        Expected format:
        {
            "message": {
                "data": "base64_encoded_json",
                "attributes": {},
                "messageId": "...",
                "publishTime": "..."
            }
        }
        """
        if not request_json:
            raise ValueError("Empty request payload")

        # Verify Pub/Sub format
        if "message" not in request_json:
            raise ValueError("Invalid Pub/Sub format: missing 'message' field")

        pubsub_message = request_json["message"]

        # Extract and decode data
        if "data" not in pubsub_message:
            raise ValueError("Invalid Pub/Sub format: missing 'data' field")

        try:
            # Decode base64
            encoded_data = pubsub_message["data"]
            decoded_data = base64.b64decode(encoded_data).decode("utf-8")

            # Parse JSON
            message_data = json.loads(decoded_data)

            # Add Pub/Sub metadata
            message_data["_pubsub_metadata"] = {
                "messageId": pubsub_message.get("messageId"),
                "publishTime": pubsub_message.get("publishTime"),
                "attributes": pubsub_message.get("attributes", {}),
            }

            return message_data

        except (base64.binascii.Error, UnicodeDecodeError) as e:
            raise ValueError(f"Failed to decode base64 data: {str(e)}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON data: {str(e)}")

    @staticmethod
    def validate_message_schema(message_data: dict) -> dict:
        """
        Validate the message schema and return cleaned data

        Args:
            message_data: The message data to validate

        Returns:
            The validated and cleaned data

        Raises:
            ValueError: If required fields are missing or invalid

        Expected format:
        {
            "project_id": "my-project",
            "instance_name": "my-instance",
            "database_name": "my-db",
            "region": "europe-west1",
            "schema_name": "my-schema",  # optional, default: {database_name}_schema
            "iam_users": [
                {
                    "name": "user@project.iam.gserviceaccount.com",
                    "permission_level": "readonly|readwrite|admin"  # optional, default: readonly
                }
            ]
        }
        """
        required_fields = [
            "project_id",
            "instance_name",
            "database_name",
            "region",
            "iam_users",
        ]
        missing_fields = [
            field for field in required_fields if not message_data.get(field)
        ]

        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")

        # Clean and validate data
        cleaned_data = {
            "project_id": str(message_data["project_id"]).strip(),
            "instance_name": str(message_data["instance_name"]).strip(),
            "database_name": str(message_data["database_name"]).strip(),
            "region": str(message_data["region"]).strip(),
            "schema_name": str(
                message_data.get(
                    "schema_name", f"{message_data['database_name']}_schema"
                )
            ).strip(),
            "iam_users": message_data.get("iam_users", []),
        }

        # Validate schema name
        if not cleaned_data["schema_name"]:
            raise ValueError("Schema name cannot be empty")

        # Validate IAM users
        if not isinstance(cleaned_data["iam_users"], list):
            raise ValueError("iam_users must be a list")

        validated_users = []
        for i, user in enumerate(cleaned_data["iam_users"]):
            if not isinstance(user, dict):
                logger.warning(f"Skipping invalid user at index {i}: not a dict")
                continue

            user_name = user.get("name")
            if not user_name or not isinstance(user_name, str):
                logger.warning(f"Skipping user at index {i}: missing or invalid name")
                continue

            permission_level = user.get("permission_level", "readonly")
            if permission_level not in ["readonly", "readwrite", "admin"]:
                logger.warning(
                    f"Invalid permission_level '{permission_level}' for user {user_name}, using 'readonly'"
                )
                permission_level = "readonly"

            validated_users.append(
                {"name": user_name.strip(), "permission_level": permission_level}
            )

        cleaned_data["iam_users"] = validated_users

        # Preserve Pub/Sub metadata
        if "_pubsub_metadata" in message_data:
            cleaned_data["_pubsub_metadata"] = message_data["_pubsub_metadata"]

        return cleaned_data
