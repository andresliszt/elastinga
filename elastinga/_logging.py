
# -*- coding: utf-8 -*-
"""Logger configuration"""

import logging.config
import uuid

from typing import Union
from typing import Optional
from functools import wraps
from pathlib import Path

import structlog

from elastinga.settings import LogDest, LogFormatter
from elastinga.settings import Development, Production


try:  # pragma: no cover
    import colorama  # pylint: disable=W0611,

    COLORAMA_INSTALLED = True
 
except ImportError:
    COLORAMA_INSTALLED = False

try:  # pragma: no cover
    import tqdm 

    TQDM_INSTALLED = True
except ImportError:
    TQDM_INSTALLED = False

COMMON_CHAIN = [
    structlog.threadlocal.merge_threadlocal_context,
    structlog.stdlib.add_logger_name,
    structlog.stdlib.add_log_level,
    structlog.stdlib.PositionalArgumentsFormatter(),
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
]


def maybe_patch_tqdm(logger, dev_mode):
    """Replaces ``tqdm.tqdm`` calls with noops."""

    if (not dev_mode) and TQDM_INSTALLED:

        def _tqdm(*a, **kw):
            """Does nothing.
            Kills tqdm
            """
            if kw or len(a) != 1:
                logger.warning("tqdm usage supressed", args=a, kwargs=kw)
            return a[0]

        tqdm.tqdm = _tqdm


def _control_logging(
    dev_mode: bool,
    settings : Union[Development, Production], 
    log_file: Optional[Path] = None,
):

    level = settings.LOG_LEVEL
    formatter = settings.LOG_FORMAT
    dest = settings.LOG_DESTINATION

    if formatter == LogFormatter.JSON.value:
        fmt = {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.processors.JSONRenderer(),
            "foreign_pre_chain": COMMON_CHAIN,
        }
    elif formatter == LogFormatter.COLOR.value:

        fmt = {
            "()": structlog.stdlib.ProcessorFormatter,
            "processor": structlog.dev.ConsoleRenderer(
                colors=dev_mode and COLORAMA_INSTALLED
            ),
            "foreign_pre_chain": COMMON_CHAIN,
        }
        
    else:
        raise NotImplementedError(  # pragma: no cover
            "Pydantic shouldn't allow this."
        )

    if dest == LogDest.CONSOLE.value:
        hndler = {
            "level": level,
            "class": "logging.StreamHandler",
            "formatter": "default",
        }
    elif dest == LogDest.FILE.value:

        if not log_file:
            raise NotImplementedError("`log_file` must be specified")

        hndler = {
            "level": level,
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(log_file),
            "formatter": "default",
            "maxBytes": 10e6,
            "backupCount": 100,
        }
        log_file.parent.mkdir(parents=True, exist_ok=True)
    else:
        raise NotImplementedError(  # pragma: no cover
            "Pydantic shouldn't allow this."
        )

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"default": fmt},
            "handlers": {"default": hndler},
            "loggers": {
                "": {
                    "handlers": ["default"],
                    "level": level,
                    "propagate": True,
                }
            },
        }
    )
    structlog.configure_once(
        processors=[
            structlog.stdlib.filter_by_level,
            *COMMON_CHAIN,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def configure_logging(
    name,
    settings: Union[Development, Production],
    log_file: Optional[Path] = None,
    kidnap_loggers=False,
):
    """Setup logging with (hopefully) sane defaults.
    Args:
        name: Name for the logger.
        level: Level from where to start logging.
        dest: Whether to log to file or console.
        formatter: Whether to output data as json or colored, parsed
            logs.
        log_file: Where to store logfiles. Only used if ``dest='FILE'``.
        kidnap_loggers: Whether to configure the loggers on just
            instantiate one.
    Returns:
        The configured logger.
    """

    dev_mode = True if isinstance(settings, Development) else False

    if kidnap_loggers:
        _control_logging(dev_mode, settings, log_file)

    logger = structlog.get_logger(name)
    logger.trace = trace_using(logger) # pylint: disable=assignment-from-none
    maybe_patch_tqdm(logger, dev_mode)
    return logger


def trace_using(logger):
    """Decorator factory to trace callables.
    Args:
        logger: The logger to use for tracing
    Returns:
        The decorator, which takes a function and decorates it.
    """

    def real_decorator(func): # pylint: disable=unused-variable
        """Decorate a callable to report args, kwargs and return."""

        @wraps(func)
        def wrapper(*args, **kwargs):
            uuid_ = str(uuid.uuid4())
            qual = func.__qualname__
            args_repr = ",".join(repr(a) for a in args)
            kwargs_repr = ",".join(
                k + "=" + repr(v) for k, v in kwargs.items()
            )
            repr_ = f"{qual}({args_repr},{kwargs_repr})"
            with structlog.threadlocal.tmp_bind(
                logger,
                repr=repr_,
                uuid=uuid_,
                func=qual,
                args=args,
                kwargs=kwargs,
            ) as tmp_log:

                tmp_log.info(event="CALLED")
                retval = func(*args, **kwargs)
                tmp_log.info(event="RETURN", value=retval)
            return retval

        return wrapper

    return 
