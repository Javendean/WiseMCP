Implementation Guide: High-Power Research Agent MCP Server
==========================================================

Introduction
------------

This document provides the definitive implementation plan for a high-power, asynchronous Model Context Protocol (MCP) server. The primary objective is to construct a specialized research agent for advanced mathematical software development, capable of supporting the creation of deep reasoning models. This guide supersedes all previous plans, adopting a production-grade architecture engineered for maximum performance, robustness, and long-term extensibility.1

The server architecture is founded upon three critical principles that collectively transform the agent from a simple command-executor into a sophisticated research partner:

1.  Asynchronous Performance: The system leverages an ASGI-native stack, specifically FastAPI and the Uvicorn server. This event-driven model is intrinsically suited for the I/O-bound nature of research tasks---querying external APIs, reading from databases, and accessing web content. By handling these operations concurrently without blocking, the server ensures a highly responsive and efficient agent experience, which is a core requirement for achieving "maximum research power".1

2.  Persistent State: The architecture moves beyond volatile, in-memory state management to a robust, persistent backend using an asynchronous SQLite database. This creates a "Persistent Conversational Memory," a permanent, queryable log of every tool execution. This statefulness is the prerequisite for complex, multi-turn reasoning, historical analysis, and enabling the agent to learn from its own operational history.1

3.  Compounding Knowledge: The system integrates a vector database, ChromaDB, to build a long-term, semantically searchable knowledge base. By embedding and storing the findings from its research activities, the agent creates a compounding memory. This elevates its function from a reactive tool-user that repeatedly rediscovers information to a proactive knowledge partner that synthesizes past findings to inform current tasks.1

Section 1: Project Initialization and Environment Setup
-------------------------------------------------------

This section establishes the foundational project structure and dependencies. Adhering to these conventions is the first step toward building a clean, maintainable, and reproducible development environment.

### 1.1 Prescribed Directory Structure

To ensure long-term maintainability and minimize cognitive overhead, the project must be modularized. A strict separation of concerns is a standard practice in professional software development and is essential for managing complexity as the system grows.1 The following directory structure is prescribed:

-   main.py: This file serves as the main entry point to the application. Its responsibility is limited to instantiating the FastAPI application, defining the lifespan context manager for startup and shutdown events, and declaring the API endpoints (/tools, /execute).1

-   tools.py: This module houses the core business logic for all agent-facing research tools, such as query_arxiv and search_github_code. This isolates the implementation details of the tools from the web framework wiring.1

-   database.py: This module centralizes all database-related setup and configuration. It is responsible for defining the database connection engine, the session factory, and the dependency injection function that provides database sessions to the API endpoints.1

-   models.py: This module contains all data schema definitions. This includes the Pydantic models used for API request and response validation, as well as the SQLModel (or SQLAlchemy) classes that define the structure of the database tables.1

### 1.2 Core Dependencies and Environment

The selection of Python libraries for this project is deliberate, reflecting a philosophy of building an anti-fragile system that proactively mitigates common failure points. For instance, the combination of FastAPI and Pydantic provides automatic, out-of-the-box data validation at the API edge. This directly solves the "Parameter Mismatch" problem---where the LLM might hallucinate or misinterpret tool parameters---a critical fragility identified in earlier analyses.1 Furthermore, the use of SQLModel unifies the API and database schemas into single class definitions, drastically reducing the risk of data-layer inconsistencies and saving significant debugging time by catching errors early and providing clear, structured feedback.1

The following table specifies the complete set of required Python packages. This list should be used to create a requirements.txt file to ensure a reproducible build environment.

|

Package

 |

Version (Recommended)

 |

Description

 |
|

fastapi

 |

^0.110.0

 |

The core ASGI web framework for building the API.1

 |
|

uvicorn[standard]

 |

^0.29.0

 |

The high-performance ASGI server to run the FastAPI application.1

 |
|

sqlalchemy

 |

^2.0

 |

The SQL toolkit and Object-Relational Mapper (ORM) for database interaction.1

 |
|

aiosqlite

 |

^0.20.0

 |

The asynchronous driver for SQLite, enabling non-blocking database operations.1

 |
|

sqlmodel

 |

