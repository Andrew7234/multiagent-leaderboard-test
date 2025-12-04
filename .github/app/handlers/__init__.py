"""Webhook handlers."""

from enum import StrEnum


class Status(StrEnum):
    OK = "ok"
    IGNORED = "ignored"
    ERROR = "error"
    REJECTED = "rejected"
