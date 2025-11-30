"""
Resumable Workflows - resumable workflows

Based on Day 2b: Tools Best Practices
Implements resumable workflows pattern for long-running operations.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from enum import Enum
from datetime import datetime
from pathlib import Path

try:
    from google.adk.apps.app import App, ResumabilityConfig
    HAS_ADK_APPS = True
except ImportError:
    HAS_ADK_APPS = False
    App = object
    ResumabilityConfig = object

from observability.logging import get_logger
from memory.shared_memory import get_shared_memory

logger = get_logger(__name__)


class WorkflowStatus(Enum):
    """Workflow status."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ResumableWorkflow:
    """
    Resumable workflow for long-running operations.
    
    Saves state and allows resuming execution after pause.
    """
    
    def __init__(
        self,
        workflow_id: str,
        state_file: Optional[str] = None
    ):
        """Initialize workflow.
        
        Args:
            workflow_id: Unique workflow ID
            state_file: Path to file for saving state (optional)
        """
        self.workflow_id = workflow_id
        self.state_file = state_file or f"workflow_{workflow_id}.json"
        self.status = WorkflowStatus.PENDING
        self.current_step = 0
        self.steps: List[Dict[str, Any]] = []
        self.state: Dict[str, Any] = {}
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        self._load_state()
    
    def add_step(
        self,
        step_name: str,
        step_func: callable,
        depends_on: Optional[List[int]] = None
    ) -> None:
        """Adds step to workflow.
        
        Args:
            step_name: Step name
            step_func: Function to execute step
            depends_on: List of step indices this step depends on
        """
        self.steps.append({
            "name": step_name,
            "func": step_func,
            "depends_on": depends_on or [],
            "status": "pending",
            "result": None
        })
    
    async def execute(self) -> Dict[str, Any]:
        """Executes workflow.
        
        Returns:
            Dictionary with execution result
        """
        self.status = WorkflowStatus.RUNNING
        self._save_state()
        
        try:
            for i, step in enumerate(self.steps):
                if i < self.current_step:
                    continue
                
                if step["depends_on"]:
                    for dep_idx in step["depends_on"]:
                        if self.steps[dep_idx]["status"] != "completed":
                            logger.warning(f"Step {i} depends on {dep_idx} which is not completed")
                            self.status = WorkflowStatus.PAUSED
                            self._save_state()
                            return {
                                "status": "paused",
                                "message": f"Step {i} waiting for dependencies"
                            }
                
                logger.info(f"Executing step {i}: {step['name']}", extra={
                    "event_type": "workflow_step_start",
                    "workflow_id": self.workflow_id,
                    "step_index": i,
                    "step_name": step["name"]
                })
                
                try:
                    if callable(step["func"]):
                        result = await step["func"](self.state)
                    else:
                        result = step["func"]
                    
                    step["status"] = "completed"
                    step["result"] = result
                    self.state[f"step_{i}_result"] = result
                    self.current_step = i + 1
                    self.updated_at = datetime.utcnow()
                    self._save_state()
                    
                    logger.info(f"Step {i} completed: {step['name']}", extra={
                        "event_type": "workflow_step_complete",
                        "workflow_id": self.workflow_id,
                        "step_index": i
                    })
                except Exception as e:
                    step["status"] = "failed"
                    step["error"] = str(e)
                    self.status = WorkflowStatus.FAILED
                    self._save_state()
                    
                    logger.error(f"Step {i} failed: {e}", extra={
                        "event_type": "workflow_step_failed",
                        "workflow_id": self.workflow_id,
                        "step_index": i,
                        "error": str(e)
                    }, exc_info=True)
                    
                    return {
                        "status": "failed",
                        "step": i,
                        "error": str(e)
                    }
            
            # All steps completed
            self.status = WorkflowStatus.COMPLETED
            self._save_state()
            
            return {
                "status": "completed",
                "workflow_id": self.workflow_id,
                "results": self.state
            }
        
        except Exception as e:
            self.status = WorkflowStatus.FAILED
            self._save_state()
            
            logger.error(f"Workflow failed: {e}", extra={
                "event_type": "workflow_failed",
                "workflow_id": self.workflow_id,
                "error": str(e)
            }, exc_info=True)
            
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def pause(self) -> None:
        """Pauses workflow."""
        self.status = WorkflowStatus.PAUSED
        self._save_state()
        logger.info(f"Workflow paused: {self.workflow_id}")
    
    def resume(self) -> Dict[str, Any]:
        """Resumes workflow execution.
        
        Returns:
            Dictionary with execution result
        """
        if self.status != WorkflowStatus.PAUSED:
            return {
                "status": "error",
                "message": f"Workflow is not paused (current status: {self.status})"
            }
        
        return self.execute()
    
    def _save_state(self) -> None:
        """Saves workflow state to file."""
        try:
            state_data = {
                "workflow_id": self.workflow_id,
                "status": self.status.value,
                "current_step": self.current_step,
                "steps": [
                    {
                        "name": s["name"],
                        "status": s["status"],
                        "result": s.get("result")
                    }
                    for s in self.steps
                ],
                "state": self.state,
                "created_at": self.created_at.isoformat(),
                "updated_at": self.updated_at.isoformat()
            }
            
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save workflow state: {e}")
    
    def _load_state(self) -> None:
        """Loads workflow state from file."""
        try:
            if Path(self.state_file).exists():
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state_data = json.load(f)
                
                self.status = WorkflowStatus(state_data.get("status", "pending"))
                self.current_step = state_data.get("current_step", 0)
                self.state = state_data.get("state", {})
                
                logger.info(f"Workflow state loaded: {self.workflow_id}", extra={
                    "event_type": "workflow_state_loaded",
                    "workflow_id": self.workflow_id,
                    "status": self.status.value,
                    "current_step": self.current_step
                })
        except Exception as e:
            logger.warning(f"Failed to load workflow state: {e}")