^0.0.16

 |

Combines Pydantic and SQLAlchemy to define data models with a single syntax.1

 |
|

pydantic

 |

^2.0

 |

Provides data validation and settings management using Python type hints.1

 |
|

arxiv

 |

^2.1.0

 |

A Python wrapper for the arXiv API to search for academic papers.1

 |
|

stackapi

 |

^0.2.0

 |

A Python wrapper for the Stack Exchange API.1

 |
|

PyGithub

 |

^2.3.0

 |

A Python library to access the GitHub REST API v3.1

 |
|

httpx

 |

^0.27.0

 |

A fully featured async-capable HTTP client for Python.1

 |
|

beautifulsoup4

 |

^4.12.3

 |

A library for pulling data out of HTML and XML files.1

 |
|

chromadb

 |

^0.4.24

 |

The open-source embedding database for the agent's long-term memory.1

 |

Section 2: The Persistent Core - Database and Data Models
---------------------------------------------------------

This section details the construction of the server's memory foundation. This implementation represents a paradigm shift from a stateless helper to a stateful research partner, capable of recalling and reflecting upon its past actions.1

### 2.1 Defining Data Contracts (models.py)

The models.py file will define the data structures for the entire application. The central component of the agent's memory is the ToolCallHistory table. By using SQLModel, a single class definition serves as both the Pydantic model for API validation and the SQLAlchemy model for the database table, which ensures consistency and reduces code duplication.1

The following table provides the formal definition for the ToolCallHistory model, which will serve as the blueprint for the agent's "Persistent Conversational Memory."

|

Field Name

 |

Type (SQL & Python)

 |

Description

 |
|

id

 |

INTEGER / Optional[int]

 |

An auto-incrementing integer that serves as the primary key.

 |
|

conversation_id

 |

VARCHAR / str

 |

A string or UUID used to group a sequence of related tool calls.

 |
|

timestamp

 |

DATETIME / datetime

 |

A timestamp, automatically populated, recording when the tool was executed.

 |
|

tool_name

 |

VARCHAR / str

 |

The name of the tool that was executed (e.g., 'query_arxiv').

 |
|

request_params

 |

JSON / Dict[str, Any]

 |

A JSON field storing the dictionary of parameters sent to the tool.

 |
|

response_content

 |

TEXT / str

 |

A text field storing the full string result returned by the tool.

 |

### 2.2 Asynchronous Database Engine (database.py)

The database.py module will centralize all database interaction logic, adhering to established best practices for managing asynchronous database connections within a FastAPI application.1 The implementation will consist of the following components:

-   Database URL: A constant will define the connection string for the database. For a lightweight, file-based setup ideal for a solo developer, this will be DATABASE_URL = "sqlite+aiosqlite:///./research_agent.db".1

-   Asynchronous Engine: An asynchronous engine object will be created using create_async_engine(DATABASE_URL). This object manages the low-level connectivity to the database file.1

-   Session Factory: An AsyncSessionMaker will be created via async_sessionmaker(engine, expire_on_commit=False). The expire_on_commit=False argument is a critical configuration for asynchronous applications, as it prevents SQLAlchemy from invalidating object state after a transaction commits, which is necessary when working within an asyncio event loop.1

-   Session Dependency: A FastAPI dependency function, get_session, will be implemented. This function will use a try...finally block with yield to create a new AsyncSession for each incoming request, provide it to the endpoint logic, and guarantee that the session is closed correctly afterward, even in the event of an error. This is the canonical pattern for reliable session management in FastAPI.1

-   Database Initialization: An async function, init_db, will be created. This function will use the engine to emit CREATE TABLE statements based on the metadata defined in the SQLModel classes. This function is designed to be called once at application startup.1

This persistent ToolCallHistory log is more than a simple audit trail; it is the foundational layer of the agent's memory. It represents a verifiable, factual record of its own operations, enabling it to answer questions like, "What were the exact parameters I used to search GitHub last week?" This historical record is the raw data that can later be mined for patterns, used for fine-tuning, or fed into the vector database, marking the first and most crucial step toward building an agent that genuinely learns and improves.1

Section 3: The Asynchronous Server - API and Endpoints (main.py)
----------------------------------------------------------------

