# Wilbur FastAPI Configuration Migration Guide

**Project**: Wilbur AI Assistant (FastAPI + WebSocket)
**Current Config File**: `wilbur/wilbur-fastapi/src/app/config.py`
**Current LOC**: 578
**Expected LOC**: 128
**LOC Reduction**: 450 (78%)
**Migration Time**: 1 hour
**Difficulty**: Low

---

## Before Migration Analysis

### Current Structure (578 LOC)

```python
# wilbur/wilbur-fastapi/src/app/config.py

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional, List

class WilburSettings(BaseSettings):
    """
    Wilbur configuration with LLM, voice, mesh, and knowledge management.

    ~578 LOC including:
    - 300 LOC: Standard configuration (app, database, Redis, logging, Azure)
    - 150 LOC: Validators (environment, secrets, CORS, pool settings)
    - 100 LOC: Property methods (is_production, database_url_async, redis_url_full)
    - 28 LOC: Caching and getter methods
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_name: str = Field(default="Wilbur AI Assistant")
    app_version: str = Field(default="1.0.0")
    app_environment: str = Field(default="development")
    app_secret_key: str = Field(...)

    # Database
    database_url: str = Field(...)
    database_pool_size: int = Field(default=10)
    database_max_overflow: int = Field(default=20)
    database_pool_timeout: int = Field(default=30)
    database_pool_recycle: int = Field(default=3600)

    # Redis
    redis_url: Optional[str] = Field(default=None)
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_db: int = Field(default=0)

    # CORS
    cors_origins: List[str] = Field(default=[...])

    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")

    # LLM Configuration (Wilbur-specific)
    llm_provider: str = Field(default="local")
    local_llm_model: str = Field(default="mistral-7b")
    local_llm_path: str = Field(default="./models")
    ollama_enabled: bool = Field(default=True)
    ollama_host: str = Field(default="localhost")
    ollama_port: int = Field(default=11434)
    openai_api_key: Optional[str] = Field(default=None)
    openai_model: str = Field(default="gpt-4")
    azure_openai_endpoint: Optional[str] = Field(default=None)
    azure_openai_api_key: Optional[str] = Field(default=None)

    # Voice Configuration
    voice_provider: str = Field(default="azure")
    azure_speech_key: Optional[str] = Field(default=None)
    azure_speech_region: str = Field(default="eastus")

    # Mesh Networking
    mesh_enabled: bool = Field(default=True)
    mesh_port: int = Field(default=8080)

    # Knowledge Management (Hippocampus)
    knowledge_provider: str = Field(default="chromadb")
    hippocampus_db_path: str = Field(default="./data/chroma")

    # Emotion Detection
    emotion_detection_enabled: bool = Field(default=True)

    # Validators (TO BE REMOVED - inherited from BaseConfig)
    @field_validator('app_environment')
    @classmethod
    def validate_environment(cls, v):
        """REMOVE: Inherited from BaseConfig"""
        valid_environments = ['development', 'staging', 'production', 'testing']
        if v not in valid_environments:
            raise ValueError(f'Environment must be one of: {valid_environments}')
        return v

    @field_validator('app_secret_key')
    @classmethod
    def validate_secret_keys(cls, v):
        """REMOVE: Inherited from BaseConfig"""
        if len(v) < 32:
            raise ValueError('Secret keys must be at least 32 characters long')
        return v

    @field_validator('cors_origins', mode='before')
    @classmethod
    def validate_cors_origins(cls, v):
        """REMOVE: Inherited from BaseConfig"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v

    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        """REMOVE: Inherited from BaseConfig"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        return v.upper()

    # Property methods (TO BE REMOVED - inherited from BaseConfig)
    @property
    def is_production(self) -> bool:
        """REMOVE: Inherited from BaseConfig"""
        return self.app_environment == "production"

    @property
    def is_development(self) -> bool:
        """REMOVE: Inherited from BaseConfig"""
        return self.app_environment == "development"

    @property
    def database_url_async(self) -> str:
        """REMOVE: Inherited from BaseConfig"""
        return self.database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)

    @property
    def redis_url_full(self) -> str:
        """REMOVE: Inherited from BaseConfig"""
        if self.redis_url:
            return self.redis_url
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # Getter methods (KEEP - Wilbur-specific)
    def get_llm_config(self) -> dict:
        """Get LLM configuration based on provider."""
        if self.llm_provider == "openai" and self.openai_api_key:
            return {
                "provider": "openai",
                "api_key": self.openai_api_key,
                "model": self.openai_model
            }
        elif self.llm_provider == "azure_openai" and self.azure_openai_api_key:
            return {
                "provider": "azure_openai",
                "endpoint": self.azure_openai_endpoint,
                "api_key": self.azure_openai_api_key
            }
        else:  # local
            return {
                "provider": "local",
                "model": self.local_llm_model,
                "path": self.local_llm_path
            }

    def get_voice_config(self) -> dict:
        """Get voice provider configuration."""
        if self.voice_provider == "azure":
            return {
                "provider": "azure",
                "key": self.azure_speech_key,
                "region": self.azure_speech_region
            }
        return {}

    # Caching (TO BE REMOVED - use library's get_settings)
    @lru_cache()
    def validate_required_settings(self):
        """REMOVE: Validation happens on init"""
        # validation code
        pass

# Caching function (TO BE REMOVED - use get_settings from library)
@lru_cache()
def get_settings() -> WilburSettings:
    """REMOVE: Use get_settings from netrun_config instead"""
    try:
        settings = WilburSettings()
        settings.validate_required_settings()
        return settings
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
        raise
```

