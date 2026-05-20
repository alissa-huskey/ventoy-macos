"""Provide the partialproperty descriptor."""

bp = breakpoint


class partialproperty:
    """Combine the functionality of property() and partialmethod().

    Example:
        >>> class RGBA:
        ...    rgba = None
        ...    def __init__(self, rgba: list = None):
        ...        self.rgba = rgba or [None, None, None, None]
        ...    def _get_channel(self, position: int) -> int:
        ...        return self.rgba[position]
        ...    def _set_channel(self, value, position: int):
        ...        self.rgba[position] = value
        ...
        ...    r = partialproperty(_get_channel, _set_channel, position=0)
        ...    g = partialproperty(_get_channel, _set_channel, position=1)
        ...    b = partialproperty(_get_channel, _set_channel, position=2)
        ...    a = partialproperty(_get_channel, _set_channel, position=3)
        >>> color = RGBA([255, 192, 128, 1])
        >>> color.r
        255
        >>> color.g
        192
        >>> color.b
        128
        >>> color.a
        1
        >>> color.r = 0
        >>> color.r
        0
        >>> color.rgba
        [0, 192, 128, 1]
    """

    def __init__(self, getter, setter=None, deleter=None, *args, **kwargs):
        """Initialize the object."""
        self.getter = getter
        self.setter = setter
        self.deleter = deleter
        self.args = args
        self.kwargs = kwargs

    def __set_name__(self, owner, name):
        """Set the owner class and attribute name."""
        self._name = name
        self._owner = owner

    def __get__(self, obj, objtype=None):
        """Call the getter function and return the result."""
        return self.getter(obj, *self.args, **self.kwargs)

    def __set__(self, obj, value):
        """Call the setter function and return the result."""
        if self.setter is None:
            raise AttributeError(
                f"{self._owner.__class__.__name__} "
                f"object can't set attribute: {self._name}"
            )

        self.setter(obj, *self.args, value, **self.kwargs)

    def __delete__(self, obj):
        """Call the deleter function and return the result."""
        if self.deleter is None:
            raise AttributeError(
                f"{self._owner.__class__.__name__} "
                f"object can't delete attribute: {self._name}"
            )

        self.deleter(obj, *self.args, **self.kwargs)