This section details the construction of the main application file, main.py. This file serves as the web-facing interface, orchestrating the interaction between the Gemini agent and its powerful new toolset.

### 3.1 Application Instantiation and Lifespan Management

The main.py file will begin by instantiating the FastAPI application: app = FastAPI(...). A critical feature to implement is the lifespan context manager. This FastAPI feature allows for the execution of code on application startup and shutdown. The init_db() function from database.py will be called within the startup portion of this manager. This guarantees that the database schema and all necessary tables are created and ready before the server begins to accept any incoming requests, preventing race conditions and runtime errors.1

### 3.2 Tool Discovery Endpoint (/tools)

A GET /tools endpoint must be defined. The purpose of this endpoint is to allow the Gemini agent to discover the capabilities of the MCP server. It will return a JSON array containing the schema definitions for all available tools. This schema, which includes the tool's name, a natural language description, and a detailed parameter specification, serves as a machine-readable contract that guides the agent's tool selection and usage logic.1

### 3.3 Tool Execution Endpoint (/execute)

The workhorse of the server is the POST /execute endpoint. This endpoint is responsible for receiving tool execution requests from the agent and dispatching them to the appropriate implementation logic. Its design incorporates several key features for robustness:

-   Pydantic Validation: The endpoint will use a Pydantic model, ToolExecutionRequest, to define the expected structure of the incoming request body. FastAPI uses this model to automatically parse and validate the JSON payload from the agent. If the request is malformed (e.g., wrong data types, missing required fields), FastAPI will intercept it and return a detailed 422 Unprocessable Entity error message before the tool's logic is ever executed. This robustly solves the "Parameter Mismatch" problem by creating a strict, enforceable contract.1

-   Database Session Injection: The endpoint will use the get_session dependency defined in database.py to acquire a database session for the duration of the request. This session will be passed to the executed tool function, enabling it to write a record of its activity to the ToolCallHistory table.1

-   Structured Response: The endpoint will return a response that conforms to a ToolExecutionResponse Pydantic model, ensuring a consistent and predictable output format for the agent.1

This combination of a discovery endpoint and a Pydantic-validated execution endpoint creates a strong, explicit, and self-documenting contract between the LLM and the server. This architecture replaces fragile, implicit agreements based on natural language descriptions with a machine-readable schema that is programmatically enforced. This provides a crucial feedback loop that is vastly superior for debugging and enables a sophisticated agent to potentially self-correct its own malformed requests.1

Section 4: The Research Arsenal - Tool Implementation (tools.py)
----------------------------------------------------------------

This section details the implementation of the core research tools within the tools.py module. Each tool is a self-contained capability, designed from the ground up with asynchronicity, structured data handling, and persistent logging in mind.

### 4.1 Core Implementation Pattern

All tools must be implemented as async functions. A mandatory pattern for any tool that relies on a synchronous third-party library (such as arxiv or StackAPI) is the use of asyncio.to_thread. This function runs the blocking I/O code in a separate thread from a worker pool managed by the asyncio event loop. This offloads the blocking work, keeping the main server process responsive and able to handle other requests. Calling a blocking function directly within an async endpoint would freeze the entire server, defeating the purpose of the asynchronous architecture.1 Furthermore, every tool function must accept the database session as an argument and conclude its execution by writing a comprehensive record of the call and its result to the

ToolCallHistory table.1

### 4.2 Tool Implementations

-   query_arxiv: This tool will use the arxiv library to search the preprint server. The library's synchronous search methods must be wrapped in asyncio.to_thread. A critical refinement is that the tool must return a structured JSON string representing a list of paper objects, each with distinct fields like title, authors, summary, and link. This is far more useful to the agent than a single, large formatted string. After fetching results, the tool will log the call and the JSON result to the database.1

-   query_stack_exchange: This tool will use the StackAPI library, also wrapped in asyncio.to_thread. To empower the agent to perform more effective searches, the tool's JSON schema description will be enhanced to explicitly mention advanced search qualifiers like isaccepted:yes, answers:1, and score:10. Like the arXiv tool, it will return structured JSON and log its execution.1

