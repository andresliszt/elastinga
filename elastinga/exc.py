# -*- coding: utf-8 -*-
"""Exceptions and Error Handling."""

import abc
import functools
from contextlib import contextmanager
from types import ModuleType
from typing import Any
from typing import Callable
from typing import Generator
from typing import Type
from typing import Union


class ElastingaErrorMixin(abc.ABC, BaseException):
    """Base class for custom errors and exceptions.

    Example:

        >>> class MyError(ElastingaErrorMixin):
                msg_template = "Value ``{value}`` could not be found"
        >>> raise MyError(value="can't touch this")
        (...)
        MyError: Value `can't touch this` could not be found

    """

    @property
    @abc.abstractmethod
    def msg_template(self) -> str:
        """A template to print when the exception is raised.

        Example:
            "Value ``{value}`` could not be found"

        """

    def __init__(self, **ctx: Any) -> None:
        self.ctx = ctx
        super().__init__()

    def __str__(self) -> str:
        txt = self.msg_template
        for name, value in self.ctx.items():
            txt = txt.replace("{" + name + "}", str(value))
        txt = txt.replace("`{", "").replace("}`", "")
        return txt


@contextmanager
def change_exception(
    raise_exc: Union[ElastingaErrorMixin, Type[ElastingaErrorMixin]],
    *except_types: Type[BaseException],
) -> Generator[None, None, None]:
    """Context Manager to replace exceptions with a custom one.

    Args:
        raise_exc: The destination exception.
        except_types: The exceptions to capture.

    Raises:
        raise_exc: If any of the supplied classes raised.

    See Also:
        :func:`pydantic.utils.change_exception`

    """
    try:
        yield
    except except_types as exception:
        raise raise_exc from exception  # type: ignore


class EnvVarNotFound(ElastingaErrorMixin, NameError):
    """Levantar cuando no se encuentre una variable de entorno"""

    msg_template = "La variable de entorno `{env_var}` no se puede encontrar"


class ElasticsearchNotReady(ElastingaErrorMixin, NameError):
    """Levantar cuando la conexión a elasticsearch no este preparada"""

    msg_template = "La conexión a elasticsearch no está lista aun"


class IndexNotExists(ElastingaErrorMixin, NameError):
    """Levantar cuando se intente operar sobre un índice inexistente"""

    msg_template = "El índice {index} no existe"
