"""
LangSmith Tracing Utilities - STRICT AGENT WATERFALL Edition
====================================================================
Only agent-to-agent spans are visible in the trace.
NO ChatOpenAI, tool, or internal function calls appear.

Each agent = ONE parent span with metadata containing:
- model_used
- decision
- reason
- evidence
"""

import os
import time
from functools import wraps
from typing import Optional, Callable, Any, Dict, List
from contextlib import contextmanager

from langsmith import Client
from langsmith.run_helpers import get_current_run_tree, traceable as ls_traceable

# Initialize LangSmith client
langsmith_client = None

# Flag to disable nested tracing inside agents
_tracing_disabled_context = False


def init_langsmith():
    """Initialize LangSmith client with API key"""
    global langsmith_client
    api_key = os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY")
    if api_key:
        # Enable tracing for explicit @ls_traceable decorators
        # LangChain auto-tracing is suppressed via:
        # 1. Removed AgentExecutor from PharmacistAgent
        # 2. Using callbacks=[] in create_non_traced_llm
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGCHAIN_PROJECT", "agentic-pharmacy")
        langsmith_client = Client(api_key=api_key)
        return True
    return False


def get_trace_id() -> Optional[str]:
    """Get the current LangSmith trace ID"""
    try:
        run_tree = get_current_run_tree()
        if run_tree:
            return str(run_tree.id)
    except:
        pass
    return None


@contextmanager
def disable_nested_tracing():
    """Context manager to disable nested tracing inside agents"""
    global _tracing_disabled_context
    old_value = _tracing_disabled_context
    _tracing_disabled_context = True
    try:
        yield
    finally:
        _tracing_disabled_context = old_value


def is_tracing_disabled() -> bool:
    """Check if nested tracing is currently disabled"""
    return _tracing_disabled_context


def agent_trace(agent_name: str, model_name: str):
    """
    STRICT agent tracing decorator - CHILD SPANS ONLY.
    Creates a child span under the current parent run tree.
    
    CRITICAL: This decorator only creates a span if called within
    an existing trace context (e.g., under OrchestratorAgent).
    If no parent exists, executes without tracing to avoid orphan roots.
    
    Usage:
        @agent_trace("PharmacistAgent", "gpt-5.2")
        async def process_message(self, message: str) -> AgentOutput:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Check if we're inside a parent trace context
            parent_run = get_current_run_tree()
            
            if parent_run is not None:
                # We have a parent - create a child span
                @ls_traceable(
                    name=f"{agent_name} ({model_name})",
                    run_type="chain",
                    metadata={
                        "agent_name": agent_name,
                        "model_used": model_name,
                        "type": "agent"
                    },
                    tags=[agent_name, model_name, "agent"]
                )
                async def traced_agent(*a, **kw):
                    # Disable nested tracing for LLM calls inside this agent
                    with disable_nested_tracing():
                        result = await func(*a, **kw)
                    return result
                
                result = await traced_agent(*args, **kwargs)
            else:
                # No parent trace - execute without creating orphan root
                with disable_nested_tracing():
                    result = await func(*args, **kwargs)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Add decision metadata to the span
            try:
                run_tree = get_current_run_tree()
                if run_tree and result:
                    metadata = {
                        "duration_ms": duration_ms,
                        "model_used": model_name,
                    }
                    
                    # Extract decision info from AgentOutput
                    if hasattr(result, 'decision'):
                        decision = result.decision
                        metadata["decision"] = decision.value if hasattr(decision, 'value') else str(decision)
                    if hasattr(result, 'reason'):
                        metadata["reason"] = result.reason
                    if hasattr(result, 'evidence'):
                        metadata["evidence"] = result.evidence
                    if hasattr(result, 'next_agent'):
                        metadata["next_agent"] = result.next_agent
                    
                    if hasattr(run_tree, 'metadata'):
                        run_tree.metadata = {**run_tree.metadata, **metadata}
            except:
                pass
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Check if we're inside a parent trace context
            parent_run = get_current_run_tree()
            
            if parent_run is not None:
                @ls_traceable(
                    name=f"{agent_name} ({model_name})",
                    run_type="chain",
                    metadata={
                        "agent_name": agent_name,
                        "model_used": model_name,
                        "type": "agent"
                    },
                    tags=[agent_name, model_name, "agent"]
                )
                def traced_agent(*a, **kw):
                    with disable_nested_tracing():
                        return func(*a, **kw)
                
                return traced_agent(*args, **kwargs)
            else:
                # No parent trace - execute without creating orphan root
                with disable_nested_tracing():
                    return func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator



def orchestrator_trace(func: Callable) -> Callable:
    """
    ROOT trace for OrchestratorAgent.
    This is the parent span that contains all agent chains.
    """
    @wraps(func)
    @ls_traceable(
        name="OrchestratorAgent",
        run_type="chain",
        metadata={
            "role": "orchestrator",
            "agent_name": "OrchestratorAgent",
            "type": "root"
        },
        tags=["orchestrator", "root"]
    )
    async def async_wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        
        # Add routing info to trace
        try:
            run_tree = get_current_run_tree()
            if run_tree and result:
                run_tree.metadata = {
                    **run_tree.metadata,
                    "agent_chain": getattr(result, 'agent_chain', []),
                    "final_action": str(getattr(result, 'final_action', 'UNKNOWN'))
                }
        except:
            pass
        
        return result
    
    return async_wrapper


def create_non_traced_llm(model_name: str, temperature: float = 0.1):
    """
    Create a ChatOpenAI instance that does NOT create trace spans.
    Use this inside agents to prevent LLM calls from appearing in traces.
    """
    from langchain_openai import ChatOpenAI
    
    # Create LLM with tracing callbacks disabled
    llm = ChatOpenAI(
        model=model_name,
        temperature=temperature,
        api_key=os.getenv("OPENAI_API_KEY"),
        # Disable LangSmith callbacks for this LLM
        callbacks=[]
    )
    
    return llm


# Legacy compatibility - these do nothing now
def agent_span(agent_name: str, action: str, run_type: str = "chain"):
    """Legacy - use agent_trace instead"""
    return agent_trace(agent_name, "gpt-5.2")


def tool_span(tool_name: str):
    """Legacy - tools don't create spans anymore"""
    def decorator(func: Callable) -> Callable:
        return func
    return decorator


def delegation_span(from_agent: str, to_agent: str):
    """Legacy - delegations are implicit in agent hierarchy"""
    def decorator(func: Callable) -> Callable:
        return func
    return decorator


def decision_span(agent_name: str, decision_type: str):
    """Legacy - decisions are metadata, not spans"""
    def decorator(func: Callable) -> Callable:
        return func
    return decorator


def child_agent_span(agent_name: str, model_name: str):
    """Alias for agent_trace for backward compatibility"""
    return agent_trace(agent_name, model_name)


def orchestrator_span(func: Callable) -> Callable:
    """Alias for orchestrator_trace for backward compatibility"""
    return orchestrator_trace(func)


def agent_waterfall_span(agent_name: str, model_name: str):
    """Alias for agent_trace for backward compatibility"""
    return agent_trace(agent_name, model_name)


# Initialize on module load
init_langsmith()
