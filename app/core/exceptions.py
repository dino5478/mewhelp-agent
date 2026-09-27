"""统一异常：业务里抛这些异常，由 main.py 注册的处理器转成固定格式的错误 JSON。"""

import logging

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("mewhelp")


class AppException(Exception):
    """业务异常基类。code 供前端区分错误类型，message 给人看。"""

    def __init__(self, message: str, status_code: int = 400, code: str = "app_error"):
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)


class UnauthorizedError(AppException):
    def __init__(self, message: str = "未认证或凭证无效"):
        super().__init__(message, status_code=401, code="unauthorized")


class ForbiddenError(AppException):
    def __init__(self, message: str = "无权访问该资源"):
        super().__init__(message, status_code=403, code="forbidden")


class NotFoundError(AppException):
    def __init__(self, message: str = "资源不存在"):
        super().__init__(message, status_code=404, code="not_found")


class ConflictError(AppException):
    def __init__(self, message: str = "资源冲突"):
        super().__init__(message, status_code=409, code="conflict")


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.code, "message": exc.message},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # 未预期的错误：记录堆栈，但对外只返回通用信息（不泄露内部细节）
    logger.exception("unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"code": "internal_error", "message": "服务器内部错误"},
    )
