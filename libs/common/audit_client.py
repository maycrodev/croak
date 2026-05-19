"""Cliente HTTP para registrar eventos en el audit-service.

El registro de auditoria es best-effort: si el audit-service no responde se loguea
una advertencia pero NO se rompe el flujo de negocio. A partir de MVP1 los servicios
llaman a `record_event` en cada operacion relevante (CLAUDE.md inciso II).
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from .config import settings

log = logging.getLogger("croak.audit-client")


def record_event(
    service: str,
    action: str,
    entity_type: str,
    entity_id: str,
    actor_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    """Envia un evento al audit-service. Nunca propaga errores de red."""
    event = {
        "service": service,
        "action": action,
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "actor_id": str(actor_id) if actor_id is not None else None,
        "payload": payload or {},
    }
    try:
        httpx.post(f"{settings.audit_url}/audit/events", json=event, timeout=3.0)
    except httpx.HTTPError as exc:
        log.warning(
            "No se pudo registrar evento de auditoria (%s/%s): %s", service, action, exc
        )
