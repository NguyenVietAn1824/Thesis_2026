from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from base import BaseModel
from fastapi import status
from fastapi.responses import JSONResponse


class ResponseMessage(str, Enum):
    INTERNAL_SERVER_ERROR = 'Server might meet some errors. Please try again later !!!'
    SUCCESS = 'Process successfully !!!'
    NOT_FOUND = 'Resource not found !!!'
    BAD_REQUEST = 'Invalid request !!!'
    UNPROCESSABLE_ENTITY = 'Input is not allowed !!!'
    RATE_LIMIT_EXCEEDED = 'Rate limit exceeded, try again later!!!'
    UNRELATED_EXCEED = 'Unrelated questions exceed, use a other question'
    UNAUTHORIZED = 'Unauthorized !!!'


class ExceptionHandler(BaseModel):
    logger: Any
    service_name: str

    def _create_message(self, e: str) -> str:
        return f'[{self.service_name}] error: {e}'

    def _create_response(
        self,
        message: str,
        data: Optional[dict] = None,
        status_code: int = status.HTTP_200_OK,
    ) -> JSONResponse:
        response_data = {'message': message}
        if data:
            response_data.update(data)

        return JSONResponse(content=response_data, status_code=status_code)

    def handle_exception(self, e: str, extra: dict) -> JSONResponse:
        self.logger.exception(e, extra=extra)

        return self._create_response(
            ResponseMessage.INTERNAL_SERVER_ERROR.value,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    def handle_not_found_error(self, message: str, extra: dict) -> JSONResponse:
        self.logger.error(
            message,
            extra=extra,
        )

        return self._create_response(
            ResponseMessage.NOT_FOUND.value,
            status_code=status.HTTP_404_NOT_FOUND,
        )

    def handle_success(self, output: dict) -> JSONResponse:
        data = {'info': output}

        return self._create_response(
            ResponseMessage.SUCCESS.value,
            data=data,
            status_code=status.HTTP_200_OK,
        )

    def handle_bad_request(self, message: str, extra: dict) -> JSONResponse:
        self.logger.error(
            message,
            extra=extra,
        )
        return self._create_response(
            ResponseMessage.BAD_REQUEST.value,
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    def handle_unprocessable_entity(self, message: str, extra: dict) -> JSONResponse:
        self.logger.error(
            message,
            extra=extra,
        )
        return self._create_response(
            ResponseMessage.UNPROCESSABLE_ENTITY.value,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    def handle_rate_limit_exceeded(self, message: str, extra: dict) -> JSONResponse:
        self.logger.warning('Rate limit exceeded', extra=extra)
        return self._create_response(
            ResponseMessage.RATE_LIMIT_EXCEEDED.value,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    def handle_unauthorized_error(self, message: str, extra: dict) -> JSONResponse:
        self.logger.warning(
            message,
            extra=extra,
        )
        return self._create_response(
            ResponseMessage.UNAUTHORIZED.value,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
