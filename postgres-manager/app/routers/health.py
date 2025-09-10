"""
Health check router for monitoring and service discovery.
"""

from fastapi import APIRouter
from ..models import HealthResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", response_model=HealthResponse)
async def health_check():
    """
    ## Health Check Endpoint

    Check the health status of the Cloud SQL IAM User Permission Manager service.

    ### Returns
    - **status**: Service health status (`healthy` or `unhealthy`)
    - **service**: Service name
    - **version**: Current service version

    ### Use Cases
    - **Load Balancer Health Checks**: Configure load balancers to use this endpoint
    - **Monitoring Systems**: Integrate with monitoring tools like Prometheus, Datadog
    - **Service Discovery**: Verify service availability before routing traffic
    - **CI/CD Pipelines**: Validate service health after deployments

    ### Example Response
    ```json
    {
        "status": "healthy",
        "service": "Cloud SQL IAM User Permission Manager",
        "version": "4.0.0"
    }
    ```

    ### HTTP Status Codes
    - `200 OK`: Service is healthy
    - `503 Service Unavailable`: Service is unhealthy (not implemented in this version)
    """
    return HealthResponse(
        status="healthy",
        service="Cloud SQL IAM User Permission Manager",
        version="0.1.0",
    )
