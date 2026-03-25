# backend/api/routes/analysis.py

import asyncio
import os
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from data.metrics_store import MetricsStore
from orchestrator.langgraph_workflow import DecayAnalysisWorkflow
from utils.config import config
from utils.github_ingest import (
    list_analyzable_files,
    prepare_github_workdir,
    repo_collaboration_hints,
)
from utils.logger import setup_logger
from utils.qa_path_validation import (
    validate_file_in_repo,
    validate_file_paths_batch,
    validate_repo_path,
)

from api.deps import client_error_detail, verify_api_key

logger = setup_logger(__name__)
router = APIRouter(dependencies=[Depends(verify_api_key)])

workflow_instance = None
metrics_store = MetricsStore()


class AnalyzeFileRequest(BaseModel):
    file_path: str = Field(..., max_length=config.MAX_PATH_LENGTH)
    repo_path: str = Field(..., max_length=config.MAX_PATH_LENGTH)


class AnalyzeProjectRequest(BaseModel):
    repo_path: str = Field(..., max_length=config.MAX_PATH_LENGTH)
    file_extensions: Optional[List[str]] = Field(default_factory=lambda: [".py", ".js", ".ts"])


class AnalysisResponse(BaseModel):
    file_path: str
    status: str
    decay_score: Optional[float] = None
    risk_level: Optional[str] = None
    prediction: Optional[dict] = None


class PreCommitRequest(BaseModel):
    repo_path: str = Field(..., max_length=config.MAX_PATH_LENGTH)
    file_paths: List[str]


class GithubAnalyzeRequest(BaseModel):
    """Analyze a public GitHub repository or a single raw file from GitHub."""

    url: str = Field(..., max_length=2048, description="https://github.com/... or raw.githubusercontent.com/...")
    ref: Optional[str] = Field(
        default=None,
        max_length=256,
        description="Optional branch or tag override when cloning",
    )
    file_extensions: Optional[List[str]] = Field(
        default_factory=lambda: [".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java"],
    )


def _resolve_github_walk_and_focus(
    repo_root: str, path_in_repo: Optional[str], is_raw_file: bool
) -> Tuple[Optional[str], Optional[str]]:
    """
    For github.com blob/tree URLs, return (focus_file_relative, walk_root_abs).
    focus is relative path for prioritization; walk_root limits directory scans.
    """
    if is_raw_file or not path_in_repo:
        return None, None
    full = os.path.normpath(os.path.join(repo_root, path_in_repo.replace("/", os.sep)))
    rr = os.path.realpath(repo_root)
    try:
        cr = os.path.realpath(full)
    except OSError:
        return None, None
    if not (cr == rr or cr.startswith(rr + os.sep)):
        return None, None
    if os.path.isfile(cr):
        return path_in_repo, None
    if os.path.isdir(cr):
        return None, cr
    return None, None


def _build_shareability_recommendations(
    hygiene: Dict[str, bool],
    style_by_category: Counter,
    style_by_severity: Counter,
    high_risk_count: int,
    avg_decay: float,
) -> List[str]:
    """Actionable suggestions for maintainers and external contributors."""
    out: List[str] = []
    if not hygiene.get("has_readme"):
        out.append(
            "Add a README with install steps, how to run tests, and a short architecture overview so others can onboard quickly."
        )
    if not hygiene.get("has_license"):
        out.append(
            "Add a LICENSE file so downstream users know how they may use and redistribute the code."
        )
    if not hygiene.get("has_gitignore"):
        out.append(
            "Add a .gitignore for build artifacts, virtualenvs, and editor files to keep clones clean for collaborators."
        )
    if not hygiene.get("has_contributing"):
        out.append(
            "Consider CONTRIBUTING.md with PR expectations, coding style, and how to report issues."
        )
    if style_by_severity.get("critical", 0) > 0:
        out.append(
            "Address critical style findings (e.g. possible secrets in source) before sharing the repository publicly."
        )
    if style_by_category.get("ai_style", 0) >= 5:
        out.append(
            "Several AI-style signals (heavy comments, placeholders, generic names) were detected; tighten naming and trim redundant comments so intent is obvious to human reviewers."
        )
    if high_risk_count > 0:
        out.append(
            f"{high_risk_count} file(s) scored high or critical decay risk; prioritize refactors or tests in those areas before external contributions spike."
        )
    elif avg_decay >= 50:
        out.append(
            "Average decay risk is elevated; schedule focused refactors and add regression tests to stabilize areas new contributors will touch."
        )
    if style_by_category.get("bug_prone_style", 0) >= 8:
        out.append(
            "Multiple bug-prone patterns (broad exception handling, magic numbers, etc.) suggest tightening error handling and extracting constants for safer collaboration."
        )
    return out


