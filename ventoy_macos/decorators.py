"""Decorators and partialproperty methods."""

import uuid
from functools import wraps

from ventoy_macos import VentoyMacosError

bp = breakpoint


ALL = [
    "_private_setter",
    "require_fd",
    "verify_attr",
]


def _private_setter(self, value: bytes, name: str):
    """Set A private attribute."""
    attr_name = f"_{name}"
    setattr(self, attr_name, value)


def require_fd(func):
    """Return a decorator for methods that require an open FD.

    For the Builder class.
    """

    def wrapper(self, *args, **kwargs):
        """Ensure .disk exists and open self.fd if it is not already."""
        if not self.disk:
            raise VentoyMacosError("Cannot write to disk: no .disk attribute.")
        if not (self.fd.is_open or self.fd.id):
            self.fd.open()
        func(self, *args, **kwargs)
    return wrapper


def verify_attr(*attrs):
    """Verify that an attribute is present and not null."""

    def decorator(func):
        """Return wrapper function."""

        @wraps(func)
        def wrapper(self):
            """Ensure .disk exists and open self.fd if it is not already."""
            for a in attrs:
                value = getattr(self, a, None)
                if not value:
                    raise VentoyMacosError(
                        f"Unable to write {a} to disk as the value is not set."
                    )
            func(self)
        return wrapper
    return decorator


def _get_cached_uuid(self, name):
    """Get a UUID and cache it.

    Intended to be used as a partial() with attr().

    Example:
        from attrs import attr, hasattrs
        from ventoy_macos.decorators import _get_cached_uuid

        @hasattrs
        class Thing:
            id = attr("id", getter=partial(_get_cached_uuid, name="id"))
    """
    attr_name = f"_{name}"
    value = getattr(self, attr_name, None)
    if not value:
        value = uuid.uuid4()
        setattr(self, attr_name, value)
    return value
