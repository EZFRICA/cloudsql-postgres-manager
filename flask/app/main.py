import atexit

from flask import Flask, request, jsonify
from app.services.cloudsql import CloudSQLUserManager
from app.services.pubsub import PubSubMessageParser
from app.utils.logging_config import logger

app = Flask(__name__)

# Global instances
user_manager = CloudSQLUserManager()
message_parser = PubSubMessageParser()


@app.route('/health', methods=['GET'])
def health_check():
    """
    Service health check endpoint

    Returns:
        JSON response with service status
    """
    return jsonify({
        "status": "healthy",
        "service": "Cloud SQL IAM User Permission Manager",
        "version": "0.1.0"
    }), 200


@app.route('/manage-users', methods=['POST'])
def manage_users_direct():
    """
    Direct endpoint for managing IAM user permissions
    
    Expected format in body:
    {
        "project_id": "my-project",
        "instance_name": "my-instance",
        "database_name": "my-db",
        "region": "europe-west1",
        "schema_name": "my-schema",  # optional, default: {database_name}_schema
        "iam_users": [
            {
                "name": "user@project.iam.gserviceaccount.com",
                "permission_level": "readonly|readwrite|admin"
            }
        ]
    }

    Returns:
        JSON response with operation status
    """
    try:
        # 1. Retrieve and validate JSON data
        request_json = request.get_json()
        logger.info("Received direct API request for IAM user permission management")

        if not request_json:
            logger.error("Empty request payload")
            return jsonify({"error": "Empty request payload"}), 400

        # 2. Validate data schema
        try:
            validated_data = message_parser.validate_message_schema(request_json)
        except ValueError as e:
            logger.error(f"Invalid request schema: {e}")
            return jsonify({"error": f"Invalid request schema: {str(e)}"}), 400

        # 3. Log processing information (without sensitive data)
        logger.info(f"Processing IAM user permissions for project: {validated_data['project_id']}, "
                    f"instance: {validated_data['instance_name']}, "
                    f"database: {validated_data['database_name']}, "
                    f"schema: {validated_data['schema_name']}, "
                    f"region: {validated_data['region']}, "
                    f"users: {len(validated_data['iam_users'])}")

        # 4. Check if there are users to process or revocations to make
        if not validated_data['iam_users']:
            logger.info("No IAM users specified in request - will revoke permissions for all existing users")

        # 5. Validate IAM permissions for specified users
        if validated_data['iam_users']:
            permissions_valid, invalid_users = user_manager.validate_iam_permissions(
                validated_data['project_id'],
                validated_data['iam_users']
            )

            if not permissions_valid:
                # Filter invalid users
                original_count = len(validated_data['iam_users'])
                validated_data['iam_users'] = [
                    user for user in validated_data['iam_users']
                    if user['name'] not in invalid_users
                ]

                logger.warning(
                    f"Proceeding with {len(validated_data['iam_users'])} valid users out of {original_count}, "
                    f"skipping {len(invalid_users)} users with invalid IAM permissions")

        # 6. Process IAM user permissions
        result = user_manager.process_users(validated_data)

        if result["success"]:
            # Success even with partial errors
            total_errors = result.get("total_errors", 0)
            
            if total_errors > 0:
                logger.warning(f"Processed direct API request with {total_errors} errors")
                return jsonify({
                    "success": True,
                    "message": f"User permissions processed with {total_errors} errors",
                    "details": result
                }), 200
            else:
                logger.info("Successfully processed direct API request")
                return jsonify({
                    "success": True,
                    "message": "User permissions processed successfully",
                    "details": result
                }), 200
        else:
            logger.error(f"Failed to process direct API request: {result.get('error', 'Unknown error')}")
            return jsonify({
                "success": False,
                "error": result.get('error', 'Unknown error'),
                "details": result
            }), 500

    except Exception as e:
        logger.error(f"Unexpected error in direct API request: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500


@app.route('/', methods=['POST'])
@app.route('/pubsub', methods=['POST'])
def handle_pubsub():
    """
    Main endpoint for processing Pub/Sub messages

    IMPORTANT: This service only manages IAM Database Authentication user permissions.
    IAM users themselves must be created/deleted via Terraform, gcloud, or Cloud SQL API.

    Expected format in message:
    {
        "project_id": "my-project",
        "instance_name": "my-instance",
        "database_name": "my-db",
        "region": "europe-west1",
        "schema_name": "my-schema",  # optional, default: {database_name}_schema
        "iam_users": [
            {
                "name": "user@project.iam.gserviceaccount.com",
                "permission_level": "readonly|readwrite|admin"
            }
        ]
    }

    Returns:
        HTTP 204 on success, HTTP 400/500 on error
    """
    try:
        # 1. Parse Pub/Sub message
        request_json = request.get_json()
        logger.info("Received Pub/Sub message for IAM user permission management")

        # Basic JSON format validation
        if not request_json:
            logger.error("Empty request payload")
            return jsonify({"error": "Empty request payload"}), 400

        try:
            message_data = message_parser.parse_pubsub_message(request_json)
        except ValueError as e:
            logger.error(f"Invalid Pub/Sub message format: {e}")
            return jsonify({"error": f"Invalid message format: {str(e)}"}), 400

        # 2. Validate data schema
        try:
            validated_data = message_parser.validate_message_schema(message_data)
        except ValueError as e:
            logger.error(f"Invalid message schema: {e}")
            return jsonify({"error": f"Invalid message schema: {str(e)}"}), 400

        # 3. Log processing information (without sensitive data)
        logger.info(f"Processing IAM user permissions for project: {validated_data['project_id']}, "
                    f"instance: {validated_data['instance_name']}, "
                    f"database: {validated_data['database_name']}, "
                    f"schema: {validated_data['schema_name']}, "
                    f"region: {validated_data['region']}, "
                    f"users: {len(validated_data['iam_users'])}")

        # 4. Check if there are users to process or revocations to make
        if not validated_data['iam_users']:
            logger.info("No IAM users specified in message - will revoke permissions for all existing users")

        # 5. Validate IAM permissions for specified users
        if validated_data['iam_users']:
            permissions_valid, invalid_users = user_manager.validate_iam_permissions(
                validated_data['project_id'],
                validated_data['iam_users']
            )

            if not permissions_valid:
                # Filter invalid users
                original_count = len(validated_data['iam_users'])
                validated_data['iam_users'] = [
                    user for user in validated_data['iam_users']
                    if user['name'] not in invalid_users
                ]

                logger.warning(
                    f"Proceeding with {len(validated_data['iam_users'])} valid users out of {original_count}, "
                    f"skipping {len(invalid_users)} users with invalid IAM permissions")

        # 6. Process IAM user permissions
        result = user_manager.process_users(validated_data)

        if result["success"]:
            # Success even with partial errors
            total_errors = result.get("total_errors", 0)
            message_id = result.get('message_id', 'unknown')

            if total_errors > 0:
                logger.warning(f"Processed Pub/Sub message {message_id} with {total_errors} errors")
            else:
                logger.info(f"Successfully processed Pub/Sub message: {message_id}")

            # Return 204 No Content to indicate success to Pub/Sub
            return '', 204
        else:
            logger.error(f"Failed to process IAM user permissions: {result.get('error', 'Unknown error')}")
            return jsonify({
                "error": result.get("error", "Unknown processing error"),
                "details": {
                    "project_id": result.get("project_id"),
                    "instance_name": result.get("instance_name"),
                    "database_name": result.get("database_name"),
                    "schema_name": result.get("schema_name")
                }
            }), 500

    except Exception as e:
        logger.error(f"Unexpected error processing Pub/Sub message: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@app.errorhandler(404)
def not_found(error):
    """Handler for endpoints not found"""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(405)
def method_not_allowed(error):
    """Handler for unauthorized methods"""
    return jsonify({"error": "Method not allowed"}), 405


@app.errorhandler(500)
def internal_server_error(error):
    """Handler for internal server errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500


def cleanup():
    """Cleanup function called at shutdown"""
    logger.info("Application shutting down, cleaning up resources")
    user_manager.close()


atexit.register(cleanup)