@router.post("/file", response_model=AnalysisResponse)
async def analyze_file(request: AnalyzeFileRequest):
    """Analyze a single file (must be inside the repository)."""
    logger.info("Analysis request for file")

    ok_repo, repo_real = validate_repo_path(request.repo_path)
    if not ok_repo or not repo_real:
        raise HTTPException(status_code=404, detail=repo_real or "Repository not found")

    ok_file, file_real = validate_file_in_repo(repo_real, request.file_path)
    if not ok_file or not file_real:
        raise HTTPException(
            status_code=400,
            detail="File not found or path outside repository",
        )

    try:
        global workflow_instance
        if workflow_instance is None or getattr(
            workflow_instance, "repo_path", None
        ) != repo_real:
            workflow_instance = DecayAnalysisWorkflow(repo_real)

        result = await asyncio.to_thread(
            workflow_instance.analyze_file, file_real
        )
        prediction = result.get("prediction", {})

        return AnalysisResponse(
            file_path=file_real,
            status=result.get("status", "error"),
            decay_score=prediction.get("decay_score"),
            risk_level=prediction.get("risk_level"),
            prediction=prediction,
        )

    except Exception as e:
        logger.exception("Error analyzing file")
        raise HTTPException(
            status_code=500,
            detail=client_error_detail("Analysis failed", e),
        )


@router.post("/project")
async def analyze_project(
    request: AnalyzeProjectRequest,
    background_tasks: BackgroundTasks,
):
    """Analyze entire project (background task)."""
    logger.info("Project analysis request")

    ok_repo, repo_real = validate_repo_path(request.repo_path)
    if not ok_repo or not repo_real:
        raise HTTPException(status_code=404, detail=repo_real or "Repository not found")

    background_tasks.add_task(
        _analyze_project_background,
        repo_real,
        request.file_extensions or [".py", ".js", ".ts"],
    )

    return {
        "status": "started",
        "message": "Project analysis started",
        "repo_path": repo_real,
    }


def _analyze_project_background(
    repo_path: str, file_extensions: List[str]
):
    """Background task to analyze entire project"""
    logger.info(f"Background analysis starting for {repo_path}")

    try:
        workflow = DecayAnalysisWorkflow(repo_path)
        files_to_analyze = []

        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [
                d
                for d in dirs
                if d
                not in [".git", "node_modules", "__pycache__", "venv", ".venv"]
            ]
            for file in files:
                if any(file.endswith(ext) for ext in file_extensions):
                    file_path = os.path.join(root, file)
                    if os.path.getsize(file_path) <= config.MAX_FILE_BYTES_FOR_SCAN:
                        files_to_analyze.append(file_path)

        logger.info(f"Found {len(files_to_analyze)} files to analyze")

        for i, file_path in enumerate(files_to_analyze):
            try:
                logger.info(
                    f"Analyzing {i+1}/{len(files_to_analyze)}: {file_path}"
                )
                workflow.analyze_file(file_path)
            except Exception as e:
                logger.error(f"Error analyzing {file_path}: {e}")
                continue

        logger.info(
            f"Project analysis complete: {len(files_to_analyze)} files analyzed"
        )

    except Exception as e:
        logger.error(f"Error in background analysis: {e}")


