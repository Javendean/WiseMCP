A Refined Implementation Plan for a High-Power Research Agent MCP Server
========================================================================

Part I: A Production-Grade Blueprint for the Research MCP Server
----------------------------------------------------------------

This section provides a definitive and actionable implementation plan, refining the initial concepts outlined in the "Server Efficiency for Solo Developer" document. The focus is on transforming the proposed architecture from a functional prototype into a robust, production-grade system. The plan details the necessary code structures, architectural patterns, and best practices required to build a high-power Model Context Protocol (MCP) server using a modern, asynchronous Python stack. The architectural choices herein are deliberately prescriptive, designed to equip a solo developer with a foundation that prioritizes not only immediate performance but also long-term maintainability and extensibility, directly addressing the core objective of creating an agent with "maximum research power".1

### 4.1 The Core Server: A Resilient FastAPI Foundation with Persistent State

The foundation of any powerful application is its core architecture. While the initial analysis correctly identified FastAPI as the optimal framework, this refined plan elevates the server from a simple, stateless request-response mechanism to a stateful application capable of complex, multi-turn reasoning and long-term learning. This is achieved by introducing a persistent, asynchronous database backend, a critical component for any system intended for serious research.

#### 4.1.1 Refining the Application Structure for Maintainability

A solo developer's most valuable resource is time. A well-organized codebase minimizes cognitive overhead and accelerates development. The initial plan's monolithic main.py file is sufficient for a simple demonstration but becomes a bottleneck to productivity as complexity grows.1 Therefore, the first prescriptive step is to modularize the application into a logical directory structure. This separation of concerns is a standard practice in professional software development and is essential for building a maintainable system.

The recommended structure is as follows:

-   main.py: This file will contain only the FastAPI application instance, the lifespan context manager for startup/shutdown events, and the definitions of the API endpoints (/tools, /execute). It serves as the main entry point to the application.

-   tools.py: This module will house the implementation logic for all agent-facing tools, such as query_arxiv and search_github_code. This keeps the core business logic separate from the web framework wiring.

-   database.py: This module is responsible for all database-related setup. It will define the database connection engine, the session maker, and the dependency function for providing database sessions to the endpoints.

-   models.py: This module will contain all data model definitions, including the Pydantic models for API request/response validation and the SQLModel (or SQLAlchemy) classes that define the database table structures.

This structure ensures that each file has a single, clear responsibility, making the system easier to understand, debug, and extend over time.

#### 4.1.2 Implementing Persistent State with aiosqlite and SQLAlchemy

The original plan's suggestion of using an in-memory dictionary for state management is a critical architectural flaw for a research agent.1 Such a solution is volatile, meaning all conversational context and research history are lost the moment the server restarts. It offers no transactional safety and cannot be queried in any meaningful way. To build a "deepthink" agent, a more robust solution is not optional; it is mandatory.

The recommended architecture replaces this fragile approach with a persistent, file-based SQLite database, accessed asynchronously to align with the FastAPI event loop. This choice is deliberate: SQLite requires no separate server process, making it exceptionally lightweight and simple for a solo developer to manage, while still providing the power of a full-featured SQL database.2 To interact with it asynchronously, the

aiosqlite driver is the standard and recommended choice for use with SQLAlchemy's asynchronous engine.3

The implementation will be centralized in the database.py module. This module will establish the core components for database interaction:

1.  Database URL Definition: A DATABASE_URL constant will be defined using the format "sqlite+aiosqlite:///./research_agent.db", which specifies the use of the aiosqlite driver with a local database file named research_agent.db.2

2.  Asynchronous Engine Creation: An async_engine will be created using create_async_engine(DATABASE_URL). This object manages the low-level connectivity to the database.

3.  Session Factory: An AsyncSessionMaker will be created using async_sessionmaker(engine, expire_on_commit=False). The expire_on_commit=False argument is crucial for asynchronous applications, as it prevents SQLAlchemy from invalidating object state after a transaction commits, a necessary configuration when working within an asyncio environment.2

