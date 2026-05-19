"""Sandbox de ejecucion de codigo NO confiable (CLAUDE.md seccion 8).

Decision del orquestador (MVP1): aislamiento por subproceso + rlimits, NO
Docker-in-Docker. Patron Strategy (`Runner`) para poder anadir lenguajes o cambiar
a aislamiento por contenedor sin tocar al resto del servicio.

Garantias de cada corrida:
  - limite de CPU (RLIMIT_CPU), de memoria (RLIMIT_AS) y de descriptores (RLIMIT_NOFILE);
  - timeout de wall-clock duro (subprocess mata el proceso si lo excede);
  - carpeta temporal aislada por ejecucion (la crea/elimina el execution-service).
"""
from __future__ import annotations

import os
import resource
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

# --- Limites del sandbox (mandato del orquestador, MVP1) ---
CPU_SECONDS = 5                            # RLIMIT_CPU
ADDRESS_SPACE_BYTES = 256 * 1024 * 1024    # RLIMIT_AS  (256 MB)
MAX_OPEN_FILES = 64                        # RLIMIT_NOFILE
WALL_TIMEOUT_SECONDS = 10                  # timeout duro de subprocess.run


@dataclass
class RunOutcome:
    """Resultado de una sola corrida del sandbox."""

    stdout: str
    stderr: str
    exit_code: int | None
    duration_ms: int
    timed_out: bool

    @property
    def status(self) -> str:
        if self.timed_out:
            return "timeout"
        if self.exit_code == 0:
            return "success"
        return "runtime_error"


def _apply_limits() -> None:
    """preexec_fn: corre en el proceso hijo, tras fork y antes de exec."""
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_SECONDS, CPU_SECONDS))
    resource.setrlimit(resource.RLIMIT_AS, (ADDRESS_SPACE_BYTES, ADDRESS_SPACE_BYTES))
    resource.setrlimit(resource.RLIMIT_NOFILE, (MAX_OPEN_FILES, MAX_OPEN_FILES))


class Runner(ABC):
    """Estrategia de ejecucion para un lenguaje concreto."""

    language: str

    @abstractmethod
    def run(self, source_code: str, stdin: str, workdir: str) -> RunOutcome:
        """Ejecuta `source_code` alimentando `stdin`, dentro de `workdir`."""
        raise NotImplementedError


class PythonRunner(Runner):
    """Ejecuta codigo Python en un subproceso aislado."""

    language = "python"

    def run(self, source_code: str, stdin: str, workdir: str) -> RunOutcome:
        script_path = os.path.join(workdir, "main.py")
        with open(script_path, "w", encoding="utf-8") as fh:
            fh.write(source_code)

        started = time.monotonic()
        try:
            # -I: modo aislado (ignora env y site del usuario). -B: sin .pyc.
            proc = subprocess.run(
                [sys.executable, "-I", "-B", script_path],
                input=stdin.encode("utf-8"),
                capture_output=True,
                cwd=workdir,
                timeout=WALL_TIMEOUT_SECONDS,
                preexec_fn=_apply_limits,
                check=False,
            )
            duration_ms = int((time.monotonic() - started) * 1000)
            return RunOutcome(
                stdout=proc.stdout.decode("utf-8", errors="replace"),
                stderr=proc.stderr.decode("utf-8", errors="replace"),
                exit_code=proc.returncode,
                duration_ms=duration_ms,
                timed_out=False,
            )
        except subprocess.TimeoutExpired as exc:
            duration_ms = int((time.monotonic() - started) * 1000)
            return RunOutcome(
                stdout=(exc.stdout or b"").decode("utf-8", errors="replace"),
                stderr=(exc.stderr or b"").decode("utf-8", errors="replace"),
                exit_code=None,
                duration_ms=duration_ms,
                timed_out=True,
            )


# Registro de estrategias. Anadir un lenguaje = anadir un Runner aqui.
_RUNNERS: dict[str, Runner] = {PythonRunner.language: PythonRunner()}


def get_runner(language: str) -> Runner:
    """Devuelve el Runner para el lenguaje pedido; lanza ValueError si no existe."""
    runner = _RUNNERS.get((language or "python").lower())
    if runner is None:
        raise ValueError(f"Lenguaje no soportado en MVP1: {language!r}")
    return runner
