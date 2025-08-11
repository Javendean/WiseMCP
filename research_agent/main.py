import uuid
from contextlib import asynccontextmanager
from typing import List, Dict, Coroutine

from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from chromadb import Collection

from . import database, models, tools, exceptions, latex_tools

# --- Tool Integration ---

ALL_TOOLS_SCHEMA = tools.AVAILABLE_TOOLS_SCHEMA + latex_tools.LATEX_TOOLS_SCHEMA
ALL_TOOL_FUNCTIONS: Dict[str, Coroutine] = {**tools.TOOL_FUNCTIONS, **latex_tools.LATEX_TOOL_FUNCTIONS}

# --- Application Lifecycle ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Initializes the database connection on startup.
    """
    print("Starting up...")
    await database.init_db()
    print("Database initialized.")
    yield
    print("Shutting down...")

app = FastAPI(
    title="WiseMCP Research Agent",
    description="An asynchronous agent for advanced mathematical software development research.",
    version="1.1.0", # Version bump for new feature
    lifespan=lifespan
)

# --- Exception Handling ---

@app.exception_handler(exceptions.ToolExecutionError)
async def tool_execution_exception_handler(request: Request, exc: exceptions.ToolExecutionError):
    """
    Global exception handler for custom ToolExecutionError.
    Returns a structured JSON error response.
    """
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=exc.to_json(),
    )

# --- API Endpoints ---

@app.get("/tools", response_model=List[models.Tool])
async def get_tools() -> List[models.Tool]:
    """
    Lists all available tools with their schemas.
    """
    return ALL_TOOLS_SCHEMA

@app.post("/execute", response_model=models.ToolExecutionResponse)
async def execute_tool(
    request: models.ToolExecutionRequest,
    db_session: AsyncSession = Depends(database.get_session),
    chroma_collection: Collection = Depends(database.get_chroma_collection),
) -> models.ToolExecutionResponse:
    """
    Executes a specified tool with the given parameters.
    """
    conversation_id = str(uuid.uuid4())
    
    tool_func = ALL_TOOL_FUNCTIONS.get(request.tool_name)
    if not tool_func:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tool '{request.tool_name}' not found.")

    # Prepare arguments for the tool function
    tool_args = {
        **request.parameters,
        "db_session": db_session,
        "chroma_collection": chroma_collection,
    }

    # Inject conversation_id for tools that require it
    # This logic remains flexible for tools that might not need the full context.
    if request.tool_name != "search_internal_knowledge_base":
        tool_args["conversation_id"] = conversation_id
    else: 
        del tool_args["db_session"]

    try:
        result = await tool_func(**tool_args)
        return models.ToolExecutionResponse(
            conversation_id=conversation_id,
            tool_name=request.tool_name,
            result=str(result) # Ensure result is always a string for the API contract
        )
    except exceptions.ToolExecutionError as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")