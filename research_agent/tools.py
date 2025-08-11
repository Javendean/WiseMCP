import asyncio
import hashlib
import json
import shlex
from typing import List, Dict, Any, Coroutine

import arxiv
import httpx
from bs4 import BeautifulSoup
from chromadb import Collection
from github import Github, RateLimitExceededException as GithubRateLimitExceededException
from sqlmodel.ext.asyncio.session import AsyncSession

from .config import settings
from .exceptions import (
    ToolExecutionError,
    APICallError,
    NoResultsFoundError,
    RateLimitError,
    ContentExtractionError,
    FileOperationError,
)
from .models import ToolCallHistory

# --- Internal Helper Functions ---

async def add_to_knowledge_base(
    content: str,
    metadata: dict,
    chroma_collection: Collection
) -> None:
    """
    Adds content to the ChromaDB knowledge base after chunking.
    """
    chunks = content.split('\n\n')
    ids = [hashlib.sha256(chunk.encode()).hexdigest() for chunk in chunks]
    
    try:
        chroma_collection.upsert(
            ids=ids,
            documents=chunks,
            metadatas=[metadata] * len(chunks)
        )
    except Exception as e:
        raise ToolExecutionError(f"Failed to add to knowledge base: {e}")

# --- Research Tools ---

async def query_arxiv(
    conversation_id: str,
    query: str,
    max_results: int,
    db_session: AsyncSession,
    chroma_collection: Collection,
) -> str:
    """
    Queries the ArXiv API for scientific papers.
    """
    try:
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate
        )
        results = await asyncio.to_thread(lambda: list(search.results()))

        if not results:
            raise NoResultsFoundError("No papers found on ArXiv for the given query.")

        papers = [
            {
                "title": result.title,
                "authors": [author.name for author in result.authors],
                "summary": result.summary,
                "pdf_url": result.pdf_url,
                "published_date": result.published.isoformat(),
            }
            for result in results
        ]
        
        result_str = json.dumps(papers, indent=2)
        
        history_entry = ToolCallHistory(
            conversation_id=conversation_id,
            tool_name="query_arxiv",
            parameters=json.dumps({"query": query, "max_results": max_results}),
            result=result_str,
        )
        db_session.add(history_entry)
        await db_session.commit()

        for paper in papers:
            await add_to_knowledge_base(
                content=f"Title: {paper['title']}\nSummary: {paper['summary']}",
                metadata={"source": "arxiv", "query": query, "url": paper['pdf_url']},
                chroma_collection=chroma_collection,
            )

        return result_str
    except NoResultsFoundError:
        raise # Re-raise the specific error to be handled by the caller
    except Exception as e:
        raise APICallError(f"Failed to query ArXiv: {e}")


async def search_github_code(
    conversation_id: str,
    query: str,
    db_session: AsyncSession,
    chroma_collection: Collection,
) -> str:
    """
    Searches for code on GitHub.
    """
    try:
        g = Github(settings.GITHUB_TOKEN)
        
        rate_limit = g.get_rate_limit()
        if rate_limit.core.remaining < 10:
             raise RateLimitError("GitHub API rate limit is low. Please try again later.")

        results = await asyncio.to_thread(g.search_code, query)
        
        if results.totalCount == 0:
            raise NoResultsFoundError("No code found on GitHub for the given query.")

        code_files = [
            {
                "repository": item.repository.full_name,
                "file_path": item.path,
                "url": item.html_url,
                "score": item.score,
            }
            for item in results[:10]
        ]
        
        result_str = json.dumps(code_files, indent=2)

        history_entry = ToolCallHistory(
            conversation_id=conversation_id,
            tool_name="search_github_code",
            parameters=json.dumps({"query": query}),
            result=result_str,
        )
        db_session.add(history_entry)
        await db_session.commit()

        for item in code_files:
            await add_to_knowledge_base(
                content=f"Found relevant code in repository: {item['repository']}, file: {item['file_path']}",
                metadata={"source": "github", "query": query, "url": item['url']},
                chroma_collection=chroma_collection,
            )

        return result_str
    except GithubRateLimitExceededException:
        raise RateLimitError("GitHub API rate limit exceeded.")
    except Exception as e:
        raise APICallError(f"Failed to search GitHub: {e}")


