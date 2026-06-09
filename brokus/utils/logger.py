"""Logging utility for brokus – mit Tracing, Stage-Namen und Timing."""

import atexit
import logging
import sys
import time
import traceback
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field


# ─────────────────────────────────────────────────────────────
# TraceEntry – ein einzelner Trace-Schritt
# ─────────────────────────────────────────────────────────────

@dataclass
class TraceEntry:
    """A single trace step: stage, action, timing, details."""
    stage: str          # e.g. "DNA", "Kapitel 3/12"
    action: str         # e.g. "Extrahiere Buch-DNA", "Compliance-Check"
    status: str         # "RUNNING", "OK", "WARN", "ERROR"
    elapsed_ms: float = 0.0
    detail: str = ""
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    def format_console(self) -> str:
        """Format for terminal output."""
        icons = {"RUNNING": "🔄", "OK": "✅", "WARN": "⚠️", "ERROR": "❌"}
        icon = icons.get(self.status, "▸")
        time_str = f" ({self.elapsed_ms:.0f}ms)" if self.elapsed_ms > 0 else ""
        detail_str = f" – {self.detail}" if self.detail else ""
        return f"  {icon} [{self.stage}] {self.action}{detail_str}{time_str}"

    def format_log(self) -> str:
        """Format for log file."""
        time_str = f" ({self.elapsed_ms:.0f}ms)" if self.elapsed_ms > 0 else ""
        return f"[{self.timestamp}] [{self.status}] [{self.stage}] {self.action}{time_str}"


# ─────────────────────────────────────────────────────────────
# TraceContext – verfolgt die aktuelle Operation
# ─────────────────────────────────────────────────────────────

class TraceContext:
    """Context manager for tracing a pipeline stage."""

    def __init__(self, stage: str, action: str, detail: str = ""):
        self.stage = stage
        self.action = action
        self.detail = detail
        self._start: float = 0.0
        self._entry: TraceEntry | None = None

    async def __aenter__(self):
        self._start = time.monotonic()
        self._entry = TraceEntry(
            stage=self.stage, action=self.action, status="RUNNING", detail=self.detail,
        )
        log._emit(self._entry)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        elapsed = (time.monotonic() - self._start) * 1000
        if exc_type is not None:
            status = "ERROR"
            detail = f"{exc_type.__name__}: {exc_val}" if exc_val else str(exc_type.__name__)
        else:
            status = "OK"
            detail = ""
        self._entry = TraceEntry(
            stage=self.stage, action=self.action, status=status,
            elapsed_ms=elapsed, detail=detail,
        )
        log._emit(self._entry)
        return False  # Don't suppress exceptions

    # Sync variant for non-async contexts
    def __enter__(self):
        self._start = time.monotonic()
        self._entry = TraceEntry(
            stage=self.stage, action=self.action, status="RUNNING", detail=self.detail,
        )
        log._emit(self._entry)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = (time.monotonic() - self._start) * 1000
        if exc_type is not None:
            status = "ERROR"
            detail = f"{exc_type.__name__}: {exc_val}" if exc_val else str(exc_type.__name__)
        else:
            status = "OK"
            detail = ""
        self._entry = TraceEntry(
            stage=self.stage, action=self.action, status=status,
            elapsed_ms=elapsed, detail=detail,
        )
        log._emit(self._entry)


# ─────────────────────────────────────────────────────────────
# LogManager – mit Tracing und Stage-Unterstützung
# ─────────────────────────────────────────────────────────────

class LogManager:
    """Manages application logging with trace support."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self.logger = logging.getLogger("brokus")
        self.logger.setLevel(logging.DEBUG)

        self._trace_log: list[TraceEntry] = []
        self._tui_callback = None
        self._console_callback = None

        # ── Log-Datei (data/logs/brokus_YYYYMMDD_HHMMSS.log) ──
        log_dir = Path("data/logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(
            log_dir / f"brokus_{datetime.now():%Y%m%d_%H%M%S}.log"
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        self.logger.addHandler(fh)

        # ── Trace-Log-Datei (nur Trace-Einträge, lesbarer) ──
        self._trace_file = open(
            log_dir / f"trace_{datetime.now():%Y%m%d_%H%M%S}.log",
            "w", encoding="utf-8",
        )
        self._trace_file.write(f"brokus Trace Log – {datetime.now():%Y-%m-%d %H:%M:%S}\n")
        self._trace_file.write("=" * 80 + "\n")
        self._trace_file.flush()
        atexit.register(self.close)

        # ── Console Handler ──
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        self.logger.addHandler(ch)

    def set_tui_callback(self, callback):
        """Register a callback for TUI log display."""
        self._tui_callback = callback

    def set_console_callback(self, callback):
        """Register a callback for console trace display."""
        self._console_callback = callback

    def _emit(self, entry: TraceEntry):
        """Internal: emit a trace entry to all outputs."""
        self._trace_log.append(entry)

        # Trace-Datei
        self._trace_file.write(entry.format_log() + "\n")
        self._trace_file.flush()

        # Console (via Callback oder direkt)
        if self._console_callback:
            self._console_callback(entry)
        else:
            print(entry.format_console())

        # TUI
        if self._tui_callback:
            self._tui_callback(entry.timestamp, entry.status, entry.stage)

        # Standard-Logger (als INFO, ERROR usw.)
        log_level = {
            "OK": "INFO", "RUNNING": "DEBUG",
            "WARN": "WARNING", "ERROR": "ERROR",
        }.get(entry.status, "INFO")

        msg = f"[{entry.stage}] {entry.action}"
        if entry.detail:
            msg += f" – {entry.detail}"
        log_method = getattr(self.logger, log_level.lower(), self.logger.info)
        log_method(msg)

    # ── Standard-Log-Methoden ──

    def log(self, level: str, message: str, stage: str = ""):
        """Log a raw message with optional stage prefix."""
        prefix = f"[{stage}] " if stage else ""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._trace_log.append(TraceEntry(
            stage=stage or "-", action=message, status=level,
        ))
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(f"{prefix}{message}")

    def debug(self, msg: str, stage: str = ""): self.log("DEBUG", msg, stage)
    def info(self, msg: str, stage: str = ""): self.log("INFO", msg, stage)
    def warning(self, msg: str, stage: str = ""): self.log("WARNING", msg, stage)
    def error(self, msg: str, stage: str = ""): self.log("ERROR", msg, stage)

    def exception(self, msg: str, stage: str = ""):
        """Log with full traceback."""
        tb = traceback.format_exc().strip()
        prefix = f"[{stage}] " if stage else ""
        if tb and tb not in ("None", ""):
            self.log("ERROR", f"{prefix}{msg}\n{tb}")
        else:
            self.log("ERROR", f"{prefix}{msg}")

    # ── Trace-Erstellung ──

    def trace(self, stage: str, action: str, detail: str = "") -> TraceContext:
        """Create a TraceContext for async with."""
        return TraceContext(stage, action, detail)

    @property
    def logs(self) -> list[tuple[str, str, str]]:
        return [(e.timestamp, e.status, f"[{e.stage}] {e.action}") for e in self._trace_log]

    @property
    def trace_log(self) -> list[TraceEntry]:
        return list(self._trace_log)

    def close(self):
        """Close trace file."""
        try:
            self._trace_file.close()
        except Exception:
            pass


# Global access
log = LogManager()
