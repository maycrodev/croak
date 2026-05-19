"""Logging estructurado en JSON hacia stdout (sin stack de observabilidad)."""
from __future__ import annotations

import datetime as dt
import json
import logging
import sys


class JsonFormatter(logging.Formatter):
    """Serializa cada registro de log como una linea JSON."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(service_name: str, level: str = "INFO") -> logging.Logger:
    """Configura el root logger con salida JSON y devuelve el logger del servicio."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    return logging.getLogger(service_name)
