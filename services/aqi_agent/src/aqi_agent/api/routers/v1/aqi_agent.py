from __future__ import annotations

import time

from aqi_agent.api.helpers.exception_handler import ExceptionHandler
from aqi_agent.application.service import AQIAgentApplication
from aqi_agent.application.service import AQIAgentInput
from aqi_agent.application.service import AQIAgentOutput
from aqi_agent.shared.exception import UnauthorizedException
from aqi_agent.shared.exception import ValidationException
from aqi_agent.shared.utils import get_resources
from aqi_agent.shared.utils import get_settings
from fastapi import APIRouter
from fastapi import BackgroundTasks
from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from logger import get_logger

aqi_agent_router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


@aqi_agent_router.post(
    '/aqi_agent',
    response_model=AQIAgentOutput,
)
async def aqi_agent(
    request: Request,
    background_tasks: BackgroundTasks,
    inputs: AQIAgentInput,
) -> JSONResponse:

    exception_handler = ExceptionHandler(
        logger=logger.bind(),
        service_name=__name__,
    )

    try:
        resources = get_resources(request)
        aqi_agent_application = AQIAgentApplication(
            resources=resources,
        )
    except Exception as e:
        return exception_handler.handle_exception(
            e=f'Error during application initialization: {e!s}',
            extra={},
        )

    # Validate required inputs
    try:
        if not inputs.question:
            return exception_handler.handle_bad_request(
                message='Question is required',
                extra={'conversation_id': inputs.conversation_id},
            )
        if not inputs.conversation_id:
            return exception_handler.handle_bad_request(
                message='Conversation ID is required',
                extra={'question': inputs.question},
            )
        if not inputs.user_id:
            return exception_handler.handle_bad_request(
                message='User ID is required',
                extra={'question': inputs.question},
            )
        else:
            with resources.sql_database.get_session() as session:
                user = resources.sql_database.get_user_by_id(
                    session,
                    inputs.user_id,
                )
            if not user:
                return exception_handler.handle_unauthorized_error(
                    message='Invalid user_id',
                    extra={'question': inputs.question},
                )
    except Exception as e:
        return exception_handler.handle_exception(
            e=f'Error during user_id validation: {e!s}',
            extra={},
        )

    try:
        start_time = time.time()
        aqi_agent_response = await aqi_agent_application.process(
            inputs=inputs,
            background_tasks=background_tasks,
        )
        end_time = time.time()

        logger.info(
            'AQI Agent request processed',
            extra={
                'conversation_id': inputs.conversation_id,
                'question': inputs.question,
                'processing_time_seconds': end_time - start_time,
            },
        )

    except UnauthorizedException as e:
        return exception_handler.handle_unauthorized_error(message=str(e), extra={})

    except ValidationException as e:
        return exception_handler.handle_bad_request(
            message=str(e),
            extra={'question': inputs.question},
        )

    except Exception as e:
        return exception_handler.handle_exception(
            e=str(e),
            extra={
                'conversation_id': inputs.conversation_id,
            },
        )

    return exception_handler.handle_success(
        jsonable_encoder(
            aqi_agent_response,
        ),
    )
