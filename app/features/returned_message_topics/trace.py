import logging


# Temporary feature trace (RMT_TRACE): remove this module and its imports/calls
# when tracing is no longer needed.
TRACE_MARKER = "[RMT_TRACE]"
logger = logging.getLogger("app.features.returned_message_topics.trace")


def trace_info(event: str, **fields: object) -> None:
    logger.info("%s event=%s%s", TRACE_MARKER, event, _format_fields(fields))


def trace_exception(event: str, **fields: object) -> None:
    logger.exception("%s event=%s%s", TRACE_MARKER, event, _format_fields(fields))


def _format_fields(fields: dict[str, object]) -> str:
    if not fields:
        return ""
    return " " + " ".join(
        f"{key}={value!r}" for key, value in sorted(fields.items())
    )
