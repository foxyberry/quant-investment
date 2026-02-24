"""Broker-layer exception hierarchy.

Every exception carries an implicit HTTP status mapping so that API
routers can translate domain errors into appropriate responses without
leaking internal details.

Hierarchy
---------
::

    RuntimeError
    └── BrokerError                    (500 Internal Server Error)
        ├── BrokerConnectionError      (503 Service Unavailable)
        ├── BrokerSafetyError          (409 Conflict)
        └── ...

    RuntimeError + ValueError
    └── BrokerValidationError          (400 Bad Request)

    RuntimeError + KeyError
    └── OrderNotFoundError             (404 Not Found)
"""

from __future__ import annotations


class BrokerError(RuntimeError):
    """Base exception for all broker operations.

    HTTP mapping: **500 Internal Server Error**
    """


class BrokerConnectionError(BrokerError):
    """Raised when the broker connection is unavailable or times out.

    HTTP mapping: **503 Service Unavailable**
    """


class BrokerValidationError(BrokerError, ValueError):
    """Raised when an order request fails input validation.

    Inherits from both ``BrokerError`` (for broker-layer catching) and
    ``ValueError`` (for generic validation catching).

    HTTP mapping: **400 Bad Request**
    """


class OrderNotFoundError(BrokerError, KeyError):
    """Raised when a referenced order ID does not exist.

    Inherits from both ``BrokerError`` (for broker-layer catching) and
    ``KeyError`` (for generic lookup catching).

    HTTP mapping: **404 Not Found**
    """


class BrokerSafetyError(BrokerError):
    """Raised when a safety rule (kill switch, duplicate guard, etc.) blocks an operation.

    HTTP mapping: **409 Conflict**
    """
