Project Goal: Implement a high-power, asynchronous Model Context Protocol (MCP) server to act as a specialized research agent for advanced mathematical software development. This plan transitions the initial prototype from a stateless helper to a stateful, knowledge-compounding partner.

Meta-Instruction: The Critical Review Mandate

Before executing any implementation tasks, you must first perform and present a critical review of this entire prompt. Your critique should be structured into the following four sections:

1.  Strengths: Identify which parts of the prompt are clear, well-structured, and follow best practices. Acknowledge the "why" behind good architectural decisions.

2.  Weaknesses & Potential Pitfalls: Identify any ambiguities, potential bottlenecks, or areas where the plan might be brittle or unreliable. Question architectural choices that seem sub-optimal.

3.  Strategic Gaps & Omissions: Point out any missing components or tools that would be valuable for achieving the overall project goal. Have any requirements from the source documents been overlooked?

4.  Opportunities for Brilliance & Refinement Suggestions: Propose specific, actionable improvements. Suggest small changes that could have an outsized impact on the system's robustness, capability, or elegance. Suggest alternative approaches that might be more efficient or powerful.

Only after presenting this critique and receiving confirmation should you proceed with the implementation plan.

Core Architecture:

-   Framework: FastAPI

-   Server: Uvicorn

-   Database (Conversational History): Asynchronous SQLite (via aiosqlite and SQLModel)

-   Knowledge Base (Long-Term Memory): ChromaDB

Implementation Plan: A Step-by-Step Guide

(Please implement the following modules in the order listed to ensure dependencies are met.)

#### Phase 1: Foundational Setup & Data Contracts

Task 1.1: Project Structure & Dependencies

Create the following directory structure to ensure modularity and maintainability:

/research_agent\
|-- main.py\
|-- tools.py\
|-- database.py\
|-- models.py\
|-- exceptions.py\
|-- requirements.txt\
|-- .env

Create a requirements.txt file with the following dependencies:

fastapi==0.110.0\
uvicorn[standard]==0.29.0\
sqlalchemy==2.0.29\
aiosqlite==0.20.0\
sqlmodel==0.0.16\
pydantic==2.7.1\
arxiv==2.1.0\
stackapi==0.2.0\
PyGithub==2.3.0\
httpx==0.27.0\
beautifulsoup4==4.12.3\
chromadb==0.4.24\
python-dotenv==1.0.1

Task 1.2: Define Data Models (models.py)

This module is the single source of truth for all data schemas.

-   ToolCallHistory Model: Define a SQLModel class to serve as the schema for our persistent conversational memory. This is critical for moving beyond a stateless agent. It must include:

-   id: Optional[int] with Field(default=None, primary_key=True)

-   conversation_id: str

-   timestamp: datetime

-   tool_name: str

-   request_params: Dict[str, Any] with Field(sa_column=Column(JSON))

-   response_content: str

-   API Models: Define the Pydantic models for the API contract: ToolParameterProperty, ToolParameters, Tool, ToolExecutionRequest, and ToolExecutionResponse.

Task 1.3: Define Custom Exceptions (exceptions.py)

Create a custom exception class to standardize error handling across all tools.

-   ToolExecutionError: Define a custom exception class that inherits from Exception. All tools will raise this for expected operational failures (e.g., API failures, no results found, parsing errors).

#### Phase 2: The Persistent Core (Database & Knowledge Base)

Task 2.1: Asynchronous Database Setup (database.py)

Centralize all database connection logic here.

-   Database URL: Define DATABASE_URL = "sqlite+aiosqlite:///./research_agent.db".

-   Async Engine: Create the create_async_engine from SQLAlchemy.

-   Session Factory: Create an async_sessionmaker and ensure you set expire_on_commit=False, which is a crucial configuration for async operations.

-   get_session Dependency: Implement the canonical FastAPI dependency using yield within a try...finally block to manage the session lifecycle reliably.

-   init_db Function: Create an async function that uses SQLModel.metadata.create_all(engine) to initialize the database schema.

