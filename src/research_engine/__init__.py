"""Axiovex Research Engine — record service core (Spec 002, Phase 1).

The record is an append-only, hash-chained JSONL event log per study.
Everything else in the system is a projection or a service around it.
"""

from .record import EventStore, VerificationResult, verify_log

__all__ = ["EventStore", "VerificationResult", "verify_log"]
__version__ = "0.1.0"