-   search_github_code: This tool is a strategic necessity, moving beyond local codebase searches to query the entirety of public code on GitHub. It will be implemented using the PyGithub library. The implementation must include three key features for robustness: 1) Securely loading a GitHub Personal Access Token from an environment variable (e.g., GITHUB_TOKEN) to avoid hardcoding credentials. 2) Proactively checking the API rate limit using g.get_rate_limit() before executing a search, and returning an informative message if the limit is low to prevent unexpected failures. 3) Logging every search execution to the database.1

-   extract_web_content: This tool serves as the agent's "safety net" for ingesting information from any URL. It will use the async-native httpx library for network requests and BeautifulSoup for parsing. It must implement a robust heuristic-based approach for content extraction: first searching for semantic HTML tags (<article>, <main>), then for common div IDs (id="content"), and finally falling back to concatenating all <p> tags. The entire process must be wrapped in extensive try...except blocks to gracefully handle network errors, HTTP errors, and parsing failures. The execution and the extracted text must be logged.1

### 4.3 Consolidated Tool Contracts

The following table serves as the "source of truth" for the agent's tool definitions. The JSON schemas defined here will be served by the /tools endpoint, forming the explicit contract between the agent and the server.

|

Tool Name (name)

 |

LLM-Facing Description (description)

 |

Parameters (JSON Schema Snippet)

 |
|

query_arxiv

 |

Searches the arXiv.org preprint server for academic papers. Use for questions about scientific research, mathematical proofs, computer science algorithms, and machine learning models. Returns a JSON list of results.

 |

{"query": {"type": "string"}, "max_results": {"type": "integer", "default": 5}}

 |
|

query_stack_exchange

 |

Searches a specified Stack Exchange site. Use for practical coding questions and technical issues. Use advanced qualifiers like isaccepted:yes in the query for better results.

 |

{"site": {"type": "string", "enum": ["stackoverflow", "math.stackexchange.com"]}, "query": {"type": "string"}}

 |
|

search_github_code

 |

Searches for code snippets in all public GitHub repositories. Use qualifiers like repo:owner/name, language:python, or extension:py in the query to narrow results.

 |

{"query": {"type": "string", "description": "Search keywords and qualifiers."}}

 |
|

extract_web_content

 |

Fetches and extracts the main text content from a given URL. Use for reading blog posts, documentation, or other web pages without a formal API.

 |

{"url": {"type": "string", "description": "The full URL of the web page to read."}}

 |

This curated toolset is not merely a list of functions; it enables an integrated workflow that mirrors a human expert's research process. An expert might read a paper (query_arxiv), search for its open-source implementation (search_github_code), read related documentation (extract_web_content), and troubleshoot issues with community help (query_stack_exchange). By providing this exact suite of tools, the system empowers the agent to follow this same powerful, multi-modal research pattern, directly fulfilling the "deep research" objective.1

Section 5: The Knowledge Partner - Long-Term Vector Memory
----------------------------------------------------------

This section details the implementation of the agent's long-term memory, which is the most critical component for elevating it to a "deepthink" partner. The integration of a persistent, searchable vector database is not a future enhancement but the core value proposition of this architecture.1

### 5.1 Vector Store Initialization

ChromaDB is selected for its simplicity and developer-friendly, open-source nature. It will be run in its persistent client mode, which stores the database on the local filesystem and requires no separate server process to manage---an ideal setup for a solo developer.1

-   Client Setup: A singleton ChromaDB client instance will be created using chromadb.PersistentClient(path="/path/to/chroma_db"), where the path points to a local directory.1

-   Collection Creation: A single collection will serve as the agent's entire long-term memory. It will be created or retrieved using client.get_or_create_collection(name="knowledge_base"). This function is idempotent, making it safe to call during the application's startup sequence, which should be handled via the lifespan manager in main.py.1

### 5.2 Knowledge Base Schema

To enable powerful, filtered semantic search, the documents stored in ChromaDB must contain rich metadata alongside the text content. The following schema defines the structure for each entry in the knowledge_base collection.

|

Field Name

 |

Type

 |

Description

 |
|

id

 |

string (Primary Key)

 |

A unique SHA256 hash of the document content to prevent duplicates.

 |
|

document

 |