Task 2.2: Vector Knowledge Base Setup (Update database.py)

This is the core of the "deepthink" capability, creating a compounding knowledge base.

-   ChromaDB Client: Create a persistent client instance: chroma_client = chromadb.PersistentClient(path="./chroma_db").

-   Collection: Get or create a collection named "knowledge_base". This is idempotent and safe for startup routines.

-   get_chroma_client Dependency: Create a simple dependency function that returns the chroma_client instance.

#### Phase 3: The Research Arsenal (tools.py)

This module contains the agent's primary capabilities. Every tool must be an async function and accept a database session (db_session: AsyncSession) to log its execution. All tools must raise the custom ToolExecutionError for predictable failures.

Task 3.1: Knowledge Ingestion Helper

-   add_to_knowledge_base Function: Create an internal async helper function.

-   It must accept content: str, metadata: dict, and an optional chunking_strategy.

-   For long documents, it should split the text into smaller, overlapping chunks before embedding. This improves semantic search quality.

-   It must use a SHA256 hash of the content chunk as the document ID to ensure idempotency when upserting into the ChromaDB "knowledge_base" collection.

Task 3.2: External Research Tools

-   query_arxiv Tool:

-   Use the arxiv library.

-   CRITICAL: Wrap the synchronous library call in asyncio.to_thread to avoid blocking the server's event loop.

-   Return structured JSON, not a single formatted string.

-   After getting results, log the execution to the ToolCallHistory table and call add_to_knowledge_base for each paper abstract.

-   query_stack_exchange Tool:

-   Use the StackAPI library, also wrapped in asyncio.to_thread.

-   Enhance the tool's description to mention advanced search qualifiers like isaccepted:yes and score:10.

-   Log the execution to the database.

-   search_github_code Tool: This is a strategic necessity, moving beyond local search.

-   Use the PyGithub library.

-   Load your GitHub Personal Access Token securely from a .env file (do not hardcode it).

-   Proactively check the API rate limit before executing a search and raise a ToolExecutionError if the limit is low. This is key to robustness.

-   Log the execution to the database.

-   extract_web_content Tool: This is the agent's safety net for reading from any URL.

-   Use the async-native httpx for network requests and BeautifulSoup for parsing.

-   Implement a robust heuristic for content extraction: first try <article>, then <main>, then common IDs like id="content", and finally fall back to all <p> tags.

-   Wrap the entire process in extensive try...except blocks, raising ToolExecutionError for network and parsing failures.

-   Log the execution and ingest the extracted text into ChromaDB using the helper function.

Task 3.3: Internal Research Tools

-   search_internal_knowledge_base Tool: This enables the "memory-first" workflow.

-   This tool should query the ChromaDB collection.

-   Accept query_texts and an optional where_filter to allow for powerful hybrid semantic and metadata searches.

-   The tool's description must instruct the LLM to use this tool first before accessing external APIs.

-   search_local_codebase Tool: This re-introduces the high-value local search utility.

-   Use ripgrep (rg) for fast, local file searching.

-   Use asyncio.create_subprocess_exec for non-blocking execution of the rg command.

-   The tool should search a pre-configured local project directory.

#### Phase 4: API Orchestration (main.py)

This file wires everything together.

Task 4.1: Lifespan Manager

-   Use FastAPI's @asynccontextmanager to create a lifespan function. On startup (yield), call the init_db() function to ensure tables are ready before the server starts.

Task 4.2: API Endpoints

-   /tools Endpoint: Create a GET endpoint that returns the JSON schemas for all available tools. This serves as the agent's discoverable contract.

-   /execute Endpoint: Create a POST endpoint.

-   Use Pydantic models for automatic request validation.

-   Use Depends to inject the database session (get_session) and ChromaDB client (get_chroma_client).

-   Dispatch the request to the correct tool function from tools.py.

-   Wrap the tool execution in a try...except ToolExecutionError block to catch the custom exception and return a structured HTTPException with a 400 status code. Catch any other Exception and return a generic 500 error.