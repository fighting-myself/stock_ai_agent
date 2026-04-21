from pydantic import BaseModel
from typing import Any, Optional

class ApiResponse(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    agent_type: Optional[str] = None
    model: Optional[str] = None

def success_response(data: Any, agent_type: str, model: str) -> ApiResponse:
    return ApiResponse(
        success=True,
        data=data,
        agent_type=agent_type,
        model=model
    )

def error_response(message: str) -> ApiResponse:
    return ApiResponse(success=False, error=message)