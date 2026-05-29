"""VentoyMacos."""

SECTOR_SIZE = 512


class VentoyMacosError(Exception):
    """VentoyMacos Errors."""

    def __init__(self, *args, **kwargs):
        """Initialize."""
        self.kwargs = kwargs
        for k, v in kwargs.items():
            setattr(self, k, v)

        super().__init__(*args)


class VentoyMacosWriteError(VentoyMacosError):
    """Failure during disk write operations."""


class Abort(VentoyMacosError):
    """User errors."""