4.  Session Dependency: A FastAPI dependency function, get_session, will be implemented. This function will use a try...finally block with yield to create a new AsyncSession for each incoming request, provide it to the endpoint, and ensure the session is closed correctly afterward, even if errors occur.2 This pattern is the canonical way to manage database connections cleanly and reliably in FastAPI.

5.  Database Initialization: An init_db function will be created to issue CREATE TABLE commands based on the defined models. This function will be called once at application startup using FastAPI's lifespan context manager, ensuring the database schema is in place before the server begins accepting requests.2

#### 4.1.3 The Paradigm Shift to Persistent Conversational Memory

The introduction of a persistent database is more than a technical upgrade; it represents a fundamental paradigm shift in the agent's capabilities. The system moves beyond simple "state management"---the temporary tracking of variables within a single interaction---to the creation of a Persistent Conversational Memory.

With a volatile in-memory dictionary, the agent is forgetful. It cannot recall past conversations or build upon previous research sessions. Each interaction starts from a blank slate. This severely limits its ability to perform the kind of deep, longitudinal research implied by the "deepthink" objective.1

By implementing a ToolCallHistory table in the SQLite database, every single tool execution---every query to arXiv, every search on GitHub---is recorded permanently. This log captures the tool that was called, the parameters it was given, the exact result it returned, and a timestamp. This transforms the agent's operational history from an ephemeral stream of events into a structured, queryable archive.

The agent can now be endowed with the ability to reflect on its own past work. It could be asked, "What were the most relevant papers I found yesterday when searching for 'attention mechanisms'?" or "Show me the code snippets I retrieved last week related to JAX." These queries are impossible for a stateless agent but are simple SQL queries for an agent with a persistent memory. This historical log is the foundational prerequisite for true learning and knowledge synthesis. It is the raw material from which all higher-order intelligence, including the vector-based knowledge base discussed later, will be built.

To formalize this architectural decision, the following table contrasts the two approaches.

Table 4.1: State Management Architecture Comparison

|

Feature

 |

In-Memory Dictionary (Original Proposal)

 |

Persistent SQLite (aiosqlite) (Recommended)

 |
|

Persistence

 |

Volatile. All data is lost on server restart.

 |

Durable. Data persists across server restarts and application sessions.

 |
|

Data Integrity

 |

None. No transactional guarantees or ACID compliance.

 |

High. Provides ACID compliance through SQLite's transactional nature.

 |
|

Query Capability

 |

Basic key-value lookup only. Cannot filter or aggregate data.

 |

Rich. Supports the full SQL query language for complex filtering, ordering, and aggregation.

 |
|

Scalability

 |

Poor. Strictly limited by available server RAM.

 |

High. Limited by available disk space, which is far more abundant.

 |
|

Foundation for AI Memory

 |

Poor. Provides no historical data for learning or embedding.

 |

Excellent. Creates a structured, permanent log of all research activities, which is the ideal source for vector embedding.

 |
|

Implementation Complexity

 |

Very Low. A single line of code.

 |

Low-to-Moderate. Requires initial setup, but patterns are well-established and reusable.2

 |

#### 4.1.4 Defining Data Contracts with SQLModel and Pydantic

To enforce data integrity at both the API and database layers, the system will leverage SQLModel. SQLModel is a library that elegantly combines the functionality of Pydantic and SQLAlchemy, allowing a single class definition to serve as both a Pydantic model for API validation and a SQLAlchemy model for database table representation.2 This reduces code duplication and ensures consistency between the data the API accepts and the data it stores.

In the models.py file, a ToolCallHistory class will be defined. This model will serve as the schema for the persistent conversational memory log. It will include fields such as:

-   id: An auto-incrementing integer primary key.

-   conversation_id: A string or UUID to group related tool calls.

-   timestamp: A datetime field, automatically populated, to record when the tool was executed.

-   tool_name: A string for the name of the executed tool.

-   request_params: A JSON field to store the dictionary of parameters sent to the tool.

-   response_content: A Text field to store the full string result returned by the tool.

