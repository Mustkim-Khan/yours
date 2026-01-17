"""
LangSmith Tracing Utilities - Agent Waterfall Edition
Creates clean hierarchical agent traces without low-level tool noise.

Each agent appears as a single span with:
- model_used
- decision
- reason  
- evidence
- duration
"""

import os
import time
from functools import wraps
from typing import Optional, Callable, Any, Dict, List

from langsmith import Client, traceable
from langsmith.run_helpers import get_current_run_tree

# Initialize LangSmith client
langsmith_client = None


def init_langsmith():
    """Initialize LangSmith client with API key"""
    global langsmith_client
    api_key = os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY")
    if api_key:
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


def format_decision_output(agent_output) -> Dict[str, Any]:
    """Format AgentOutput into clean decision summary for trace metadata"""
    if not agent_output:
        return {}
    
    return {
        "decision": getattr(agent_output, 'decision', 'UNKNOWN').value if hasattr(getattr(agent_output, 'decision', None), 'value') else str(getattr(agent_output, 'decision', 'UNKNOWN')),
        "reason": getattr(agent_output, 'reason', ''),
        "evidence": getattr(agent_output, 'evidence', []),
        "next_agent": getattr(agent_output, 'next_agent', None),
        "message": getattr(agent_output, 'message', None)
    }


def agent_waterfall_span(agent_name: str, model_name: str):
    """
    Decorator for creating clean agent spans in the waterfall trace.
    
    Each agent appears as a single node showing:
    - Agent name
    - Model used
    - Decision summary
    
    Usage:
        @agent_waterfall_span("PharmacistAgent", "gpt-5.2")
        async def process_message(self, message: str):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Create the traceable wrapper inline with metadata
            @traceable(
                name=f"{agent_name} ({model_name})",
                run_type="chain",
                metadata={
                    "agent_name": agent_name,
                    "model_used": model_name
                },
                tags=[agent_name, model_name, "agent"]
            )
            async def traced_func(*a, **kw):
                return await func(*a, **kw)
            
            result = await traced_func(*args, **kwargs)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Add decision metadata to current run if available
            try:
                run_tree = get_current_run_tree()
                if run_tree and result:
                    decision_data = format_decision_output(result)
                    decision_data["duration_ms"] = duration_ms
                    decision_data["model_used"] = model_name
                    
                    # Update run metadata
                    if hasattr(run_tree, 'metadata'):
                        run_tree.metadata = {**run_tree.metadata, **decision_data}
            except:
                pass
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            
            @traceable(
                name=f"{agent_name} ({model_name})",
                run_type="chain",
                metadata={
                    "agent_name": agent_name,
                    "model_used": model_name
                },
                tags=[agent_name, model_name, "agent"]
            )
            def traced_func(*a, **kw):
                return func(*a, **kw)
            
            result = traced_func(*args, **kwargs)
            return result
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


def orchestrator_span(func: Callable) -> Callable:
    """
    Special decorator for OrchestratorAgent - appears as ROOT span.
    Shows routing decisions only.
    """
    @wraps(func)
    @traceable(
        name="OrchestratorAgent",
        run_type="chain",
        metadata={"role": "router", "agent_name": "OrchestratorAgent"},
        tags=["orchestrator", "root", "agent"]
    )
    async def async_wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        
        # Add routing info to trace
        try:
            run_tree = get_current_run_tree()
            if run_tree and result:
                run_tree.metadata = {
                    **run_tree.metadata,
                    "decision": "ROUTED",
                    "agent_chain": getattr(result, 'agent_chain', []),
                    "final_action": str(getattr(result, 'final_action', 'UNKNOWN'))
                }
        except:
            pass
        
        return result
    
    return async_wrapper


def child_agent_span(agent_name: str, model_name: str):
    """
    Decorator for child agents (Inventory, Policy, Fulfillment).
    Creates a clean span under the parent agent.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        @traceable(
            name=f"{agent_name} ({model_name})",
            run_type="chain",
            metadata={
                "agent_name": agent_name,
                "model_used": model_name
            },
            tags=[agent_name, model_name, "child-agent"]
        )
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Add decision to metadata
            try:
                run_tree = get_current_run_tree()
                if run_tree and result:
                    decision_data = format_decision_output(result)
                    decision_data["duration_ms"] = duration_ms
                    run_tree.metadata = {**run_tree.metadata, **decision_data}
            except:
                pass
            
            return result
        
        @wraps(func)
        @traceable(
            name=f"{agent_name} ({model_name})",
            run_type="chain",
            metadata={
                "agent_name": agent_name,
                "model_used": model_name
            },
            tags=[agent_name, model_name, "child-agent"]
        )
        def sync_wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator


# Legacy decorators for backward compatibility (do nothing visible)
def agent_span(agent_name: str, action: str, run_type: str = "chain"):
    """Legacy - use agent_waterfall_span instead"""
    return agent_waterfall_span(agent_name, "gpt-5.2")


def tool_span(tool_name: str):
    """Legacy - tools are now metadata, not spans"""
    def decorator(func: Callable) -> Callable:
        return func  # No-op, tools shouldn't create visible spans
    return decorator


def delegation_span(from_agent: str, to_agent: str):
    """Legacy - delegations are implicit in hierarchy, not separate spans"""
    def decorator(func: Callable) -> Callable:
        return func  # No-op, removes extra CoT nodes
    return decorator


def decision_span(agent_name: str, decision_type: str):
    """Legacy - decisions are metadata, not spans"""
    def decorator(func: Callable) -> Callable:
        return func  # No-op
    return decorator


# Initialize on module load
init_langsmith()
