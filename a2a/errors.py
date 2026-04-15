"""
A2A Error Handling
Standardized exceptions and FastAPI error handlers
"""
from typing import Any, Optional

from fastapi import Request
from fastapi.responses import JSONResponse

from a2a.models import A2AError


class A2AException(Exception):
    """Base exception for A2A protocol errors"""

    def __init__(
        self,
        code: int,
        message: str,
        data: Optional[dict[str, Any]] = None,
        retryable: bool = False,
        retry_after: Optional[int] = None,
    ):
        self.code = code
        self.message = message
        self.data = data
        self.retryable = retryable
        self.retry_after = retry_after
        super().__init__(message)

    def to_error(self) -> A2AError:
        return A2AError(
            code=self.code,
            message=self.message,
            data=self.data,
            retryable=self.retryable,
            retry_after_seconds=self.retry_after,
        )


# ============================================================
# PREDEFINED ERROR FACTORIES
# ============================================================

def task_not_found(task_id: str) -> A2AException:
    return A2AException(404, f"Task not found: {task_id}")


def invalid_transition(from_state: str, to_state: str) -> A2AException:
    return A2AException(
        400,
        f"Invalid state transition: {from_state} -> {to_state}",
        data={"from_state": from_state, "to_state": to_state},
    )


def invalid_request(message: str) -> A2AException:
    return A2AException(400, message)


def unauthorized(message: str = "Unauthorized") -> A2AException:
    return A2AException(401, message)


def agent_busy() -> A2AException:
    return A2AException(429, "Agent is busy", retryable=True, retry_after=5)


def internal_error(message: str = "Internal server error") -> A2AException:
    return A2AException(500, message, retryable=True, retry_after=10)


def webhook_not_found(webhook_id: str) -> A2AException:
    return A2AException(404, f"Webhook not found: {webhook_id}")


# ============================================================
# FASTAPI EXCEPTION HANDLER
# ============================================================

async def a2a_exception_handler(request: Request, exc: A2AException) -> JSONResponse:
    """FastAPI exception handler for A2AException"""
    return JSONResponse(
        status_code=exc.code,
        content=exc.to_error().model_dump(),
    )