The Pydantic models from the original plan, such as ToolExecutionRequest and ToolExecutionResponse, will be retained. FastAPI will use these models to automatically validate incoming requests from the Gemini agent and serialize outgoing responses, providing a robust, type-safe API contract that mitigates the "Parameter Mismatch" problem identified in the initial analysis.1

### 4.2 The High-Power Research Tool Arsenal

The true power of the agent is realized through the capabilities of its tools. This section details the implementation of a versatile and potent toolset designed to fulfill the agent's core research mission. Each tool will be implemented as an async function within the tools.py module. Critically, every tool execution will conclude by writing a record of its activity to the ToolCallHistory table via the database session provided by FastAPI's dependency injection system.

#### 4.2.1 Tool 1 & 2: Refined query_arxiv and query_stack_exchange

The tool implementations for querying arXiv and Stack Exchange from the original blueprint serve as a solid foundation.1 The key refinement is ensuring they operate correctly within the asynchronous ASGI architecture. Libraries like

arxiv and StackAPI are synchronous; their network operations are blocking.1 Calling them directly within an

async function would freeze the server's event loop, defeating the purpose of using an asynchronous framework.

The correct pattern, demonstrated in the initial code, is to wrap the synchronous library calls with asyncio.to_thread. This function runs the blocking code in a separate thread from a worker pool managed by the asyncio event loop, thus offloading the blocking work and keeping the main loop responsive. This "asynchronous wrapper pattern" is essential for integrating the vast ecosystem of synchronous Python libraries into a modern ASGI application.

Further refinements include:

-   Structured Output: Instead of returning a single, large, formatted string, the tools will be modified to return a JSON string representing a list of result objects. Each object will contain distinct fields like title, authors, summary, and link. This structured data is far more useful for the agent, as it can be easily parsed and used as input for subsequent tool calls (e.g., a summarization or analysis tool).

-   Enhanced Descriptions: The JSON schema description for the query_stack_exchange tool will be updated to explicitly guide the LLM on how to use advanced search qualifiers. The description will mention operators like isaccepted:yes, answers:1, and score:10, empowering the agent to formulate more precise and effective queries beyond simple keywords.5

#### 4.2.2 Tool 3: search_github_code (Global Code Search)

The original plan's search_codebase tool, which uses ripgrep, is a valuable utility for inspecting a local project.1 However, the agent's mission is to research the implementation of

advanced mathematical reasoning models, which are developed and shared in public repositories across the globe. A local search tool is insufficient for this global research task.

Therefore, a new and far more powerful tool, search_github_code, is introduced. This tool moves beyond the local filesystem to search the entirety of GitHub's public code. This is not merely an enhancement; it is a strategic necessity to fulfill the agent's primary objective. It creates a powerful research workflow where the agent can discover a seminal paper on arXiv and immediately search for its open-source implementation on GitHub, directly connecting theory with practice.

The implementation will leverage the PyGithub library, a mature and widely used Python wrapper for the GitHub REST API.6

-   Core Functionality: The tool will be built around the github.search_code() method.7 It will construct a query string that combines user-provided keywords with powerful search qualifiers supported by the GitHub API, such as\
    repo: to scope the search to a specific repository (e.g., repo:google/jax), language: to filter by programming language, in:file to search only file contents, and extension: to find specific file types.9

-   Authentication: The GitHub API requires authentication for most non-trivial requests. The tool will be configured to securely load a GitHub Personal Access Token from an environment variable (e.g., GITHUB_TOKEN), avoiding the insecure practice of hardcoding credentials.10

-   Rate Limiting: The GitHub Search API has a particularly strict rate limit, separate from the core API limit. A well-behaved client must respect these limits. Before executing a search, the tool will use the g.get_rate_limit() method to check the status of the search resource.8 If the remaining requests are low, the tool will not proceed with the search and will instead return a clear message to the agent (e.g., "GitHub search API rate limit is low. Please try again later."). This prevents unexpected failures and makes the agent more robust.

#### 4.2.3 Tool 4: extract_web_content (General Web Extraction)

