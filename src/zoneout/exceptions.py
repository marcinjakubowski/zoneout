class ZoneError(Exception):
    """Base exception for ZoneOut driver."""
    pass


class DeviceNotFoundError(ZoneError):
    """Raised when the USB device cannot be found or accessed."""
    pass


class ProtocolError(ZoneError):
    """Raised when the device sends an unexpected response or timeouts."""
    pass