async def extract_web_content(
    conversation_id: str,
    url: str,
    db_session: AsyncSession,
    chroma_collection: Collection,
) -> str:
    """
    Extracts the main textual content from a given URL.
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        
        content_tags = ["article", "main", "div.post-content", "div.content", "body"]
        text = ""
        for tag in content_tags:
            element = soup.select_one(tag)
            if element:
                text = element.get_text(separator="\n", strip=True)
                if len(text.split()) > 50:
                    break
        
        if not text:
            raise ContentExtractionError("Could not extract meaningful content from the URL.")

        result_str = json.dumps({"url": url, "content": text[:4000]}, indent=2)

        history_entry = ToolCallHistory(
            conversation_id=conversation_id,
            tool_name="extract_web_content",
            parameters=json.dumps({"url": url}),
            result=result_str,
        )
        db_session.add(history_entry)
        await db_session.commit()

        await add_to_knowledge_base(
            content=text,
            metadata={"source": "web", "url": url},
            chroma_collection=chroma_collection,
        )

        return json.dumps({"url": url, "content": text}, indent=2)
    except httpx.HTTPStatusError as e:
        raise APICallError(f"HTTP error fetching URL {url}: {e.response.status_code}")
    except Exception as e:
        raise ToolExecutionError(f"Failed to extract web content: {e}")


async def search_local_codebase(
    conversation_id: str,
    query: str,
    db_session: AsyncSession,
    chroma_collection: Collection,
) -> str:
    """
    Searches the local codebase using ripgrep for a given query.
    """
    base_path = settings.LOCAL_CODEBASE_PATH
    
    safe_query = shlex.quote(query)
    command = ['rg', '--json', '--case-sensitive', safe_query, '.']

    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=base_path
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0 and process.returncode != 1:
            raise FileOperationError(f"ripgrep failed: {stderr.decode()}")
        
        results = []
        if stdout:
            for line in stdout.decode().splitlines():
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        if not results and process.returncode == 1:
            raise NoResultsFoundError("No results found in the local codebase.")

        result_str = json.dumps(results, indent=2)

        history_entry = ToolCallHistory(
            conversation_id=conversation_id,
            tool_name="search_local_codebase",
            parameters=json.dumps({"query": query}),
            result=result_str,
        )
        db_session.add(history_entry)
        await db_session.commit()

        for res in results:
            if res.get('type') == 'match':
                file_path = res['data']['path']['text']
                line_number = res['data']['line_number']
                line_text = res['data']['lines']['text'].strip()
                await add_to_knowledge_base(
                    content=line_text,
                    metadata={"source": "local_codebase", "file_path": file_path, "line_number": line_number},
                    chroma_collection=chroma_collection,
                )

        return result_str
    except FileNotFoundError:
        raise ToolExecutionError("ripgrep (rg) is not installed or not in PATH.")
    except Exception as e:
        raise ToolExecutionError(f"Failed to search local codebase: {e}")


async def search_internal_knowledge_base(
    query_texts: List[str],
    n_results: int = 5,
    where_filter: Dict[str, Any] = None,
    chroma_collection: Collection = None,
    **kwargs
) -> str:
    """
    Searches the agent's internal vector knowledge base.
    """
    if not chroma_collection:
         raise ToolExecutionError("Chroma collection not available.")
    try:
        results = chroma_collection.query(
            query_texts=query_texts,
            n_results=n_results,
            where=where_filter
        )
        return json.dumps(results, indent=2)
    except Exception as e:
        raise ToolExecutionError(f"Failed to query knowledge base: {e}")


# --- Tool Registry ---

AVAILABLE_TOOLS_SCHEMA = [
    {
        "name": "query_arxiv",
        "description": "Search ArXiv for scientific papers. Use for finding cutting-edge research, algorithms, and theoretical foundations. Best for academic and scientific topics.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query (e.g., 'quantum computing', 'author:Yann LeCun')."},
                "max_results": {"type": "integer", "description": "Maximum number of papers to return.", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_github_code",
        "description": "Search GitHub for code. Essential for finding real-world implementations, libraries, and code examples. Use qualifiers like 'language:python' or 'repo:owner/repo' for targeted searches.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query. Can include GitHub search qualifiers."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "extract_web_content",
        "description": "Extract the main text from a URL. Ideal for reading documentation, articles, and blog posts to understand a topic or technology.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to scrape."},
            },
            "required": ["url"],
        },
    },
    {
        "name": "search_local_codebase",
        "description": "Search the contents of files in the current project directory using a regular expression via ripgrep (rg). Crucial for understanding the existing code before making changes.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "A ripgrep-compatible regex pattern to search for within the local project files."},
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_internal_knowledge_base",
        "description": "Search your own long-term memory for relevant information from past interactions and research. This should be your first step when starting a new task to see what you already know.",
        "parameters": {
            "type": "object",
            "properties": {
                "query_texts": {"type": "array", "items": {"type": "string"}, "description": "A list of questions or topics to search for in your memory."}, 
                "n_results": {"type": "integer", "description": "Number of results to return.", "default": 5},
                "where_filter": {"type": "object", "description": "Optional metadata filter (e.g., {'source': 'arxiv'})."},
            },
            "required": ["query_texts"],
        },
    },
]

TOOL_FUNCTIONS: Dict[str, Coroutine] = {
    "query_arxiv": query_arxiv,
    "search_github_code": search_github_code,
    "extract_web_content": extract_web_content,
    "search_local_codebase": search_local_codebase,
    "search_internal_knowledge_base": search_internal_knowledge_base,
}