The agent's research cannot be confined to platforms that offer structured APIs. Critical information---such as an author's explanatory blog post, official library documentation, or a university research page---often exists only on the open web. The extract_web_content tool serves as the agent's "safety net" and "creativity engine," giving it the ability to ingest knowledge from any URL. This capability makes the agent more robust, as it has a fallback when a specific API is unavailable, and more creative, as it can synthesize information from a much wider and more diverse range of sources.

This tool will be implemented using the requests (or an async-native equivalent like httpx) and BeautifulSoup libraries.12

-   Fetching and Parsing: The tool will take a url as input. It will perform an HTTP GET request to fetch the raw HTML content and then parse it into a BeautifulSoup object for traversal and analysis.13

-   Content Extraction: The primary challenge in web scraping is distinguishing the main article content from boilerplate elements like navigation bars, sidebars, and footers.14 A perfect solution is impossible, but a robust heuristic-based approach is highly effective. The tool will first search for semantic HTML5 tags like\
    <article> and <main>. If these are not found, it will look for common div IDs or classes like id="content", id="main", or class="post-content". As a final fallback, it can concatenate the text content from all <p> tags within the <body>.14

-   Error Handling and Cleanup: The tool must be wrapped in extensive try...except blocks to gracefully handle network errors, HTTP error codes, request timeouts, and HTML parsing errors. The extracted text will be cleaned to remove excessive newlines and whitespace before being returned to the agent. The unstructured and often noisy nature of this tool's output makes it a prime candidate for later ingestion into the ChromaDB vector store, where its semantic meaning can be indexed and made searchable.

The complete suite of tools provides the agent with a comprehensive arsenal for conducting deep software development research. The following table summarizes their contracts.

Table 4.2: Refined Research Tool Suite

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

Part II: The Strategic Trajectory: From Research Assistant to Knowledge Partner
-------------------------------------------------------------------------------

This section outlines the strategic path to elevate the agent from a reactive tool-using assistant to a proactive knowledge partner. It reframes the "future trajectory" concepts from the original document as an immediate and actionable strategy, focusing on the implementation of a persistent, long-term memory as the central pillar of the agent's "deepthink" capability.

### 5.1 The Immediate Next Step: Building a Persistent Knowledge Base with ChromaDB

An agent that can only fetch data is merely a convenient API wrapper. An agent that learns from and remembers its research becomes a true intellectual partner. The "maximum research power" objective is not fully met until the agent can synthesize past findings and avoid re-discovering the same information repeatedly. Therefore, the integration of a vector database is not a deferred "future" enhancement; it is the core value proposition of the system and the most critical step after the foundational tools are in place.

#### 5.1.1 Architectural Justification and Implementation Plan

ChromaDB is selected as the vector database for this project due to its open-source nature, focus on developer experience, and simplicity of deployment---all ideal characteristics for a solo developer's workflow.15 The implementation will use ChromaDB's persistent client mode, which stores the database on the local filesystem, requiring no additional server management.5

The implementation plan is as follows:

1.  Setup: The chromadb Python package will be installed.15 A singleton client instance will be created in the application using\
    chromadb.PersistentClient(path="/path/to/chroma_db"), where the path points to a directory on the local disk.5

2.  Collection Creation: A single ChromaDB collection will serve as the agent's entire long-term memory. It will be created using client.get_or_create_collection(name="knowledge_base"). This function is idempotent, meaning it will safely create the collection if it doesn't exist or retrieve the existing one if it does, making it ideal for use in the application's startup sequence.15

3.  Data Ingestion Pipeline: A new asynchronous function, add_to_knowledge_base(content: str, metadata: dict), will be created. This function will be the sole entry point for adding information to the agent's memory. It will be called from within the primary research tools. For example, after query_arxiv successfully retrieves a set of papers, it will iterate through them and call add_to_knowledge_base for each paper's abstract.

-   This pipeline will use the collection.upsert() method to add documents.15\
    upsert is critically important as it prevents the creation of duplicate entries if the agent happens to research the same source multiple times.

-   A unique ID for each document will be generated by creating a SHA256 hash of its content, ensuring idempotency.

