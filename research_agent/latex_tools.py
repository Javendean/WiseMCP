import asyncio
import base64
import io
import json
from typing import Dict, Coroutine

import matplotlib.pyplot as plt
import sympy
from chromadb import Collection
from sqlmodel.ext.asyncio.session import AsyncSession

from .exceptions import ToolExecutionError
from .models import ToolCallHistory
from .tools import add_to_knowledge_base # Re-use the helper

async def process_latex_string(
    conversation_id: str,
    latex_string: str,
    db_session: AsyncSession,
    chroma_collection: Collection,
) -> str:
    """
    Parses a LaTeX string into a SymPy expression, extracts its components,
    and renders it as a base64 PNG image.
    """
    try:
        # 1. Parse the LaTeX string
        parsed_expr = await asyncio.to_thread(sympy.parsing.latex.parse_latex, latex_string)
        
        # 2. Extract components
        components = set()
        for arg in sympy.preorder_traversal(parsed_expr):
            components.add(arg.__class__.__name__)
        parsed_components = sorted(list(components))

        # 3. Render the LaTeX string to a PNG image in memory
        fig, ax = plt.subplots()
        ax.text(0.5, 0.5, f"${latex_string}$", size=20, ha='center', va='center')
        ax.axis('off')
        
        buf = io.BytesIO()
        await asyncio.to_thread(fig.savefig, buf, format='png', bbox_inches='tight', pad_inches=0.1)
        plt.close(fig)
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')

        # 4. Prepare the result
        result_dict = {
            "parsed_components": parsed_components,
            "rendered_image": img_base64,
        }
        result_str = json.dumps(result_dict, indent=2)

        # 5. Log to database
        history_entry = ToolCallHistory(
            conversation_id=conversation_id,
            tool_name="process_latex_string",
            parameters={"latex_string": latex_string},
            result=result_str,
        )
        db_session.add(history_entry)
        await db_session.commit()

        # 6. Add to knowledge base
        await add_to_knowledge_base(
            content=f"Parsed LaTeX components: {', '.join(parsed_components)}",
            metadata={
                "source": "latex_parser",
                "original_latex": latex_string
            },
            chroma_collection=chroma_collection,
        )

        return result_str

    except Exception as e:
        raise ToolExecutionError(f"Failed to process LaTeX string: {e}")

# --- Tool Registry for LaTeX Tools ---

LATEX_TOOLS_SCHEMA = [
    {
        "name": "process_latex_string",
        "description": "Parses and renders a mathematical LaTeX string. Use this to understand, validate, and visualize mathematical equations.",
        "parameters": {
            "type": "object",
            "properties": {
                "latex_string": {"type": "string", "description": "The LaTeX string representing the equation (e.g., '\frac{d}{dx} e^x')."},
            },
            "required": ["latex_string"],
        },
    },
]

LATEX_TOOL_FUNCTIONS: Dict[str, Coroutine] = {
    "process_latex_string": process_latex_string,
}