@router.post("/pre-commit")
async def check_before_commit(request: PreCommitRequest):
    """
    Run style and bug-prone checks on files (e.g. staged for commit).
    Paths must resolve inside the repository; oversized files are skipped.
    """
    logger.info(f"Pre-commit check for {len(request.file_paths)} paths")

    if len(request.file_paths) > config.MAX_PRE_COMMIT_FILES * 2:
        raise HTTPException(
            status_code=400,
            detail=f"Too many paths (max {config.MAX_PRE_COMMIT_FILES * 2} per request)",
        )

    if not request.file_paths:
        return {
            "ok": True,
            "files_checked": 0,
            "files_with_issues": 0,
            "total_issues": 0,
            "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "issues": [],
            "message": "No files to check.",
            "paths_rejected": 0,
        }

    ok_repo, repo_real = validate_repo_path(request.repo_path)
    if not ok_repo or not repo_real:
        raise HTTPException(status_code=404, detail=repo_real or "Repository not found")

    valid_paths, rejected = validate_file_paths_batch(
        repo_real, request.file_paths
    )

    if len(request.file_paths) > config.MAX_PRE_COMMIT_FILES:
        logger.warning(
            f"Pre-commit: truncated to {config.MAX_PRE_COMMIT_FILES} files"
        )

    if not valid_paths:
        return {
            "ok": True,
            "files_checked": 0,
            "files_with_issues": 0,
            "total_issues": 0,
            "by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0},
            "issues": [],
            "message": "No valid files to check (outside repo, missing, or too large).",
            "paths_rejected": rejected,
        }

    try:
        global workflow_instance
        if workflow_instance is None or getattr(
            workflow_instance, "repo_path", None
        ) != repo_real:
            workflow_instance = DecayAnalysisWorkflow(repo_real)

        report = workflow_instance.check_files_for_commit(
            valid_paths, skip_save=True
        )
        report["paths_rejected"] = rejected
        return report
    except Exception as e:
        logger.exception("Error in pre-commit check")
        raise HTTPException(
            status_code=500,
            detail=client_error_detail("Pre-commit check failed", e),
        )


