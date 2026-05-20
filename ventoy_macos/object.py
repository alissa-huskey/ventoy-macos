"""Custom base object class."""


class Object():
    """Arbitrary object class.

    Useful to subclass from.

    - Assigns all kwargs as attributes on init.
    - Provides repr to display class name and all attributes and values.
    - Provides equivilance opeartor.
    - Provides .dict attriute, which returns all attributes in a dictionary.

    Examples:
        >>> a = Object(a=1, b=2, c=3)
        >>> a
        Object(a=1, b=2, c=3)
        >>> a.dict
        {'a': 1, 'b': 2, 'c': 3}
        >>> b = Object(c=3, b=2, a=1)
        >>> a == b
        True
        >>> a.d = 4
        >>> a
        Object(a=1, b=2, c=3, d=4)
    """

    def __init__(self, **kwargs):
        """Set all keyword args as attributes."""
        for k, v in kwargs.items():
            setattr(self, k, v)

    def __repr__(self):
        """Object(attr='value')."""
        attrs = ", ".join([f"{k}={v!r}" for k, v in self.__dict__.items()])
        return f"{self.__class__.__name__}({attrs})"

    @property
    def dict(self) -> dict:
        """Return the object attributes as a dictionary."""
        return self.__dict__

    def __eq__(self, other):
        """Provide comparison oprators."""
        return (isinstance(other, self.__class__) and
                self.__dict__ == other.__dict__)
