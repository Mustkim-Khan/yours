"""
Realtime Voice Tracing
======================
LangSmith integration for real-time voice sessions.
Creates manual spans for WebSocket sessions since they're not natively traced.
"""

import os
import time
from typing import Dict, List, Any, Optional
from datetime import datetime
from contextlib import contextmanager
from functools import wraps
from dotenv import load_dotenv

load_dotenv()

# LangSmith client
try:
    from langsmith import Client
    from langsmith.run_trees import RunTree
    langsmith_available = True
except ImportError:
    langsmith_available = False
    print("⚠️ LangSmith not available - tracing disabled")


# ============ Configuration ============

LANGCHAIN_API_KEY = os.getenv("LANGCHAIN_API_KEY")
LANGCHAIN_PROJECT = os.getenv("LANGCHAIN_PROJECT", "agentic-pharmacy")


class RealtimeTraceManager:
    """
    Manages LangSmith traces for realtime voice sessions.
    
    Since WebSocket sessions aren't automatically traced by LangChain,
    we create manual spans to track:
    - Session lifecycle (start → end)
    - Tool invocations within the session
    - Audio input/output events
    - UI action triggers
    """
    
    def __init__(self):
        self.client = None
        self.active_traces: Dict[str, RunTree] = {}
        
        if langsmith_available and LANGCHAIN_API_KEY:
            try:
                self.client = Client(api_key=LANGCHAIN_API_KEY)
                print("✅ RealtimeTraceManager connected to LangSmith")
            except Exception as e:
                print(f"⚠️ Failed to initialize LangSmith client: {e}")
    
    def start_session_trace(
        self,
        session_id: str,
        user_id: str,
        conversation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Start a new trace for a realtime voice session.
        Returns the trace ID.
        """
        if not self.client:
            return None
        
        try:
            # Create root run tree
            run_tree = RunTree(
                name="RealtimeVoiceSession",
                run_type="chain",
                inputs={
                    "session_id": session_id,
                    "user_id": user_id,
                    "conversation_id": conversation_id,
                    "started_at": datetime.now().isoformat()
                },
                extra={
                    "metadata": {
                        "session_id": session_id,
                        "user_id": user_id,
                        "model": "gpt-4o-realtime-preview",
                        "type": "realtime_voice",
                        **(metadata or {})
                    }
                },
                project_name=LANGCHAIN_PROJECT
            )
            
            # Post to LangSmith
            run_tree.post()
            
            self.active_traces[session_id] = run_tree
            print(f"✅ Started trace for session {session_id}: {run_tree.id}")
            
            return str(run_tree.id)
            
        except Exception as e:
            print(f"❌ Failed to start session trace: {e}")
            return None
    
    def log_audio_input(
        self,
        session_id: str,
        duration_ms: int,
        transcript: Optional[str] = None
    ):
        """Log an audio input event"""
        run_tree = self.active_traces.get(session_id)
        if not run_tree:
            return
        
        try:
            child = run_tree.create_child(
                name="AudioInput",
                run_type="tool",
                inputs={
                    "duration_ms": duration_ms,
                    "transcript": transcript
                }
            )
            child.end(outputs={"processed": True})
            child.post()
            
        except Exception as e:
            print(f"⚠️ Failed to log audio input: {e}")
    
    def log_audio_output(
        self,
        session_id: str,
        text: str,
        duration_ms: Optional[int] = None
    ):
        """Log an audio output event"""
        run_tree = self.active_traces.get(session_id)
        if not run_tree:
            return
        
        try:
            child = run_tree.create_child(
                name="AudioOutput",
                run_type="tool",
                inputs={"text": text}
            )
            child.end(outputs={
                "duration_ms": duration_ms,
                "character_count": len(text)
            })
            child.post()
            
        except Exception as e:
            print(f"⚠️ Failed to log audio output: {e}")
    
    def log_tool_call(
        self,
        session_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Dict[str, Any],
        duration_ms: Optional[int] = None
    ):
        """Log a tool/function call"""
        run_tree = self.active_traces.get(session_id)
        if not run_tree:
            return
        
        try:
            child = run_tree.create_child(
                name=f"Tool:{tool_name}",
                run_type="tool",
                inputs=arguments,
                extra={
                    "metadata": {
                        "tool_name": tool_name,
                        "triggered_ui_action": "ui_action" in result
                    }
                }
            )
            
            # Remove large data from result for logging
            logged_result = {k: v for k, v in result.items() if k != "ui_action"}
            
            child.end(outputs=logged_result)
            child.post()
            
            print(f"📊 Logged tool call: {tool_name}")
            
        except Exception as e:
            print(f"⚠️ Failed to log tool call: {e}")
    
    def log_ui_action(
        self,
        session_id: str,
        action_type: str,
        action_data: Dict[str, Any]
    ):
        """Log a UI action triggered by the voice session"""
        run_tree = self.active_traces.get(session_id)
        if not run_tree:
            return
        
        try:
            child = run_tree.create_child(
                name=f"UIAction:{action_type}",
                run_type="chain",
                inputs={"action_type": action_type}
            )
            child.end(outputs={"data_keys": list(action_data.keys())})
            child.post()
            
        except Exception as e:
            print(f"⚠️ Failed to log UI action: {e}")
    
    def end_session_trace(
        self,
        session_id: str,
        status: str = "success",
        tools_invoked: Optional[List[str]] = None,
        error: Optional[str] = None
    ):
        """End and finalize a session trace"""
        run_tree = self.active_traces.get(session_id)
        if not run_tree:
            return
        
        try:
            outputs = {
                "status": status,
                "ended_at": datetime.now().isoformat(),
                "tools_invoked": tools_invoked or [],
                "tool_count": len(tools_invoked or [])
            }
            
            if error:
                outputs["error"] = error
                run_tree.end(error=error, outputs=outputs)
            else:
                run_tree.end(outputs=outputs)
            
            run_tree.patch()
            
            del self.active_traces[session_id]
            print(f"✅ Ended trace for session {session_id}")
            
        except Exception as e:
            print(f"❌ Failed to end session trace: {e}")
    
    def get_trace_url(self, session_id: str) -> Optional[str]:
        """Get the LangSmith URL for a trace"""
        run_tree = self.active_traces.get(session_id)
        if not run_tree:
            return None
        
        return f"https://smith.langchain.com/o/default/projects/p/{LANGCHAIN_PROJECT}/r/{run_tree.id}"


# Global instance
realtime_trace_manager = RealtimeTraceManager()


# ============ Decorator for traced tool execution ============

def trace_tool_call(tool_name: str):
    """
    Decorator to automatically trace tool calls.
    Use on tool handler functions.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(session, *args, **kwargs):
            start_time = time.time()
            
            try:
                result = await func(session, *args, **kwargs)
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Log to LangSmith
                realtime_trace_manager.log_tool_call(
                    session_id=session.session_id,
                    tool_name=tool_name,
                    arguments=kwargs,
                    result=result,
                    duration_ms=duration_ms
                )
                
                # Log UI action if present
                if "ui_action" in result:
                    ui_action = result["ui_action"]
                    realtime_trace_manager.log_ui_action(
                        session_id=session.session_id,
                        action_type=ui_action.get("action", "unknown"),
                        action_data=ui_action.get("data", {})
                    )
                
                return result
                
            except Exception as e:
                duration_ms = int((time.time() - start_time) * 1000)
                realtime_trace_manager.log_tool_call(
                    session_id=session.session_id,
                    tool_name=tool_name,
                    arguments=kwargs,
                    result={"error": str(e)},
                    duration_ms=duration_ms
                )
                raise
        
        return wrapper
    return decorator


# ============ Convenience Functions ============

def start_voice_trace(
    session_id: str,
    user_id: str,
    conversation_id: Optional[str] = None
) -> Optional[str]:
    """Start tracing a voice session"""
    return realtime_trace_manager.start_session_trace(
        session_id, user_id, conversation_id
    )


def end_voice_trace(
    session_id: str,
    status: str = "success",
    tools_invoked: Optional[List[str]] = None,
    error: Optional[str] = None
):
    """End tracing a voice session"""
    realtime_trace_manager.end_session_trace(
        session_id, status, tools_invoked, error
    )


def log_voice_tool(
    session_id: str,
    tool_name: str,
    arguments: Dict[str, Any],
    result: Dict[str, Any]
):
    """Log a tool call in a voice session"""
    realtime_trace_manager.log_tool_call(
        session_id, tool_name, arguments, result
    )