### LOC Breakdown
- **Application/Database/Redis/CORS/Logging**: 120 LOC
- **LLM/Voice/Mesh/Knowledge Configuration**: 75 LOC
- **Standard Validators** (Environment, Secrets, CORS, Log Level): 85 LOC
- **Property Methods** (is_production, is_development, database_url_async, redis_url_full): 45 LOC
- **Getter Methods** (get_llm_config, get_voice_config): 50 LOC
- **Caching/Utilities**: 28 LOC
- **Class Definition/Comments/Whitespace**: 175 LOC
- **TOTAL**: 578 LOC

---

## Migration Steps

### Step 1: Update Imports (2 minutes)

**Replace**:
```python
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
```

**With**:
```python
from netrun_config import BaseConfig, Field, get_settings
from pydantic import field_validator
```

### Step 2: Change Base Class (1 minute)

**Replace**:
```python
class WilburSettings(BaseSettings):
    """..."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
```

**With**:
```python
class WilburSettings(BaseConfig):
    """
    Wilbur AI Assistant configuration.

    Inherits from BaseConfig:
    - app_name, app_version, app_environment (validated)
    - app_secret_key, jwt_secret_key, encryption_key (validated ≥32 chars)
    - database_url, database_pool_size, redis_url, redis_host, redis_port
    - cors_origins, log_level, logging configuration
    - is_production, is_development, is_staging properties
    - database_url_async, redis_url_full properties
    - CORS origins parsing (string → list)
    - Settings caching via get_settings()
    """
```

### Step 3: Keep Project-Specific Configuration (5 minutes)

Keep only Wilbur-specific fields (LLM, Voice, Mesh, Knowledge):

