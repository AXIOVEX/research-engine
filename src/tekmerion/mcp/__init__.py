"""Tekmerion MCP server (Spec 009).

A third surface over the production services — the same store,
claims, verification, freeze, verdicts, export, deposit, adapter,
and math modules the shipped UI drives, through the same workspace
orchestration (`tekmerion.ui.state`). This package adds no record
semantics of its own.

This module is import-safe without the MCP SDK installed: the SDK is
an optional extra (`tekmerion[mcp]`), required only by the
`tekmerion-mcp` entry point (Spec 009, CLM-009-05).
"""
