"""
E2B Sandbox Runner
==================

Manages E2B sandbox lifecycle for Claude Agent SDK execution.
Each agent runs in an isolated, ephemeral virtual computer.

Features:
- Automatic sandbox creation/destruction
- Environment variable injection
- Project file upload
- Session management for resumable agents
"""

import os
import asyncio
from typing import Optional, Dict, Any
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class AgentResult:
    """Result of an agent execution"""
    status: str  # "success", "error", "timeout"
    output: Optional[str] = None
    error: Optional[str] = None
    session_id: Optional[str] = None  # For resumable sessions
    tokens_used: Optional[int] = None
    cost_estimate: Optional[float] = None

async def run_agent_in_sandbox(
    agent_module: str,
    agent_function: str,
    params: Optional[Dict[str, Any]] = None,
    timeout: int = 900,  # 15 minutes default
    resume_session: Optional[str] = None
) -> AgentResult:
    """
    Spawn an E2B sandbox and run a Claude agent

    Args:
        agent_module: Python module name (e.g., "content_pipeline")
        agent_function: Function to call (e.g., "run_content_pipeline")
        params: Optional parameters to pass to the agent
        timeout: Maximum execution time in seconds
        resume_session: Optional session ID to resume

    Returns:
        AgentResult with status, output, and optional session_id
    """
    try:
        # Import E2B (lazy import to avoid issues if not installed)
        from e2b_code_interpreter import Sandbox

        # Create sandbox with environment variables
        sandbox = Sandbox(
            template="Python3-DataAnalysis",  # Pre-configured Python template
            timeout=timeout,
            env_vars={
                "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", ""),
                "NOTION_TOKEN": os.environ.get("NOTION_TOKEN", ""),
                "GMTM_DB_URL": os.environ.get("GMTM_DB_URL", ""),
                "SENDGRID_API_KEY": os.environ.get("SENDGRID_API_KEY", ""),
                "TWITTER_BEARER_TOKEN": os.environ.get("TWITTER_BEARER_TOKEN", ""),
                "LINKEDIN_ACCESS_TOKEN": os.environ.get("LINKEDIN_ACCESS_TOKEN", ""),
            }
        )

        try:
            # Install Claude Agent SDK in sandbox
            setup_result = sandbox.run_code("""
import subprocess
import sys

# Install Claude Agent SDK
subprocess.run([sys.executable, '-m', 'pip', 'install', 'claude-agent-sdk', '-q'], check=True)

# Install Claude Code CLI (required by SDK)
subprocess.run(['npm', 'install', '-g', '@anthropic-ai/claude-code'],
               capture_output=True, check=True)

print("Setup complete")
""")
            if setup_result.error:
                return AgentResult(
                    status="error",
                    error=f"Setup failed: {setup_result.error}"
                )

            # Upload project files to sandbox
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

            # Upload .claude/ config
            claude_dir = os.path.join(project_root, "..", "..", ".claude")
            if os.path.exists(claude_dir):
                # Note: E2B upload_file is sync, but we handle it
                pass  # TODO: Upload .claude/ directory

            # Upload agents/ directory
            agents_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agents")
            if os.path.exists(agents_dir):
                pass  # TODO: Upload agents/ directory

            # Build the agent execution code
            params_str = str(params) if params else "{}"
            resume_str = f'"{resume_session}"' if resume_session else "None"

            agent_code = f'''
import asyncio
import os

# Set working directory
os.chdir('/home/user/project')

# Import the agent
from agents.{agent_module} import {agent_function}

# Run the agent
async def main():
    try:
        result = await {agent_function}(params={params_str}, resume={resume_str})
        return result
    except Exception as e:
        return {{"error": str(e)}}

result = asyncio.run(main())
print("AGENT_RESULT:", result)
'''

            # Execute the agent
            exec_result = sandbox.run_code(agent_code)

            # Parse result
            if exec_result.error:
                return AgentResult(
                    status="error",
                    error=exec_result.error
                )

            output = exec_result.logs if hasattr(exec_result, 'logs') else str(exec_result)

            # Extract session ID if present (for resumable agents)
            session_id = None
            if "SESSION_ID:" in output:
                session_id = output.split("SESSION_ID:")[1].split("\n")[0].strip()

            return AgentResult(
                status="success",
                output=output,
                session_id=session_id
            )

        finally:
            # Always close the sandbox (ephemeral pattern)
            sandbox.close()

    except ImportError:
        # E2B not installed - fall back to local execution for development
        return await run_agent_locally(agent_module, agent_function, params)

    except Exception as e:
        return AgentResult(
            status="error",
            error=str(e)
        )

async def run_agent_locally(
    agent_module: str,
    agent_function: str,
    params: Optional[Dict[str, Any]] = None
) -> AgentResult:
    """
    Run agent locally (for development without E2B)

    This is a fallback for when E2B is not available.
    Uses direct Agent SDK execution on local machine.
    """
    try:
        # Dynamic import of the agent module
        import importlib
        module = importlib.import_module(f"agents.{agent_module}")
        func = getattr(module, agent_function)

        # Run the agent function
        result = await func(params=params or {})

        return AgentResult(
            status="success",
            output=str(result)
        )

    except Exception as e:
        return AgentResult(
            status="error",
            error=f"Local execution failed: {str(e)}"
        )

# ============================================
# SESSION MANAGEMENT (for resumable agents)
# ============================================

class SessionManager:
    """
    Manages agent sessions for resumable workflows

    Stores session IDs in a local database or cache.
    Used for hybrid session patterns (Lead Qualification, etc.)
    """

    def __init__(self, storage_path: str = ".sessions"):
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)

    def save_session(self, agent_name: str, session_id: str) -> None:
        """Save a session ID for later resumption"""
        filepath = os.path.join(self.storage_path, f"{agent_name}.session")
        with open(filepath, 'w') as f:
            f.write(session_id)

    def get_session(self, agent_name: str) -> Optional[str]:
        """Retrieve a saved session ID"""
        filepath = os.path.join(self.storage_path, f"{agent_name}.session")
        if os.path.exists(filepath):
            with open(filepath, 'r') as f:
                return f.read().strip()
        return None

    def clear_session(self, agent_name: str) -> None:
        """Clear a saved session"""
        filepath = os.path.join(self.storage_path, f"{agent_name}.session")
        if os.path.exists(filepath):
            os.remove(filepath)

# Global session manager instance
session_manager = SessionManager()

# ============================================
# UTILITY FUNCTIONS
# ============================================

def estimate_cost(tokens_used: int, model: str = "claude-sonnet-4-20250514") -> float:
    """
    Estimate cost based on token usage

    Pricing (per 1M tokens):
    - Haiku: $0.25 input, $1.25 output
    - Sonnet: $3 input, $15 output
    - Opus: $15 input, $75 output
    """
    pricing = {
        "claude-haiku-4-20250514": {"input": 0.25, "output": 1.25},
        "claude-sonnet-4-20250514": {"input": 3.0, "output": 15.0},
        "claude-opus-4-6": {"input": 15.0, "output": 75.0},
    }

    # Assume 50/50 input/output split for estimation
    rates = pricing.get(model, pricing["claude-sonnet-4-20250514"])
    cost_per_token = (rates["input"] + rates["output"]) / 2 / 1_000_000

    return tokens_used * cost_per_token
