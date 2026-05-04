"""
Configuration loader for RAGEve.

Reads configuration from service_conf.yaml with environment variable substitution.
This replaces the old Pydantic-based config.py system to align with RAGEve patterns.

Environment variables take precedence over YAML values.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml

try:
    from dotenv import load_dotenv

    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False


def _substitute_env_vars(value: str) -> str:
    """Replace ${VAR_NAME} or ${VAR_NAME:-default} or $VAR_NAME with env values."""
    if not isinstance(value, str):
        return value

    pattern = r"\$\{([^}:]+)(?::-(.*?))?\}|\$([A-Za-z_][A-Za-z0-9_]*)"

    def replace(match: re.Match[str]) -> str:
        var_name = match.group(1) or match.group(3)
        if var_name is None:
            return match.group(0)
        default = match.group(2)
        if default is not None:
            return os.getenv(var_name, default)
        return os.getenv(var_name, match.group(0))

    return re.sub(pattern, replace, value)


def _deep_substitute(data: Any) -> Any:
    """Recursively substitute environment variables in data structure."""
    if isinstance(data, dict):
        return {k: _deep_substitute(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [_deep_substitute(item) for item in data]
    elif isinstance(data, str):
        return _substitute_env_vars(data)
    else:
        return data


class ConfigSection:
    """A nested configuration section with attribute access."""

    def __init__(self, data: dict[str, Any], prefix: str = ""):
        self._data = data
        self._prefix = prefix

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)
        if name not in self._data:
            raise AttributeError(f"Configuration key '{self._prefix}{name}' not found")
        value = self._data[name]
        if isinstance(value, dict):
            return ConfigSection(value, prefix=f"{self._prefix}{name}.")
        return value

    def get(self, name: str, default: Any = None) -> Any:
        """Get a config value with optional default."""
        return self._data.get(name, default)


class Settings:
    """Global settings object loaded from service_conf.yaml.

    Provides both nested access (settings.mysql.host) for RAGEve compatibility
    and flat access (settings.mysql_host) for backward compatibility.
    """

    # Type hints and fallback defaults for commonly used settings
    max_upload_bytes: int = 500 * 1024 * 1024
    default_chunk_size: int = 1200
    default_chunk_overlap: int = 180
    default_max_tokens_per_chunk: int = 500

    # Legacy attribute mapping: old flat name -> new nested path
    LEGACY_MAP: dict[str, str] = {
        # From limits section
        "max_upload_bytes": "limits_max_upload_bytes",
        "max_dataset_bytes": "limits_max_dataset_bytes",
        # From storage section
        "data_root": "storage_data_root",
        # From chunking section
        "default_chunk_size": "chunking_default_size",
        "default_chunk_overlap": "chunking_default_overlap",
        "default_max_tokens_per_chunk": "chunking_default_max_tokens",
        # From pdf_parsing section
        "enable_column_detection": "pdf_parsing_enable_column_detection",
        "enable_structured_tables": "pdf_parsing_enable_structured_tables",
        "enable_hierarchical_chunking": "pdf_parsing_enable_hierarchical_chunking",
        "enable_reading_order_optimization": "pdf_parsing_enable_reading_order_optimization",
        # From ocr section
        "ocr_engine": "ocr_engine",
        "ocr_threshold_chars": "ocr_threshold_chars",
        # From column_detection section
        "column_histogram_bins": "column_detection_histogram_bins",
        "column_peak_threshold": "column_detection_peak_threshold",
        "column_min_gap": "column_detection_min_gap",
        # From pdfplumber section
        "pdfplumber_table_strategy": "pdfplumber_table_strategy",
        "pdfplumber_snap_tolerance": "pdfplumber_snap_tolerance",
        "pdfplumber_join_tolerance": "pdfplumber_join_tolerance",
        # From logging section
        "log_level": "logging_level",
        # From cors section
        "cors_origins": "cors_origins",
        # From security section
        "api_key": "security_api_key",
        "rate_limit_per_minute": "security_rate_limit_per_minute",
        "trusted_proxy_count": "security_trusted_proxy_count",
        "jwt_secret_key": "security_jwt_secret_key",
        "jwt_expire_minutes": "security_jwt_expire_minutes",
        # From frontend section
        "frontend_url": "frontend_url",
        # From smtp section
        "smtp_dev_mode": "smtp_dev_mode",
        "smtp_host": "smtp_host",
        "smtp_port": "smtp_port",
        "smtp_user": "smtp_user",
        "smtp_password": "smtp_password",
        "smtp_from": "smtp_from",
        "smtp_use_tls": "smtp_use_tls",
        # From huggingface section
        "hf_token": "huggingface_token",
        # From rag section (RAG pipeline configuration)
        "overfetch_multiplier": "rag_overfetch_multiplier",
        "reranker_cache_size": "rag_reranker_cache_size",
        # Database settings (mysql section)
        "mysql_host": "mysql_host",
        "mysql_port": "mysql_port",
        "mysql_user": "mysql_user",
        "mysql_password": "mysql_password",
        "mysql_dbname": "mysql_dbname",
        # Vector DB settings
        "qdrant_url": "qdrant_url",
        "qdrant_api_key": "qdrant_api_key",
        # Ollama settings
        "ollama_base_url": "ollama_base_url",
        "ollama_timeout": "ollama_timeout",
        # App settings
        "app_name": "app_name",
        "app_env": "app_env",
    }

    def __init__(self) -> None:
        self._raw: dict[str, Any] = {}
        self._config_path: Path | None = None
        self._flat_map: dict[str, Any] = {}

        # Load .env file for local development (if present)
        if HAS_DOTENV:
            env_path = Path(".env")
            if env_path.exists():
                load_dotenv(env_path, override=True)
                print(f"[config] Loaded environment from {env_path}")

        self._reload()

    def _reload(self) -> None:
        """Load and parse configuration file."""
        config_paths = [
            Path("/app/conf/service_conf.yaml"),
            Path("/app/service_conf.yaml"),
            Path("docker/conf/service_conf.yaml"),
            Path("docker/service_conf.yaml"),
            Path("service_conf.yaml"),
        ]

        for path in config_paths:
            if path.exists():
                self._config_path = path
                break

        if self._config_path is None:
            raise FileNotFoundError(
                "Could not find service_conf.yaml in any of: "
                + ", ".join(str(p) for p in config_paths)
            )

        with open(self._config_path, encoding="utf-8") as f:
            self._raw = yaml.safe_load(f) or {}

        # Substitute environment variables
        self._raw = _deep_substitute(self._raw)

        # Build flat map
        self._flat_map = self._flatten_dict(self._raw)

        # Set attributes from flat map (backward compatibility)
        for key, value in self._flat_map.items():
            setattr(self, key, value)

        # Coerce known numeric/boolean fields from strings (env var substitution) to proper types
        # This handles cases where ${VAR:-3306} returns "3306" as a string
        _int_keys = {
            "mysql_port",
            "mysql_max_connections",
            "mysql_stale_timeout",
            "mysql_max_allowed_packet",
            "redis_port",
            "redis_db",
            "qdrant_timeout",
            "ollama_timeout",
            "security_rate_limit_per_minute",
            "security_trusted_proxy_count",
            "security_jwt_expire_minutes",
            "storage_upload_dir_name",
            "storage_chunk_dir_name",  # These are actually strings but used in paths
            "chunking_default_size",
            "chunking_default_overlap",
            "chunking_default_max_tokens",
            "pdfplumber_snap_tolerance",
            "pdfplumber_join_tolerance",
            "column_histogram_bins",
            "column_min_gap",
            "column_peak_threshold",
            "limits_max_upload_bytes",
            "limits_max_dataset_bytes",
            "logging_level",  # Actually string but often compared as int in some contexts
            "cache_embedding_ttl",
            "cache_search_ttl",
            "cache_answer_ttl",
            "huggingface_timeout",
            "huggingface_max_retries",
            "rag_overfetch_multiplier",
            "rag_reranker_cache_size",
            "ocr_threshold_chars",
        }
        _float_keys = {
            "pdfplumber_snap_tolerance",
            "pdfplumber_join_tolerance",
            "column_peak_threshold",
            "column_min_gap",
            "rag_reranker_cache_size",  # Can be float too
        }
        _bool_keys = {
            "minio_secure",
            "smtp_use_tls",
            "smtp_dev_mode",
            "pdf_parsing_enable_column_detection",
            "pdf_parsing_enable_structured_tables",
            "pdf_parsing_enable_hierarchical_chunking",
            "pdf_parsing_enable_reading_order_optimization",
        }
        for key in _int_keys:
            if (
                hasattr(self, key)
                and isinstance(getattr(self, key), str)
                and getattr(self, key).isdigit()
            ):
                setattr(self, key, int(getattr(self, key)))
        for key in _float_keys:
            if hasattr(self, key) and isinstance(getattr(self, key), str):
                try:
                    setattr(self, key, float(getattr(self, key)))
                except ValueError:
                    pass  # Keep as string if not parseable
        for key in _bool_keys:
            if hasattr(self, key) and isinstance(getattr(self, key), str):
                val = getattr(self, key).lower()
                if val in ("true", "1", "yes", "on"):
                    setattr(self, key, True)
                elif val in ("false", "0", "no", "off"):
                    setattr(self, key, False)

        # Set nested ConfigSection objects
        for key, value in self._raw.items():
            if isinstance(value, dict):
                setattr(self, key.replace("-", "_"), ConfigSection(value))

        # Set legacy alias attributes (e.g., max_upload_bytes -> limits_max_upload_bytes)
        for legacy_name, new_name in self.LEGACY_MAP.items():
            if hasattr(self, new_name) and not hasattr(self, legacy_name):
                setattr(self, legacy_name, getattr(self, new_name))

        # Set up computed properties
        self._setup_computed_properties()

    def _flatten_dict(self, data: dict[str, Any], prefix: str = "") -> dict[str, Any]:
        """Flatten nested dict into single-level dict with underscored keys."""
        result: dict[str, Any] = {}
        for key, value in data.items():
            flat_key = f"{prefix}{key}".replace("-", "_").lower()
            if isinstance(value, dict):
                result.update(self._flatten_dict(value, f"{flat_key}_"))
            else:
                result[flat_key] = value
        return result

    def _setup_computed_properties(self) -> None:
        """Create computed properties like upload_root, chunk_root, etc."""
        data_root_val = getattr(self, "storage_data_root", "./data")
        data_root = (
            Path(data_root_val) if isinstance(data_root_val, str) else Path("data")
        )
        # Expose data_root as a Path object for path operations (overrides legacy string alias)
        self.data_root = data_root

        # Path properties (backward compatible)
        if not hasattr(self, "upload_root"):
            upload_dir = getattr(self, "storage_upload_dir_name", "uploads")
            self.upload_root = data_root / upload_dir
        if not hasattr(self, "chunk_root"):
            chunk_dir = getattr(self, "storage_chunk_dir_name", "chunks")
            self.chunk_root = data_root / chunk_dir
        if not hasattr(self, "vector_root"):
            vector_dir = getattr(self, "storage_vector_dir_name", "vector")
            self.vector_root = data_root / vector_dir
        if not hasattr(self, "logs_dir"):
            self.logs_dir = data_root / "logs"

        # db_path for SQLite fallback
        if not hasattr(self, "db_path"):
            self.db_path = data_root / "chat.db"

        # Status files
        if not hasattr(self, "hf_status_file"):
            self.hf_status_file = data_root / "hf" / "_download_status.json"
        if not hasattr(self, "ingest_status_file"):
            self.ingest_status_file = data_root / "_ingest_status.json"
        if not hasattr(self, "hf_ingest_status_file"):
            self.hf_ingest_status_file = data_root / "hf" / "_ingest_status.json"

        # Database URL (SQLAlchemy format) for backward compatibility
        # Uses MySQL connection parameters from nested config
        if not hasattr(self, "db_url"):
            mysql_host = getattr(self, "mysql_host", "localhost")
            mysql_port = getattr(self, "mysql_port", 3306)
            mysql_user = getattr(self, "mysql_user", "root")
            mysql_password = getattr(self, "mysql_password", "")
            mysql_dbname = getattr(self, "mysql_dbname", "rag_eve")
            self.db_url = f"mysql://{mysql_user}:{mysql_password}@{mysql_host}:{mysql_port}/{mysql_dbname}"

        # SQLAlchemy connection pool settings
        if not hasattr(self, "db_pool_size"):
            self.db_pool_size = 10
        if not hasattr(self, "db_max_overflow"):
            self.db_max_overflow = 20

        # RAG pipeline settings
        if not hasattr(self, "overfetch_multiplier"):
            self.overfetch_multiplier = 3
        if not hasattr(self, "reranker_cache_size"):
            self.reranker_cache_size = 10

    def reload(self) -> None:
        """Reload configuration from file."""
        self._reload()

    def get(self, key: str, default: Any = None) -> Any:
        """Get a flat config value by key (e.g., 'mysql_host')."""
        return self._flat_map.get(key, default)

    @property
    def config_path(self) -> Path | None:
        return self._config_path


# Global settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


settings = get_settings()

# Export for backward compatibility
__all__ = ["settings", "Settings", "ConfigSection", "get_settings"]
