"""Application configuration loaded from environment variables."""

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_path: Path


def load_settings() -> Settings:
    return Settings(database_path=Path(os.getenv("DATABASE_PATH", "data/project.db")))
