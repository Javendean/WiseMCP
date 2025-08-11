from typing import Optional

class ToolExecutionError(Exception):
    """Base class for exceptions in this module."""
    def __init__(self, message: str, tool_name: Optional[str] = None):
        self.message = message
        self.tool_name = tool_name
        super().__init__(self.message)

    def to_json(self):
        return {
            "error_code": self.__class__.__name__,
            "message": self.message,
            "tool_name": self.tool_name,
        }

class RateLimitError(ToolExecutionError):
    """Raised when an API rate limit is exceeded."""
    pass

class NoResultsFoundError(ToolExecutionError):
    """Raised when a tool finds no results for a given query."""
    pass

class InvalidToolParameterError(ToolExecutionError):
    """Raised when a tool receives invalid parameters."""
    pass

class APICallError(ToolExecutionError):
    """Raised for general API call failures."""
    pass

class FileOperationError(ToolExecutionError):
    """Raised for errors during file operations."""
    pass

class ContentExtractionError(ToolExecutionError):
    """Raised when content extraction from a webpage fails."""
    pass
