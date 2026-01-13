from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Any, Dict
from app.models.system_settings import SystemSettings
from app.core.config import settings as env_settings


# Settings that can be managed via Admin UI
# Format: key -> (env_attr, value_type, description)
ADMIN_SETTINGS = {
    # App
    "app_name": ("APP_NAME", "string", "Application name shown in UI"),
    
    # LLM
    "llm_model": ("LLM_MODEL", "string", "LLM model name"),
    "llm_temperature": ("LLM_TEMPERATURE", "float", "LLM temperature (0.0-2.0)"),
    "llm_top_p": ("LLM_TOP_P", "float", "LLM top_p sampling (0.0-1.0)"),
    "llm_repetition_penalty": ("LLM_REPETITION_PENALTY", "float", "Repetition penalty (1.0-2.0)"),
    
    # Default RAG Settings
    "default_top_n": ("DEFAULT_TOP_N", "int", "Default chunks to retrieve (1-20)"),
    "default_similarity_threshold": ("DEFAULT_SIMILARITY_THRESHOLD", "float", "Default similarity threshold (0.0-1.0)"),
    "default_use_hybrid_search": ("DEFAULT_USE_HYBRID_SEARCH", "bool", "Use hybrid search by default"),
    
    # RAG Presets
    "rag_precise_top_n": ("RAG_PRECISE_TOP_N", "int", "Precise mode: chunks to retrieve"),
    "rag_precise_threshold": ("RAG_PRECISE_THRESHOLD", "float", "Precise mode: similarity threshold"),
    "rag_comprehensive_top_n": ("RAG_COMPREHENSIVE_TOP_N", "int", "Comprehensive mode: chunks to retrieve"),
    "rag_comprehensive_threshold": ("RAG_COMPREHENSIVE_THRESHOLD", "float", "Comprehensive mode: similarity threshold"),
    
    # Features
    "mcp_enabled": ("MCP_ENABLED", "bool", "Enable MCP tool calling (web search)"),
    "pdf_provider": ("PDF_PROVIDER", "string", "PDF processing provider"),
    
    # Vector Store
    "vector_store": ("VECTOR_STORE", "string", "Vector database: qdrant or lancedb"),
    
    # System Prompt
    "default_system_prompt": ("DEFAULT_SYSTEM_PROMPT", "string", "Default system prompt for new workspaces"),
}


class SettingsService:
    """Service for managing system settings with DB override of .env defaults."""
    
    async def get(self, db: AsyncSession, key: str) -> Any:
        """Get a setting value. DB value overrides .env default."""
        # Check DB first
        result = await db.execute(
            select(SystemSettings).where(SystemSettings.key == key)
        )
        db_setting = result.scalar_one_or_none()
        
        if db_setting and db_setting.value is not None:
            return db_setting.typed_value
        
        # Fall back to .env
        if key in ADMIN_SETTINGS:
            env_attr = ADMIN_SETTINGS[key][0]
            return getattr(env_settings, env_attr, None)
        
        return None
    
    async def get_all(self, db: AsyncSession) -> Dict[str, Any]:
        """Get all admin-configurable settings with current values."""
        settings_dict = {}
        
        # Get all DB settings
        result = await db.execute(select(SystemSettings))
        db_settings = {s.key: s for s in result.scalars().all()}
        
        # Build response with DB values or .env defaults
        for key, (env_attr, value_type, description) in ADMIN_SETTINGS.items():
            if key in db_settings and db_settings[key].value is not None:
                value = db_settings[key].typed_value
                source = "database"
            else:
                value = getattr(env_settings, env_attr, None)
                source = "default"
            
            settings_dict[key] = {
                "value": value,
                "type": value_type,
                "description": description,
                "source": source,
            }
        
        return settings_dict
    
    async def set(self, db: AsyncSession, key: str, value: Any) -> bool:
        """Set a setting value in DB (overrides .env)."""
        if key not in ADMIN_SETTINGS:
            return False
        
        value_type = ADMIN_SETTINGS[key][1]
        description = ADMIN_SETTINGS[key][2]
        
        # Convert value to string for storage
        str_value = str(value) if value is not None else None
        
        # Upsert
        result = await db.execute(
            select(SystemSettings).where(SystemSettings.key == key)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            existing.value = str_value
            existing.value_type = value_type
        else:
            db.add(SystemSettings(
                key=key,
                value=str_value,
                value_type=value_type,
                description=description
            ))
        
        await db.commit()
        return True
    
    async def reset(self, db: AsyncSession, key: str) -> bool:
        """Reset a setting to .env default (delete from DB)."""
        result = await db.execute(
            select(SystemSettings).where(SystemSettings.key == key)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            await db.delete(existing)
            await db.commit()
        
        return True
    
    async def reset_all(self, db: AsyncSession) -> bool:
        """Reset all settings to .env defaults."""
        result = await db.execute(select(SystemSettings))
        for setting in result.scalars().all():
            await db.delete(setting)
        await db.commit()
        return True


settings_service = SettingsService()
