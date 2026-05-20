"""attr module."""

from functools import cached_property, partialmethod
from typing import Callable

from more_itertools import first_true

bp = breakpoint


class attr():
    """Works like property() but with default getters/setters/deleters.

    The default methods will get, set or delete the attribute with the same
    name prefixed with an underscore. For attribute names that begin with an
    underscore, the name will be suffixed with an underscore instead.

    Like property(), it can be called as a function or used as a decorator.

    Decorator kwargs:
        method (str, default="getter"): one of getter, setter, or deleter

    Example:
        >>> @hasattrs   # initializes all of the protected (._attr) attributes
        ... class Car():
        ...     # if you only need a custom getter function, use the @attr decorator
        ...     # the setter will be created for you
        ...     @attr
        ...     def make(self):
        ...         return self._make.title()
        ...
        ...     # if you only need to customize a setter function, use the @attr decorator
        ...     # the getter will be created for you
        ...     @attr(method="setter")
        ...     def year(self, value: int):
        ...         if not (isinstance(value, int) and len(str(value)) == 4) :
        ...             raise ValueError("You must enter a 4 digit year.")
        ...         self._year = value
        ...
        ...     # if you want to define an attribute with no special functionality
        ...     # you can do so by calling the attr() function
        ...     model = attr("model")
        ...
        ...     # you can also define a getter or setter with an inline lambda
        ...     color = attr("color", getter=lambda self: self._color.lower())
        ...
        ...     # of you can pass the name of a prevoiusly defined function
        ...     def _set_vin(self, value):
        ...         self._vin = value.upper()
        ...     vin = attr("vin", setter=_set_vin)
        >>> car = Car()
        >>> car.make = "honda"
        >>> car._make
        'honda'
        >>> car.make
        'Honda'
        >>> car.year = 98
        Traceback (most recent call last):
        ...
        ValueError: You must enter a 4 digit year.
        >>> car.year = 1998
        >>> car.year
        1998
        >>> car.model = "Accord"
        >>> car.model
        Accord
        >>> car.color = "Black"
        >>> car._color
        'Black'
        >>> car.color
        'black'
        >>> car.vin = "1n4al2ap3cc151426"
        >>> car._vin
        '1N4AL2AP3CC151426'
        >>> car.vin
        '1N4AL2AP3CC151426'
    """  # noqa E501

    def __new__(cls, *args, **kwargs):
        """Return the Python property object for this attribute."""
        # when used in the form:
        #
        # @attr(method="setter")
        # def something(self):
        #     ...
        #
        # we must return a callable that takes a func as an argument
        # so this calls back to this method, but passes the function argument
        if not args and (kwargs.get("method")):
            return lambda func: cls(func, **kwargs)

        # otherwise, create a new attr class instance and instantiate it
        obj = object.__new__(cls)
        obj.__init__(*args, **kwargs)

        # the return the Python property from the instance
        return obj.result

    def __init__(self, attribute: str | Callable, **kwargs):
        """Initialize attr object.

        Arguments:
            attribute (str | Callable): name of the attribute or function to call
        Keyword Arguments:
            method (str, default="getter"): when attribute is a callable,
                                            which method it should be:
                                            "getter", "setter", or "deleter"
            getter (Callable | bool): getter function, set to False to not create
            setter (Callable | bool): setter function, set to False to not create
            deleter (Callable | bool): deleter function, set to False to not create
            doc (str): docstring
        """
        # if attribute is callable, get the name and doc from the function
        # and set the getter/setter/deleter to the func, depending on method
        if callable(attribute):
            method = kwargs.get("method", "getter")
            func = attribute
            name = func.__name__
            kwargs[method] = func
            kwargs["doc"] = func.__doc__
        else:
            name = attribute

        self.name = name
        self.doc = kwargs.pop("doc", f"{name} attribute.")
        self.methods = kwargs

    @property
    def private(self):
        """Return the private attribute name.

        Prefix the name with an underscore. Names that start with an underscore
        are suffixed with an underscore instead.
        """
        if self.name.startswith("_"):
            return f"{self.name}_"

        return f"_{self.name}"

    @cached_property
    def defaults(parent) -> dict[Callable]:
        """Return a dictionary of default accessor methods."""
        def getter(self):
            self.__dict__.setdefault(parent.private, None)
            return self.__dict__.get(parent.private)

        def setter(self, value):
            self.__dict__.setdefault(parent.private, None)
            self.__dict__[parent.private] = value

        def deleter(self):
            delattr(self, parent.private)

        return {
            "getter": getter,
            "setter": setter,
            "deleter": deleter,
        }

    def accessor(self, name: str) -> Callable:
        """Return a getter, setter or deleter accessor method."""
        # get the method defined by the user or the default
        method = self.methods.get(name, self.defaults[name])

        # don't create an accessor if the user set the kwarg to False
        if method is False:
            return None

        # set the method name and docstring if missing
        if callable(method):
            method.__name__ = method.__name__ or self.name
            method.__doc__ = method.__doc__ or self.doc
            method.__private__ = self.private

        return method

    getter = partialmethod(accessor, "getter")
    setter = partialmethod(accessor, "setter")
    deleter = partialmethod(accessor, "deleter")

    @property
    def result(self) -> "property":
        """Return the Python property object for this attribute."""
        prop = property(self.getter(), self.setter(), self.deleter(), self.doc)
        return prop


def hasattrs(cls):
    """Decorate class that uses the @attr decorator on any of its methods.

    Set all _attr attributes (as defined by @attr on the getter/setter/deleter
    .__private__ attribute) on cls to None.
    """
    # the getter/setter/deleter from each property that has a __private__
    # attribute
    attrs = [
        # the getter/setter/deleter that has a __private__ attribute
        first_true([
            func for func in (meth.fget, meth.fset, meth.fdel)
            if hasattr(func, "__private__")
        ])
        for meth in cls.__dict__.values()
        if isinstance(meth, property)
    ]

    for attr in attrs:
        if not attr:
            continue
        if not hasattr(cls, attr.__private__):
            setattr(cls, attr.__private__, None)
    return cls
