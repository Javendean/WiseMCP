import chromadb
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlmodel import SQLModel
from .config import settings

# --- Asynchronous SQL Database (SQLite) Setup ---

# 1. Database URL is now sourced from the central config
DATABASE_URL = settings.DATABASE_URL

# 2. Create Async Engine
# The connect_args are recommended for SQLite to prevent operational errors under high concurrency
engine = create_async_engine(DATABASE_URL, echo=True, connect_args={"check_same_thread": False})

# 3. Create Async Session Factory
# expire_on_commit=False is crucial for FastAPI dependencies and async operations,
# preventing models from being expired after transaction commits.
AsyncSessionFactory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_session() -> AsyncSession:
    """
    FastAPI dependency to get an async database session.
    Yields a session and ensures it's closed after the request.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
        finally:
            await session.close()

async def init_db():
    """
    Initializes the database schema.
    This is called on application startup.
    """
    async with engine.begin() as conn:
        # This command creates all tables defined by SQLModel metadata
        await conn.run_sync(SQLModel.metadata.create_all)


# --- Vector Knowledge Base (ChromaDB) Setup ---

# 1. Create a persistent ChromaDB client
# The path is sourced from the central config
chroma_client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)

# 2. Get or create the "knowledge_base" collection
# This operation is idempotent and safe to run on every startup.
knowledge_base = chroma_client.get_or_create_collection("knowledge_base")

def get_chroma_collection() -> chromadb.Collection:
    """
    FastAPI dependency to get the ChromaDB collection for the knowledge base.
    """
    return knowledge_base
