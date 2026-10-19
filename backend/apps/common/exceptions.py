import logging

from rest_framework.views import exception_handler

logger = logging.getLogger("quillstack")


def quillstack_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        payload = {
            "error": True,
            "status_code": response.status_code,
            "detail": response.data,
        }
        if isinstance(response.data, dict) and "detail" in response.data and len(response.data) > 1:
            payload["message"] = str(response.data["detail"])
        else:
            payload["message"] = "Request failed"
        response.data = payload
        logger.warning("API error %s: %s", response.status_code, payload.get("message"))
    return response
