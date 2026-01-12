from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings
import os


# Extract database path and create directory if needed
db_path = settings.DATABASE_URL.replace("sqlite+aiosqlite:///", "")
if db_path.startswith("./"):
    # Relative path - resolve from current working directory
    db_dir = os.path.dirname(os.path.abspath(db_path))
else:
    # Absolute path
    db_dir = os.path.dirname(db_path)

if db_dir:
    os.makedirs(db_dir, exist_ok=True)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Run migrations for existing databases
    await run_migrations()


async def run_migrations():
    """Run database migrations for existing databases"""
    from sqlalchemy import text
    
    async with engine.begin() as conn:
        # Check if admin_pinned column exists in workspaces table
        try:
            result = await conn.execute(text("SELECT admin_pinned FROM workspaces LIMIT 1"))
        except Exception:
            # Column doesn't exist, add it
            print("Adding admin_pinned column to workspaces table...")
            await conn.execute(text("ALTER TABLE workspaces ADD COLUMN admin_pinned BOOLEAN DEFAULT 0"))
            print("Migration complete: admin_pinned column added")
        
        # Check if sound_enabled column exists in workspaces table
        try:
            result = await conn.execute(text("SELECT sound_enabled FROM workspaces LIMIT 1"))
        except Exception:
            # Column doesn't exist, add it
            print("Adding sound_enabled column to workspaces table...")
            await conn.execute(text("ALTER TABLE workspaces ADD COLUMN sound_enabled BOOLEAN DEFAULT 1"))
            print("Migration complete: sound_enabled column added")
        
        # Add rag_mode column to workspaces if it doesn't exist
        try:
            await conn.execute(text("SELECT rag_mode FROM workspaces LIMIT 1"))
        except Exception:
            print("Adding rag_mode column to workspaces table...")
            await conn.execute(text("ALTER TABLE workspaces ADD COLUMN rag_mode TEXT DEFAULT 'global'"))
            print("Migration complete: rag_mode column added")
        
        # Create rag_evaluations table if it doesn't exist
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS rag_evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workspace_id INTEGER NOT NULL,
                document_id INTEGER NOT NULL,
                document_name TEXT,
                question TEXT NOT NULL,
                rag_response TEXT,
                rag_context_tokens INTEGER,
                rag_response_tokens INTEGER,
                rag_time_seconds REAL,
                rag_chunks_retrieved INTEGER,
                cag_response TEXT,
                cag_context_tokens INTEGER,
                cag_response_tokens INTEGER,
                cag_time_seconds REAL,
                rag_scores JSON,
                cag_scores JSON,
                winner TEXT,
                reasoning TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER
            )
        """))
        
        # Create system_settings table if it doesn't exist
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS system_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT,
                value_type TEXT DEFAULT 'string',
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Create A/B test tables if they don't exist
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ab_test_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                anythingllm_url TEXT NOT NULL,
                anythingllm_workspace TEXT NOT NULL,
                privateai_url TEXT NOT NULL,
                privateai_workspace_id INTEGER NOT NULL,
                num_queries INTEGER NOT NULL,
                num_documents INTEGER NOT NULL,
                anythingllm_avg_latency REAL,
                anythingllm_avg_faithfulness REAL,
                anythingllm_avg_relevancy REAL,
                anythingllm_recall REAL,
                anythingllm_mrr REAL,
                privateai_avg_latency REAL,
                privateai_avg_faithfulness REAL,
                privateai_avg_relevancy REAL,
                privateai_recall REAL,
                privateai_mrr REAL,
                winner TEXT,
                winner_reason TEXT,
                status TEXT DEFAULT 'pending',
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                created_by INTEGER
            )
        """))
        
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ab_test_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                query_id TEXT NOT NULL,
                query TEXT NOT NULL,
                category TEXT,
                difficulty TEXT,
                ground_truth_docs JSON,
                anythingllm_answer TEXT,
                anythingllm_latency REAL,
                anythingllm_faithfulness REAL,
                anythingllm_relevancy REAL,
                anythingllm_retrieved_docs JSON,
                anythingllm_recall REAL,
                anythingllm_mrr REAL,
                privateai_answer TEXT,
                privateai_latency REAL,
                privateai_faithfulness REAL,
                privateai_relevancy REAL,
                privateai_retrieved_docs JSON,
                privateai_recall REAL,
                privateai_mrr REAL,
                winner TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ab_test_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                file_type TEXT,
                file_size INTEGER,
                anythingllm_uploaded INTEGER DEFAULT 0,
                privateai_uploaded INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Create API keys table
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                key TEXT UNIQUE NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMP,
                expires_at TIMESTAMP
            )
        """))