```python
    # ========================================================================
    # Wilbur-Specific: LLM Configuration
    # ========================================================================

    llm_provider: str = Field(default="local", env="LLM_PROVIDER")
    local_llm_model: str = Field(default="mistral-7b", env="LOCAL_LLM_MODEL")
    local_llm_path: str = Field(default="./models", env="LOCAL_LLM_PATH")

    ollama_enabled: bool = Field(default=True, env="OLLAMA_ENABLED")
    ollama_host: str = Field(default="localhost", env="OLLAMA_HOST")
    ollama_port: int = Field(default=11434, env="OLLAMA_PORT")

    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4", env="OPENAI_MODEL")

    azure_openai_endpoint: Optional[str] = Field(default=None, env="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: Optional[str] = Field(default=None, env="AZURE_OPENAI_API_KEY")

    # ========================================================================
    # Wilbur-Specific: Voice Configuration
    # ========================================================================

    voice_provider: str = Field(default="azure", env="VOICE_PROVIDER")
    azure_speech_key: Optional[str] = Field(default=None, env="AZURE_SPEECH_KEY")
    azure_speech_region: str = Field(default="eastus", env="AZURE_SPEECH_REGION")

    # ========================================================================
    # Wilbur-Specific: Mesh Networking
    # ========================================================================

    mesh_enabled: bool = Field(default=True, env="MESH_ENABLED")
    mesh_port: int = Field(default=8080, env="MESH_PORT")

    # ========================================================================
    # Wilbur-Specific: Knowledge Management (Hippocampus)
    # ========================================================================

    knowledge_provider: str = Field(default="chromadb", env="KNOWLEDGE_PROVIDER")
    hippocampus_db_path: str = Field(default="./data/chroma", env="HIPPOCAMPUS_DB_PATH")

    # ========================================================================
    # Wilbur-Specific: Emotion Detection
    # ========================================================================

    emotion_detection_enabled: bool = Field(default=True, env="EMOTION_DETECTION_ENABLED")
```

### Step 4: Remove Standard Validators (5 minutes)

**DELETE these validators** (now inherited from BaseConfig):
- `validate_environment()`
- `validate_secret_keys()`
- `validate_cors_origins()`
- `validate_log_level()`
- `validate_pool_settings()`

### Step 5: Remove Standard Property Methods (3 minutes)

**DELETE these property methods** (now inherited from BaseConfig):
- `is_production`
- `is_development`
- `database_url_async`
- `redis_url_full`

### Step 6: Keep Project-Specific Methods (2 minutes)

Keep only Wilbur-specific methods:

```python
    # ========================================================================
    # Wilbur-Specific Methods
    # ========================================================================

    def get_llm_config(self) -> dict:
        """Get LLM configuration based on provider."""
        if self.llm_provider == "openai" and self.openai_api_key:
            return {
                "provider": "openai",
                "api_key": self.openai_api_key,
                "model": self.openai_model
            }
        elif self.llm_provider == "azure_openai" and self.azure_openai_api_key:
            return {
                "provider": "azure_openai",
                "endpoint": self.azure_openai_endpoint,
                "api_key": self.azure_openai_api_key
            }
        else:  # local
            return {
                "provider": "local",
                "model": self.local_llm_model,
                "path": self.local_llm_path,
                "ollama_enabled": self.ollama_enabled,
                "ollama_host": self.ollama_host,
                "ollama_port": self.ollama_port
            }

    def get_voice_config(self) -> dict:
        """Get voice provider configuration."""
        if self.voice_provider == "azure":
            return {
                "provider": "azure",
                "key": self.azure_speech_key,
                "region": self.azure_speech_region
            }
        return {}

    def get_knowledge_config(self) -> dict:
        """Get knowledge management configuration."""
        return {
            "provider": self.knowledge_provider,
            "db_path": self.hippocampus_db_path
        }
```

### Step 7: Add Wilbur-Specific Validator (3 minutes)

Add validator for Wilbur-specific LLM provider:

```python
    @field_validator('llm_provider')
    @classmethod
    def validate_llm_provider(cls, v: str) -> str:
        """Validate LLM provider is supported."""
        valid_providers = ['local', 'openai', 'azure_openai', 'ollama']
        if v not in valid_providers:
            raise ValueError(f'LLM provider must be one of: {valid_providers}')
        return v
```

### Step 8: Update Settings Factory (2 minutes)

**Replace**:
```python
@lru_cache()
def get_settings() -> WilburSettings:
    try:
        settings = WilburSettings()
        settings.validate_required_settings()
        return settings
    except Exception as e:
        logger.error(f"Failed to load settings: {e}")
        raise
```