string

 |

The text chunk to be embedded (e.g., paper abstract, code snippet).

 |
|

metadata.source

 |

string

 |

The origin of the data (e.g., 'arxiv', 'github', 'web').

 |
|

metadata.source_id

 |

string

 |

The unique identifier from the source system (e.g., arXiv ID, URL).

 |
|

metadata.ingest_timestamp

 |

integer (Unix)

 |

The timestamp when the document was added to the knowledge base.

 |
|

metadata.original_query

 |

string

 |

The user or agent query that led to the discovery of this document.

 |

### 5.3 Knowledge Ingestion and Retrieval

-   Ingestion Pipeline: An internal, asynchronous function, add_to_knowledge_base(content: str, metadata: dict), will be the sole entry point for adding information to the agent's memory. This function will be called by the primary research tools after they successfully retrieve information. For example, query_arxiv will iterate through its results and call this function for each paper's abstract. The implementation must use the collection.upsert() method. Using upsert with a content-derived hash as the ID is critically important, as it ensures idempotency and prevents the creation of duplicate entries if the agent researches the same source multiple times.1

-   Retrieval Tool: A new agent-facing tool, search_internal_knowledge_base, must be implemented. This tool allows the agent to query its own memory. It will accept query_texts (a list of search strings) and an optional where_filter dictionary. The tool will execute collection.query(..., where=where_filter), enabling powerful hybrid search that combines semantic similarity with structured metadata filtering. For example, the agent could search for "information about 'recurrent neural networks' but only from 'arxiv' sources." The tool's description must be crafted to instruct the LLM to use this tool first before querying external APIs, establishing a "memory-first" workflow.1

This ChromaDB integration creates a virtuous cycle of intelligence. The agent performs research, the results are ingested into its long-term memory, and subsequent queries begin by searching this internal knowledge base. The agent no longer needs to re-discover information; it retrieves what it already knows and builds upon it. The system's value and intelligence compound with every interaction, which is the essence of the "deepthink" capability.1

Section 6: Advanced Horizons and Final Execution
------------------------------------------------

With the robust, memory-enabled foundation in place, the architecture is well-positioned to support more advanced capabilities. This final section provides instructions for running the server and outlines the future potential unlocked by this design.

### 6.1 Scaffolding for Specialization

The core architecture (FastAPI, SQLite, ChromaDB) is domain-agnostic. The specialization for a domain like "math competition problems" is achieved by adding new, specialized tools. The modular structure of the project is designed to make adding such tools a clean and simple process. Future enhancements that build upon this foundation include:

-   Proactive Context Injection: A separate "watcher" process could use a library like watchdog to monitor the developer's filesystem. When a source code file is opened or modified, this process could trigger research tools to silently find related examples or documentation and ingest them into the ChromaDB knowledge base. The developer's agent would then be "pre-warmed" with relevant context before a question is even asked.1

-   Custom LaTeX Parsing: Given the focus on mathematical models, a tool to process LaTeX notation would be invaluable. A process_latex_string tool could be created using libraries like matplotlib to render an equation (e.g., σ(z)i​=∑j=1K​ezj​ezi​​) as an image for visualization, or SymPy to parse it into a symbolic expression. The agent could then use the parsed components as new, highly specific search terms, enabling it to deconstruct mathematical concepts and research their constituent parts---a sophisticated research strategy.1

### 6.2 Final Configuration and Execution

To run the server, two final steps are required:

1.  Environment Variables: The search_github_code tool requires authentication to interact with the GitHub API. A Personal Access Token must be generated on GitHub and made available to the application through an environment variable. Set this variable in the terminal before launching the server:\
    export GITHUB_TOKEN='your_github_personal_access_token'

2.  Server Execution Command: Navigate to the root directory of the project in the terminal. Use the Uvicorn ASGI server to run the FastAPI application. The --reload flag is recommended for development, as it will automatically restart the server whenever code changes are detected.\
    uvicorn main:app --reload

Upon execution, the server will start, initialize the database and ChromaDB collection via the lifespan manager, and begin listening for requests from the Gemini agent at the /tools and /execute endpoints.

#### Works cited

1.  Agent for Mathematical Software Development_.docx