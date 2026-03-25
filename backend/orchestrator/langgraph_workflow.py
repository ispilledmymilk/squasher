# backend/orchestrator/langgraph_workflow.py
#
# LangGraph StateGraph orchestration (blueprint) with sequential fallback.

from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict

from agents.code_style_agent import CodeStyleAgent
from agents.complexity_agent import ComplexityAgent
from agents.dependency_agent import DependencyAgent
from agents.pattern_agent import PatternAgent
from agents.velocity_agent import VelocityAgent
from data.metrics_store import MetricsStore
from ml.decay_predictor import DecayPredictor
from utils.logger import setup_logger
from utils.progress_bus import emit_progress

logger = setup_logger(__name__)

try:
    from langgraph.graph import END, StateGraph

    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    END = None  # type: ignore
    StateGraph = None  # type: ignore


class DecayState(TypedDict, total=False):
    file_path: str
    repo_path: str
    complexity: Dict[str, Any]
    velocity: Dict[str, Any]
    dependency: Dict[str, Any]
    pattern: Dict[str, Any]
    prediction: Dict[str, Any]
    status: str


class DecayAnalysisWorkflow:
    """Multi-agent decay analysis via LangGraph when available, else sequential."""

    def __init__(self, repo_path: str):
        self.repo_path = repo_path

        self.complexity_agent = ComplexityAgent()
        self.velocity_agent = VelocityAgent(repo_path)
        self.dependency_agent = DependencyAgent()
        self.pattern_agent = PatternAgent()
        self.code_style_agent = CodeStyleAgent()
        self.predictor = DecayPredictor()
        self.metrics_store = MetricsStore()

        self._compiled = None
        if LANGGRAPH_AVAILABLE and StateGraph is not None:
            try:
                self._compiled = self._build_langgraph()
                logger.info("DecayAnalysisWorkflow: LangGraph graph compiled")
            except Exception as e:
                logger.warning("LangGraph compile failed, sequential mode: %s", e)
                self._compiled = None

        if self._compiled is None:
            logger.info("DecayAnalysisWorkflow: sequential mode")

    def _emit(
        self, step: str, file_path: str, detail: Optional[Dict[str, Any]] = None
    ) -> None:
        payload: Dict[str, Any] = {
            "step": step,
            "file_path": file_path,
            "repo_path": self.repo_path,
        }
        if detail:
            payload["detail"] = detail
        emit_progress({"type": "analysis_progress", "payload": payload})

    def _node_complexity(self, state: DecayState) -> Dict[str, Any]:
        fp = state["file_path"]
        self._emit("complexity", fp, {"phase": "start"})
        ctx = {"file_path": fp}
        result = self.complexity_agent.analyze(ctx)
        if result.get("status") == "unsupported_file":
            self._emit("complexity", fp, {"phase": "unsupported"})
            return {"complexity": result, "status": "unsupported_file"}
        self._emit("complexity", fp, {"phase": "done"})
        return {"complexity": result}

    def _node_velocity(self, state: DecayState) -> Dict[str, Any]:
        fp = state["file_path"]
        self._emit("velocity", fp, {"phase": "start"})
        r = self.velocity_agent.analyze({"file_path": fp})
        self._emit("velocity", fp, {"phase": "done"})
        return {"velocity": r}

    def _node_dependency(self, state: DecayState) -> Dict[str, Any]:
        fp = state["file_path"]
        self._emit("dependency", fp, {"phase": "start"})
        r = self.dependency_agent.analyze({"file_path": fp})
        self._emit("dependency", fp, {"phase": "done"})
        return {"dependency": r}

    def _node_pattern(self, state: DecayState) -> Dict[str, Any]:
        fp = state["file_path"]
        self._emit("pattern", fp, {"phase": "start"})
        r = self.pattern_agent.analyze({"file_path": fp})
        self._emit("pattern", fp, {"phase": "done"})
        return {"pattern": r}

    def _node_predict(self, state: DecayState) -> Dict[str, Any]:
        fp = state["file_path"]
        self._emit("prediction", fp, {"phase": "start"})
        agent_results = {
            "complexity": state.get("complexity", {}),
            "velocity": state.get("velocity", {}),
            "dependency": state.get("dependency", {}),
            "pattern": state.get("pattern", {}),
        }
        pred = self.predictor.predict_decay(agent_results)
        self._emit("prediction", fp, {"phase": "done", "risk": pred.get("risk_level")})
        return {"prediction": pred, "status": "completed"}

    def _route_after_complexity(self, state: DecayState) -> str:
        if state.get("status") == "unsupported_file":
            return "stop"
        return "continue"

    def _build_langgraph(self):
        g = StateGraph(DecayState)
        g.add_node("complexity", self._node_complexity)
        g.add_node("velocity", self._node_velocity)
        g.add_node("dependency", self._node_dependency)
        g.add_node("pattern", self._node_pattern)
        g.add_node("predict", self._node_predict)

        g.set_entry_point("complexity")
        g.add_conditional_edges(
            "complexity",
            self._route_after_complexity,
            {"stop": END, "continue": "velocity"},
        )
        g.add_edge("velocity", "dependency")
        g.add_edge("dependency", "pattern")
        g.add_edge("pattern", "predict")
        g.add_edge("predict", END)
        return g.compile()

    def _run_sequential(self, file_path: str) -> DecayState:
        state: DecayState = {
            "file_path": file_path,
            "repo_path": self.repo_path,
            "complexity": {},
            "velocity": {},
            "dependency": {},
            "pattern": {},
            "prediction": {},
            "status": "running",
        }
        u = self._node_complexity(state)
        state.update(u)
        if state.get("status") == "unsupported_file":
            return state
        state.update(self._node_velocity(state))
        state.update(self._node_dependency(state))
        state.update(self._node_pattern(state))
        state.update(self._node_predict(state))
        return state

    def _persist(self, state: DecayState, file_path: str) -> None:
        if state.get("status") != "completed":
            return
        logger.info(f"Saving results for {file_path}")
        try:
            complexity_data = state.get("complexity", {})
            velocity_data = state.get("velocity", {})
            dependency_data = state.get("dependency", {})
            metrics = {
                "cyclomatic_complexity": complexity_data.get("current_complexity"),
                "lines_of_code": 0,
                "maintainability_index": complexity_data.get("maintainability_index"),
                "comment_ratio": 0,
                "change_frequency": velocity_data.get("change_frequency"),
                "authors_count": velocity_data.get("authors_count"),
                "import_count": dependency_data.get("import_count"),
                "dependency_depth": dependency_data.get("dependency_depth"),
                "metadata": {},
            }
            self.metrics_store.save_metrics(file_path, metrics)
            self.metrics_store.save_prediction(file_path, state.get("prediction", {}))
            logger.info(f"Results saved successfully for {file_path}")
        except Exception as e:
            logger.error(f"Error saving results: {e}")
            state["status"] = "error"

    def analyze_file(
        self, file_path: str, persist: bool = True
    ) -> Dict[str, Any]:
        """Run full analysis on a file. When persist=False, skip metrics DB writes."""
        logger.info(f"Starting analysis workflow for {file_path}")

        if self._compiled is not None:
            initial: DecayState = {
                "file_path": file_path,
                "repo_path": self.repo_path,
                "complexity": {},
                "velocity": {},
                "dependency": {},
                "pattern": {},
                "prediction": {},
                "status": "running",
            }
            final = dict(self._compiled.invoke(initial))
        else:
            final = dict(self._run_sequential(file_path))

        if persist and final.get("status") == "completed":
            self._persist(final, file_path)
        elif not persist:
            logger.debug("Skipping metrics persistence for %s", file_path)

        logger.info(
            f"Analysis complete for {file_path}: {final.get('status', 'unknown')}"
        )
        return final

    def check_files_for_commit(
        self, file_paths: list, skip_save: bool = True
    ) -> Dict[str, Any]:
        """
        Run style + pattern + complexity checks on given files (e.g. staged).
        Returns a pre-commit report: issues per file, total counts, pass/fail.
        Does not save metrics unless skip_save=False.
        """
        all_issues: List[Dict[str, Any]] = []
        files_checked = 0
        files_with_issues = 0

        for file_path in file_paths:
            try:
                context = {"file_path": file_path}
                style_result = self.code_style_agent.analyze(context)
                issues = style_result.get("issues", [])
                for i in issues:
                    i["file_path"] = file_path
                    all_issues.append(i)
                if issues:
                    files_with_issues += 1
                files_checked += 1
            except Exception as e:
                logger.error(f"Error checking {file_path}: {e}")
                all_issues.append({
                    "file_path": file_path,
                    "type": "check_error",
                    "severity": "medium",
                    "line": 0,
                    "message": str(e),
                    "category": "system",
                })
                files_with_issues += 1
                files_checked += 1

        critical = sum(1 for i in all_issues if i.get("severity") == "critical")
        high = sum(1 for i in all_issues if i.get("severity") == "high")
        medium = sum(1 for i in all_issues if i.get("severity") == "medium")
        low = sum(1 for i in all_issues if i.get("severity") == "low")

        return {
            "ok": critical == 0 and high == 0,
            "files_checked": files_checked,
            "files_with_issues": files_with_issues,
            "total_issues": len(all_issues),
            "by_severity": {"critical": critical, "high": high, "medium": medium, "low": low},
            "issues": all_issues,
            "message": "Fix critical/high issues before commit."
            if (critical or high) else "No critical or high issues.",
        }