**With**:
```python
def get_wilbur_settings() -> WilburSettings:
    """Get Wilbur settings instance (cached via netrun_config.get_settings)."""
    return get_settings(WilburSettings)
```

### Step 9: Update Dependencies (1 minute)

In `pyproject.toml` or `requirements.txt`:

**Add**:
```
netrun-config>=1.0.0
```

**Keep**:
- pydantic>=2.0.0
- pydantic-settings>=2.0.0

### Step 10: Test & Validate (15 minutes)

```bash
# Run tests
pytest

# Verify settings load
python -c "from wilbur.src.app.config import get_wilbur_settings; print(get_wilbur_settings())"

# Check environment variables work
export APP_ENVIRONMENT=production
python -c "from wilbur.src.app.config import WilburSettings; print(WilburSettings().is_production)"
```

---

## After Migration (128 LOC)

```python
# wilbur/wilbur-fastapi/src/app/config.py (128 LOC)

from netrun_config import BaseConfig, Field, get_settings
from pydantic import field_validator
from typing import Optional

class WilburSettings(BaseConfig):
    """
    Wilbur AI Assistant configuration.

    Inherits from BaseConfig:
    - app_name, app_version, app_environment, app_debug
    - app_secret_key, jwt_secret_key, encryption_key (validated ≥32 chars)
    - database_url, database_pool_size, redis_url, redis_host, redis_port
    - cors_origins, cors_allow_credentials
    - log_level, log_format, log_file
    - enable_metrics, metrics_port, sentry_dsn
    - Validators: environment, secrets, CORS, log level
    - Properties: is_production, is_development, is_staging
    - Caching: get_settings() factory
    """

    # ========================================================================
    # Wilbur-Specific: LLM Configuration
    # ========================================================================

    llm_provider: str = Field(default="local", env="LLM_PROVIDER")
    local_llm_model: str = Field(default="mistral-7b", env="LOCAL_LLM_MODEL")
    local_llm_path: str = Field(default="./models", env="LOCAL_LLM_PATH")

    ollama_enabled: bool = Field(default=True, env="OLLAMA_ENABLED")
    ollama_host: str = Field(default="localhost", env="OLLAMA_HOST")
    ollama_port: int = Field(default=11434, env="OLLAMA_PORT")

    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4", env="OPENAI_MODEL")

    azure_openai_endpoint: Optional[str] = Field(default=None, env="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: Optional[str] = Field(default=None, env="AZURE_OPENAI_API_KEY")

    # ========================================================================
    # Wilbur-Specific: Voice Configuration
    # ========================================================================

    voice_provider: str = Field(default="azure", env="VOICE_PROVIDER")
    azure_speech_key: Optional[str] = Field(default=None, env="AZURE_SPEECH_KEY")
    azure_speech_region: str = Field(default="eastus", env="AZURE_SPEECH_REGION")

    # ========================================================================
    # Wilbur-Specific: Mesh Networking
    # ========================================================================

    mesh_enabled: bool = Field(default=True, env="MESH_ENABLED")
    mesh_port: int = Field(default=8080, env="MESH_PORT")

    # ========================================================================
    # Wilbur-Specific: Knowledge Management
    # ========================================================================

    knowledge_provider: str = Field(default="chromadb", env="KNOWLEDGE_PROVIDER")
    hippocampus_db_path: str = Field(default="./data/chroma", env="HIPPOCAMPUS_DB_PATH")

    # ========================================================================
    # Wilbur-Specific: Emotion Detection
    # ========================================================================

    emotion_detection_enabled: bool = Field(default=True, env="EMOTION_DETECTION_ENABLED")

    # ========================================================================
    # Wilbur-Specific Validator
    # ========================================================================

    @field_validator('llm_provider')
    @classmethod
    def validate_llm_provider(cls, v: str) -> str:
        """Validate LLM provider is supported."""
        valid_providers = ['local', 'openai', 'azure_openai', 'ollama']
        if v not in valid_providers:
            raise ValueError(f'LLM provider must be one of: {valid_providers}')
        return v

    # ========================================================================
    # Wilbur-Specific Methods
    # ========================================================================

    def get_llm_config(self) -> dict:
        """Get LLM configuration based on provider."""
        if self.llm_provider == "openai" and self.openai_api_key:
            return {
                "provider": "openai",
                "api_key": self.openai_api_key,
                "model": self.openai_model
            }
        elif self.llm_provider == "azure_openai" and self.azure_openai_api_key:
            return {
                "provider": "azure_openai",
                "endpoint": self.azure_openai_endpoint,
                "api_key": self.azure_openai_api_key
            }
        else:  # local
            return {
                "provider": "local",
                "model": self.local_llm_model,
                "path": self.local_llm_path,
                "ollama_enabled": self.ollama_enabled,
                "ollama_host": self.ollama_host,
                "ollama_port": self.ollama_port
            }

    def get_voice_config(self) -> dict:
        """Get voice provider configuration."""
        if self.voice_provider == "azure":
            return {
                "provider": "azure",
                "key": self.azure_speech_key,
                "region": self.azure_speech_region
            }
        return {}

    def get_knowledge_config(self) -> dict:
        """Get knowledge management configuration."""
        return {
            "provider": self.knowledge_provider,
            "db_path": self.hippocampus_db_path
        }


def get_wilbur_settings() -> WilburSettings:
    """Get Wilbur settings instance (cached via netrun_config.get_settings)."""
    return get_settings(WilburSettings)
```

