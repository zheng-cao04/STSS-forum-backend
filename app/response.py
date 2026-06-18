from typing import Any

from fastapi import HTTPException

SUCCESS_CODE = 0


def ok(data: Any = None, message: str = "OK") -> dict[str, Any]:
    return {"code": SUCCESS_CODE, "message": message, "data": data}


def fail(status_code: int, code: int, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message, "data": None},
    )