@router.post("/github")
async def analyze_github(request: GithubAnalyzeRequest):
    """
    Clone or fetch from GitHub, analyze up to MAX_GITHUB_ANALYSIS_FILES source files,
    and return decay predictions, style findings, and shareability-oriented guidance.
    Does not persist metrics to the local DB.
    """
    logger.info("GitHub analysis request url_len=%s", len(request.url))
    try:
        parsed, workdir = prepare_github_workdir(request.url, request.ref)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("GitHub ingest failed")
        raise HTTPException(
            status_code=502,
            detail=client_error_detail(
                "Could not fetch GitHub source (check URL, network, or git install)",
                e,
            ),
        )
    try:
        ok_repo, repo_real = validate_repo_path(workdir.root)
        if not ok_repo or not repo_real:
            raise HTTPException(status_code=500, detail="Invalid work directory")

        focus_rel, walk_override = _resolve_github_walk_and_focus(
            repo_real,
            parsed.path_in_repo,
            parsed.is_raw_file,
        )
        exts = request.file_extensions or [
            ".py",
            ".js",
            ".ts",
            ".jsx",
            ".tsx",
            ".go",
            ".rs",
            ".java",
        ]
        all_files = list_analyzable_files(
            repo_real,
            exts,
            focus_path=focus_rel,
            walk_root=walk_override,
        )
        max_n = config.MAX_GITHUB_ANALYSIS_FILES
        skipped = max(0, len(all_files) - max_n)
        files_to_run = all_files[:max_n]

        if not files_to_run:
            hygiene = repo_collaboration_hints(repo_real)
            return {
                "status": "completed",
                "source": {
                    "url": request.url,
                    "owner": parsed.owner,
                    "repo": parsed.repo,
                    "ref": request.ref or parsed.ref,
                    "path_in_repo": parsed.path_in_repo,
                    "is_raw_file": parsed.is_raw_file,
                },
                "summary": {
                    "files_analyzed": 0,
                    "files_skipped_oversize_or_truncated": skipped,
                    "message": "No matching source files under size limits.",
                },
                "repo_hygiene": hygiene,
                "shareability_recommendations": _build_shareability_recommendations(
                    hygiene, Counter(), Counter(), 0, 0.0
                ),
                "style_summary": {},
                "file_results": [],
            }

        workflow = DecayAnalysisWorkflow(repo_real)
        file_results: List[Dict[str, Any]] = []
        style_by_category: Counter = Counter()
        style_by_severity: Counter = Counter()
        predicted_issue_types: Counter = Counter()
        decay_scores: List[float] = []
        high_risk_files: List[Dict[str, Any]] = []

        for fp in files_to_run:
            try:
                state = workflow.analyze_file(fp, persist=False)
                style = workflow.code_style_agent.analyze({"file_path": fp})
                pred = state.get("prediction") or {}
                issues = style.get("issues") or []
                for it in issues:
                    style_by_category[it.get("category") or "unknown"] += 1
                    style_by_severity[it.get("severity") or "low"] += 1
                for p in pred.get("predicted_issues") or []:
                    predicted_issue_types[p.get("type") or "unknown"] += 1
                ds = float(pred.get("decay_score") or 0)
                decay_scores.append(ds)
                risk = pred.get("risk_level") or ""
                entry: Dict[str, Any] = {
                    "file_path": fp,
                    "status": state.get("status"),
                    "decay_score": pred.get("decay_score"),
                    "risk_level": risk,
                    "predicted_issues": pred.get("predicted_issues"),
                    "recommendations": pred.get("recommendations"),
                    "style_issues": issues[:25],
                    "style_issue_count": len(issues),
                }
                file_results.append(entry)
                if risk in ("high", "critical"):
                    high_risk_files.append(
                        {
                            "file_path": fp,
                            "decay_score": pred.get("decay_score"),
                            "risk_level": risk,
                            "recommendations": pred.get("recommendations"),
                        }
                    )
            except Exception as e:
                logger.error("GitHub analysis error for %s: %s", fp, e)
                file_results.append(
                    {
                        "file_path": fp,
                        "status": "error",
                        "error": str(e),
                    }
                )

        avg_decay = (
            sum(decay_scores) / len(decay_scores) if decay_scores else 0.0
        )
        hygiene = repo_collaboration_hints(repo_real)
        share = _build_shareability_recommendations(
            hygiene,
            style_by_category,
            style_by_severity,
            len(high_risk_files),
            avg_decay,
        )

        return {
            "status": "completed",
            "source": {
                "url": request.url,
                "owner": parsed.owner,
                "repo": parsed.repo,
                "ref": request.ref or parsed.ref,
                "path_in_repo": parsed.path_in_repo,
                "is_raw_file": parsed.is_raw_file,
            },
            "summary": {
                "files_analyzed": len(files_to_run),
                "files_skipped_oversize_or_truncated": skipped,
                "avg_decay_score": round(avg_decay, 2),
                "highest_risk_files": sorted(
                    high_risk_files,
                    key=lambda x: float(x.get("decay_score") or 0),
                    reverse=True,
                )[:15],
            },
            "repo_hygiene": hygiene,
            "future_risk_overview": {
                "predicted_issue_types": dict(predicted_issue_types.most_common(20)),
            },
            "style_summary": {
                "total_issues": sum(style_by_severity.values()),
                "by_category": dict(style_by_category),
                "by_severity": dict(style_by_severity),
            },
            "shareability_recommendations": share,
            "file_results": file_results,
        }
    finally:
        workdir.cleanup()


@router.get("/status/{file_path:path}")
async def get_analysis_status(file_path: str):
    """Get latest analysis status for a file."""
    if len(file_path) > config.MAX_PATH_LENGTH:
        raise HTTPException(status_code=400, detail="Path too long")
    try:
        prediction = metrics_store.get_latest_prediction(file_path)

        if not prediction:
            return {
                "status": "not_analyzed",
                "file_path": file_path,
            }

        return {
            "status": "analyzed",
            "file_path": file_path,
            "decay_score": prediction.decay_score,
            "risk_level": prediction.risk_level,
            "timestamp": prediction.timestamp.isoformat(),
            "prediction": {
                "decay_score": prediction.decay_score,
                "risk_level": prediction.risk_level,
                "confidence": prediction.confidence,
                "predicted_issues": prediction.predicted_issues,
                "recommendations": prediction.recommendations,
            },
        }

    except Exception as e:
        logger.exception("Error getting analysis status")
        raise HTTPException(
            status_code=500,
            detail=client_error_detail("Status lookup failed", e),
        )