# Example usage for article processing
async def create_article_processing_workflow(urls: List[str], chat_id: Optional[int] = None) -> ResumableWorkflow:
    """Creates workflow for article processing using Shared Memory.
    
    Args:
        urls: List of article URLs
        chat_id: Telegram chat ID (optional, for notifications)
        
    Returns:
        ResumableWorkflow instance
    """
    workflow = ResumableWorkflow(workflow_id=f"process_{len(urls)}_articles")
    shared_mem = get_shared_memory()
    
    async def download_step(state: Dict[str, Any]) -> Dict[str, Any]:
        from tools.web_scraper import scrape_url
        
        downloaded = []
        for url in urls:
            result = scrape_url(url)
            downloaded.append(result)
        
        state["downloaded_articles"] = downloaded
        return {"downloaded_count": len(downloaded)}
    
    async def ingest_step(state: Dict[str, Any]) -> Dict[str, Any]:
        from agents.ingest_agent import run_once
        
        ingested = []
        namespace = f"workflow_{workflow.workflow_id}"
        
        for article in state.get("downloaded_articles", []):
            article_url = article.get("url", "")
            session_id = f"{workflow.workflow_id}_{hash(article_url)}"
            
            result = await run_once({
                "raw_text": article.get("text", ""),
                "metadata": {"url": article_url},
                "session_id": session_id,
                "episode_id": article_url
            })
            ingested.append(result)
            
            shared_mem.set("ingest_result", result, namespace=f"session_{session_id}", ttl_seconds=7200)
        
        state["ingested_articles"] = ingested
        return {"ingested_count": len(ingested)}
    
    async def kg_step(state: Dict[str, Any]) -> Dict[str, Any]:
        from agents.kg_builder_agent import run_once
        
        kg_results = []
        for ingested in state.get("ingested_articles", []):
            result = await run_once({
                "chunks": ingested.get("chunks", []),
                "title": ingested.get("title", ""),
                "language": ingested.get("language", "ru"),
                "session_id": workflow.workflow_id,
                "episode_id": ingested.get("url", "")
            })
            kg_results.append(result)
        
        state["kg_results"] = kg_results
        return {"kg_results_count": len(kg_results)}
    
    workflow.add_step("download", download_step)
    workflow.add_step("ingest", ingest_step, depends_on=[0])
    workflow.add_step("kg_build", kg_step, depends_on=[1])
    
    return workflow

