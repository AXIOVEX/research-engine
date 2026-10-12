"""Register-first study workspace (Spec 002 Phase 6, T219).

A thin, local UI over the production machinery — `tekmerion.store`,
`tekmerion.claims`, `tekmerion.freeze`, `tekmerion.verdicts`,
`tekmerion.verification`, `tekmerion.export`, `tekmerion.deposit`.
The UI registers no rules of its own: every refusal it shows is the
engine's, surfaced verbatim, and every mutation it offers is an append
through those services (CLM-002-32/33).

Appearance is governed by the approved wireframes (constitution
Article XIV, DN-009): the production stylesheet is the wireframes'
own `docs/wireframes/style.css`, adopted unchanged, and the markup
mirrors `docs/wireframes/*.html` screen for screen.
"""

from .server import create_server, serve

__all__ = ["create_server", "serve"]