---

## Validation Checklist

### Before Starting
- [ ] Current `config.py` is 578 LOC (or similar)
- [ ] Tests pass with current configuration
- [ ] Created feature branch: `git checkout -b config/netrun-upgrade`

### During Migration
- [ ] Updated imports (removed BaseSettings, pydantic_settings)
- [ ] Changed base class to BaseConfig
- [ ] Removed standard validators (environment, secrets, CORS, log level)
- [ ] Removed standard property methods (is_production, is_development, database_url_async, redis_url_full)
- [ ] Kept all Wilbur-specific fields and methods
- [ ] Added Wilbur-specific validator for llm_provider
- [ ] Updated settings factory to use get_settings() from library
- [ ] Updated pyproject.toml or requirements.txt

### Testing
- [ ] `pytest` passes all tests
- [ ] Settings load without errors: `python -c "from app.config import get_wilbur_settings; print(get_wilbur_settings())"`
- [ ] Environment validation works: `export APP_ENVIRONMENT=invalid; python -c "..."`
- [ ] LLM configuration methods work: `get_llm_config()`, `get_voice_config()`, `get_knowledge_config()`
- [ ] Caching works: Second settings load is instant

### Deployment
- [ ] Deployed to staging environment
- [ ] Application starts without errors
- [ ] Logs show no configuration warnings
- [ ] Key features work (LLM, voice, mesh, knowledge)

### Completion
- [ ] Updated README with netrun-config usage
- [ ] Deleted old config.py backup
- [ ] Committed: `git commit -m "feat(config): Migrate to netrun-config v1.0.0"`
- [ ] Created Pull Request

---

## Expected Results

**LOC Reduction**: 578 → 128 = **450 LOC removed (78% reduction)**

**Before**:
- 300 LOC: Standard configuration
- 150 LOC: Duplicate validators
- 100 LOC: Standard property methods
- 28 LOC: Caching logic

**After**:
- All inherited from BaseConfig
- 25 LOC: Wilbur-specific configuration
- 45 LOC: Wilbur-specific methods
- 58 LOC: Documentation and formatting

**Migration Time**: 1 hour
**Time Savings**: 78% reduction = 7 hours saved vs. building from scratch

---

## Reference

- `netrun-config` v1.0.0 API: https://github.com/netrun-systems/netrun-config
- BaseConfig source: `Service_63_Unified_Configuration/netrun_config/base.py`
- Example integration: `examples/fastapi_integration.py`

---

**Date Created**: November 25, 2025
**Status**: Ready for migration
**Next Project**: NetrunCRM