-   Rich metadata is essential for enabling powerful, filtered queries. The metadata dictionary will be structured to include the source of the information (e.g., 'arxiv', 'github'), a timestamp, the source_id (e.g., the arXiv paper ID or the URL of the web page), and the original_query that led to the discovery of this information.5

#### 5.1.2 Tool 5: search_internal_knowledge_base

With the knowledge base in place, the agent needs a tool to access it. The search_internal_knowledge_base tool allows the agent to query its own memory.

-   Functionality: The tool will accept a query_texts list of search terms and an optional where_filter dictionary. It will execute the search using collection.query(query_texts=..., n_results=5, where=where_filter).15

-   Filtered Semantic Search: The where filter is a powerful feature that allows the LLM to combine semantic similarity search with structured metadata filtering. For example, the agent could ask to "find information about 'recurrent neural networks' but only from 'arxiv' sources published after a certain date." This hybrid search capability is a hallmark of a sophisticated retrieval system.18

-   Strategic Prompting: The tool's description in the agent's prompt will be carefully crafted to instruct the LLM to use this tool first before querying any external APIs. This creates a "memory-first" workflow, making the agent more efficient and capable of connecting new queries to past findings.

The following table defines the proposed schema for the documents stored within the ChromaDB collection, providing a clear data model for the agent's long-term memory.

Table 5.1: Proposed ChromaDB Collection Schema

|

Field Name

 |

Type

 |

Description

 |

Example

 |
|

id

 |

string (Primary Key)

 |

A unique SHA256 hash of the document content to prevent duplicates.

 |

a1b2c3d4...

 |
|

document

 |

string

 |

The text chunk to be embedded (e.g., paper abstract, code snippet, web content).

 |

"The attention mechanism allows the model to focus on relevant parts of the input..."

 |
|

metadata.source

 |

string

 |

The origin of the data.

 |

'arxiv', 'github', 'web', 'stack_exchange'

 |
|

metadata.source_id

 |

string

 |

The unique identifier from the source system.

 |

'1706.03762v5', 'https://.../main.py'

 |
|

metadata.ingest_timestamp

 |

integer (Unix)

 |

The timestamp when the document was added to the knowledge base.

 |

1672531200

 |
|

metadata.original_query

 |

string

 |

The query that led to the discovery of this document.

 |

"transformer architecture"

 |

### 5.2 Advanced Horizons: Proactive Intelligence and Specialized Reasoning

With a robust, memory-enabled foundation in place, the platform is well-positioned to support more advanced and speculative capabilities. These future enhancements build upon the core architecture to further push the boundaries of what a personalized research agent can achieve.

#### 5.2.1 Proactive Context Injection

This capability shifts the agent from a purely reactive system to one that can anticipate the user's needs. Instead of waiting for a question, the system can proactively research topics based on the user's current activity within their development environment.

An architectural sketch for this feature would involve a separate, lightweight "watcher" process running on the developer's machine. This process could use a library like watchdog to monitor filesystem events. When the user opens or modifies a source code file, the watcher would send a request to a new, internal-only endpoint on the MCP server (e.g., /proactive_research). This endpoint would then trigger the relevant research tools---search_github_code for related open-source examples, search_stack_exchange for common errors or questions related to the libraries used in the file---and silently ingest the results into the ChromaDB knowledge base. The next time the developer asks a question, the agent's context is already "warm," primed with highly relevant, up-to-the-minute information about the exact code they are working on.

#### 5.2.2 Custom Tool for LaTeX Parsing

Given the agent's focus on researching mathematical models, it will inevitably encounter mathematical notation expressed in LaTeX. While the project constraints forbid the agent from solving equations, it can be given tools to process and understand the notation to aid its research.

A new tool, process_latex_string, could be created to handle this.

-   Input: A string containing a LaTeX expression (e.g., $\sigma(z)_i = \frac{e^{z_i}}{\sum_{j=1}^{K} e^{z_j}}$).

-   Functionality:

1.  Rendering for Visualization: The tool could use a library like matplotlib and its mathtext engine to render the LaTeX string into a PNG image. It would return a local file path or a base64-encoded image string, allowing the agent to "show" the formatted equation to the user for visual confirmation.

2.  Parsing for Semantic Search: More powerfully, the tool could use a symbolic mathematics library like SymPy to parse the LaTeX string into a symbolic expression. It would not evaluate the expression but would return a string representation of its structure.

-   Use Case: This enables a powerful new research loop. The agent, while analyzing a paper, could extract a key equation, use this tool to parse it, and then use the identified components (e.g., "softmax," "exponential function") as new, highly specific search terms for query_arxiv or search_github_code. This allows the agent to deconstruct mathematical concepts and search for their constituent parts, a sophisticated research strategy that fully respects the "no direct computation" constraint.

#### Works cited

1.  Server Efficiency for Solo Developer_.docx

2.  AI-TUTOR Part 1: Building Async CRUD API with FastAPI, SQLModel, and SQLite - Medium, accessed August 6, 2025, <https://medium.com/@dharamai2024/ai-tutor-part-1-building-async-crud-api-with-fastapi-sqlmodel-and-sqlite-0edf3041511d>

3.  SQLAlchemy - FastAPI Users, accessed August 6, 2025, <https://fastapi-users.github.io/fastapi-users/13.0/configuration/databases/sqlalchemy/>

4.  seapagan/fastapi_async_sqlalchemy2_example: A Simple example how to use FastAPI with Async SQLAlchemy 2.0 - GitHub, accessed August 6, 2025, <https://github.com/seapagan/fastapi_async_sqlalchemy2_example>

5.  Getting Started with Chroma DB: A Beginner's Tutorial | by Random-long-int - Medium, accessed August 6, 2025, <https://medium.com/@pierrelouislet/getting-started-with-chroma-db-a-beginners-tutorial-6efa32300902>

6.  PyGithub/PyGithub: Typed interactions with the GitHub API v3 - GitHub, accessed August 6, 2025, <https://github.com/PyGithub/PyGithub>

7.  Main class: Github --- PyGithub 0.1.dev50+gbccc5aa documentation, accessed August 6, 2025, <https://pygithub.readthedocs.io/en/latest/github.html>

8.  Main class: Github --- PyGithub 1.59.1 documentation - Read the Docs, accessed August 6, 2025, <https://pygithub.readthedocs.io/en/v1.59.1/github.html>

9.  Search | GitHub API - LFE Documentation, accessed August 6, 2025, <https://docs2.lfe.io/v3/search/>

10. gh-search - PyPI, accessed August 6, 2025, <https://pypi.org/project/gh-search/>

11. A Python Script to connect to GitHub and Fetches Search Results - DEV Community, accessed August 6, 2025, <https://dev.to/ajeetraina/a-python-script-to-connect-to-github-and-fetches-search-results-38jk>

12. Extracting Data from HTML with BeautifulSoup - Pluralsight, accessed August 6, 2025, <https://www.pluralsight.com/resources/blog/guides/extracting-data-html-beautifulsoup>

13. Python Web Scraping Tutorial - GeeksforGeeks, accessed August 6, 2025, <https://www.geeksforgeeks.org/python/python-web-scraping-tutorial/>

14. How to extract only main content of text from a web page? : r/learnpython - Reddit, accessed August 6, 2025, <https://www.reddit.com/r/learnpython/comments/lv8i2j/how_to_extract_only_main_content_of_text_from_a/>

15. Getting Started - Chroma Docs, accessed August 6, 2025, <https://docs.trychroma.com/getting-started>

16. Learn How to Use Chroma DB: A Step-by-Step Guide | DataCamp, accessed August 6, 2025, <https://www.datacamp.com/tutorial/chromadb-tutorial-step-by-step-guide>

17. Chroma Docs: Introduction, accessed August 6, 2025, <https://docs.trychroma.com/>

18. ChromaDB using Python. - YouTube, accessed August 6, 2025, <https://www.youtube.com/watch?v=FBcWDPY2DaU>