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

# Session-based trace context storage
# Maps session_id -> root_trace_id for unified tracing across requests
_session_trace_context: Dict[str, str] = {}


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


def set_session_trace(session_id: str, trace_id: str) -> None:
    """Store the root trace ID for a session (for unified tracing)"""
    _session_trace_context[session_id] = trace_id


def get_session_trace(session_id: str) -> Optional[str]:
    """Get the root trace ID for a session"""
    return _session_trace_context.get(session_id)


def clear_session_trace(session_id: str) -> None:
    """Clear the trace context for a session (call when order completes)"""
    _session_trace_context.pop(session_id, None)


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
    
    For session-based unified tracing:
    - First request creates a root trace
    - Continuation requests (confirm) create child spans under the same session
    """
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        # Extract session_id from request argument
        session_id = None
        if args and len(args) > 1:
            request = args[1]  # args[0] is self, args[1] is request
            if hasattr(request, 'session_id'):
                session_id = request.session_id
        
        # Check if this is a continuation of an existing trace
        existing_trace = get_session_trace(session_id) if session_id else None
        
        if existing_trace:
            # This is a continuation - create a child span instead of new root
            @ls_traceable(
                name="OrchestratorAgent",
                run_type="chain",
                metadata={
                    "role": "orchestrator",
                    "agent_name": "OrchestratorAgent",
                    "type": "continuation",
                    "parent_trace": existing_trace
                },
                tags=["orchestrator", "continuation"]
            )
            async def traced_continuation(*a, **kw):
                return await func(*a, **kw)
            
            result = await traced_continuation(*args, **kwargs)
        else:
            # This is a new flow - create root trace
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
            async def traced_root(*a, **kw):
                return await func(*a, **kw)
            
            result = await traced_root(*args, **kwargs)
            
            # Store the trace ID for this session for future continuations
            if session_id:
                trace_id = get_trace_id()
                if trace_id:
                    set_session_trace(session_id, trace_id)
        
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
        
        # Clear trace context if order is complete
        if session_id and result:
            final_action = getattr(result, 'final_action', None)
            if final_action and str(final_action) == 'AgentAction.CREATE_ORDER':
                clear_session_trace(session_id)
        
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
