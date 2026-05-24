"""VentoyMacos."""

SECTOR_SIZE = 512


class VentoyMacosError(Exception):
    """VentoyMacos Errors."""

    def __init__(self, *args, **kwargs):
        """Initialize."""
        for k, v in kwargs.items():
            setattr(self, k, v)

        super().__init__(*args)
