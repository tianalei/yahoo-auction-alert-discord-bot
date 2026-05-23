"""Load and validate config.yaml; secrets remain in environment variables."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Literal

import yaml

NotificationMode = Literal["bark", "discord"]

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"


@dataclass(frozen=True)
class AppConfig:
    notification: NotificationMode
    check_interval: int
    do_not_run_start_hour: int
    do_not_run_end_hour: int
    timezone: str
    language: str
    exchange_rate: float
    log_level: str
    enable_yahoo_auction: bool
    enable_mercari: bool
    alerts: List[dict]


def _coerce_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "on")
    return bool(value)


def _normalize_alerts(raw_alerts: Any) -> List[dict]:
    if not raw_alerts:
        return []
    alerts: List[dict] = []
    for entry in raw_alerts:
        if isinstance(entry, str):
            name = entry.strip()
            if name:
                alerts.append({"name": name})
        elif isinstance(entry, dict):
            name = str(entry.get("name", "")).strip()
            if name:
                alerts.append({"name": name})
    return alerts


def load_config(config_path: Path | None = None) -> AppConfig:
    path = config_path or Path(os.getenv("CONFIG_PATH", str(DEFAULT_CONFIG_PATH)))
    if not path.is_file():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open(encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f) or {}

    notification = str(data.get("notification", "discord")).strip().lower()
    if notification not in ("bark", "discord"):
        raise ValueError(
            f"Invalid notification mode '{notification}'; expected 'bark' or 'discord'"
        )

    return AppConfig(
        notification=notification,  # type: ignore[arg-type]
        check_interval=int(data.get("check_interval", 60)),
        do_not_run_start_hour=int(data.get("do_not_run_start_hour", 0)),
        do_not_run_end_hour=int(data.get("do_not_run_end_hour", 6)),
        timezone=str(data.get("timezone", "Asia/Shanghai")).strip().strip('"'),
        language=str(data.get("language", "zh-CN")).strip().strip('"'),
        exchange_rate=float(data.get("exchange_rate", 0.0470)),
        log_level=str(data.get("log_level", "INFO")).strip().upper(),
        enable_yahoo_auction=_coerce_bool(data.get("enable_yahoo_auction"), True),
        enable_mercari=_coerce_bool(data.get("enable_mercari"), True),
        alerts=_normalize_alerts(data.get("alerts")),
    )


def setup_logging(log_level: str) -> None:
    logging.basicConfig()
    log_levels = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "WARN": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    level = log_levels.get(log_level.upper(), logging.INFO)
    logging.getLogger().setLevel(level)
    if log_level.upper() in log_levels:
        logging.info("set log level to %s", log_level.upper())
    else:
        logging.info("Invalid LOG_LEVEL '%s', using INFO as default", log_level)


def get_db_path() -> str:
    env = os.getenv("ENV", "dev").lower()
    if env == "prod":
        return "/app/data/alerts.db"
    base_dir = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_dir, "data", "alerts.db")
