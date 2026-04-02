"""Ingestion endpoints — supports both sync (legacy) and async job-based modes.

Canonical endpoint: POST /api/ingest/artifact
Legacy endpoints (kept for backward compat): /transcript/async, /transcript, /text
"""

import asyncio
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Query, UploadFile, File

from app.dependencies import get_driver, get_llm
from app.models.api import IngestJobResponse, IngestResponse, JobState
from app.models.artifact import ArtifactIngestRequest
from app.services import job_service
from app.services.github.github_app import GitHubAuth
from app.services.artifact_classifier import classify_from_metadata, classify_from_content_preview
from app.services.artifact_router import get_artifact_router
from app.services.diff_service import DiffService
from app.services.ingestion_service import IngestionService
from app.services.pipeline_runner import get_pipeline_runner

router = APIRouter(prefix="/api/ingest", tags=["ingest"])


async def _run_ingest_job(
    job_id: str,
    transcript: str,
    meeting_title: str,
    meeting_date: str,
    participants: list[str],
    driver,
    llm,
) -> None:
    """Background task: run transcript ingestion and update job state in real time.

    Delegates to the RocketRide engine when configured; falls back to in-process
    execution otherwise.
    """
    since_ts = datetime.now(timezone.utc).isoformat()
    diff_svc = DiffService(driver)
    before_snapshot = await diff_svc.snapshot_before()

    await job_service.mark_running(job_id)
    try:
        runner = get_pipeline_runner()
        pipe_path = runner.pipe_path_for("transcript") if runner.is_available() else None

        if pipe_path:
            # --- RocketRide execution path ---
            rr_result = await runner.run_pipe(
                pipe_path,
                {
                    "transcript": transcript,
                    "meeting_title": meeting_title,
                    "meeting_date": meeting_date,
                    "participants": participants,
                },
                artifact_type="transcript",
                job_emitter=job_service.make_emitter(job_id),
            )
            entities_created = rr_result.get("entities_created", {})
            meeting_id = rr_result.get("meeting_id", "")
        else:
            # --- In-process fallback ---
            service = IngestionService(driver, llm)
            result = await service.ingest_transcript(
                transcript=transcript,
                meeting_title=meeting_title,
                meeting_date=meeting_date,
                participants=participants,
                job_emitter=job_service.make_emitter(job_id),
            )
            entities_created = result.entities_created
            meeting_id = result.meeting_id

        # Compute twin diff
        await job_service.stage_started(job_id, "twin_diff")
        twin_diff = await diff_svc.compute_diff(before_snapshot, since_ts)
        await job_service.stage_completed(
            job_id,
            "twin_diff",
            entities_found=(
                len(twin_diff.new_decisions)
                + len(twin_diff.new_assumptions)
                + len(twin_diff.new_evidence)
            ),
        )

        await job_service.mark_completed(
            job_id,
            entities_created=entities_created,
            twin_diff=twin_diff,
            meeting_id=meeting_id,
        )
    except asyncio.CancelledError:
        await job_service.mark_failed(job_id, "Job cancelled (server shutdown or reload)")
        raise
    except Exception as exc:
        await job_service.mark_failed(job_id, str(exc))
        raise


async def _run_artifact_job(
    job_id: str,
    request: ArtifactIngestRequest,
    raw_content: Optional[bytes | str],
    driver,
    llm,
) -> None:
    """Background task: run artifact ingestion via the router/adapter pattern.

    Delegates to the RocketRide engine when configured; falls back to in-process
    execution otherwise.
    """
    since_ts = datetime.now(timezone.utc).isoformat()
    diff_svc = DiffService(driver)
    before_snapshot = await diff_svc.snapshot_before()

    await job_service.mark_running(job_id)
    try:
        runner = get_pipeline_runner()
        pipe_path = runner.pipe_path_for(request.artifact_type) if runner.is_available() else None

        artifact_id: Optional[str] = None
        entities_created: dict = {}

        if pipe_path:
            # --- RocketRide execution path ---
            # Build a JSON-serialisable payload combining metadata and text content
            content_text = ""
            if isinstance(raw_content, bytes):
                try:
                    content_text = raw_content.decode("utf-8", errors="replace")
                except Exception:
                    content_text = ""
            elif isinstance(raw_content, str):
                content_text = raw_content

            rr_payload: dict = {
                "artifact_type": request.artifact_type,
                "source_type": request.source_type,
                "workspace_id": request.workspace_id,
                "sensitivity": request.sensitivity,
                "meeting_title": request.meeting_title,
                "meeting_date": request.meeting_date,
                "participants": request.participants,
                "github_repo_url": request.github_repo_url,
                "github_branch": request.github_branch,
                "source_url": request.source_url,
                "metadata": request.metadata,
                "content": content_text,
            }

            rr_result = await runner.run_pipe(
                pipe_path,
                rr_payload,
                artifact_type=request.artifact_type,
                job_emitter=job_service.make_emitter(job_id),
            )
            artifact_id = rr_result.get("artifact_id")
            entities_created = rr_result.get("entities_created", {})
        else:
            # --- In-process fallback ---
            router_svc = get_artifact_router()
            result = await router_svc.route(
                request=request,
                raw_content=raw_content,
                driver=driver,
                llm=llm,
                job_emitter=job_service.make_emitter(job_id),
            )
            artifact_id = result.artifact_id
            entities_created = result.entities_created

        # Update artifact_id on the job state
        state = job_service.get_job(job_id)
        if state and artifact_id:
            state.artifact_id = artifact_id

        # Compute twin diff for graph-change summary
        if "twin_diff" in job_service.PIPELINE_STAGES:
            await job_service.stage_started(job_id, "twin_diff")
            twin_diff = await diff_svc.compute_diff(before_snapshot, since_ts)
            await job_service.stage_completed(
                job_id,
                "twin_diff",
                entities_found=(
                    len(twin_diff.new_decisions)
                    + len(twin_diff.new_assumptions)
                    + len(twin_diff.new_evidence)
                ),
            )
        else:
            twin_diff = await diff_svc.compute_diff(before_snapshot, since_ts)

        await job_service.mark_completed(
            job_id,
            entities_created=entities_created,
            twin_diff=twin_diff,
            meeting_id=None,
        )
    except asyncio.CancelledError:
        await job_service.mark_failed(job_id, "Job cancelled (server shutdown or reload)")
        raise
    except Exception as exc:
        await job_service.mark_failed(job_id, str(exc))
        raise


@router.post("/artifact", response_model=IngestJobResponse)
async def ingest_artifact(
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    metadata: str = Form("{}"),
    artifact_type: Optional[str] = Form(None),
    source_type: str = Form("upload"),
    mime_type: Optional[str] = Form(None),
    workspace_id: str = Form("default"),
    sensitivity: str = Form("internal"),
    ingest_mode: str = Form("async"),
    principal_user_id: str = Form("anonymous"),
    meeting_title: Optional[str] = Form(None),
    meeting_date: Optional[str] = Form(None),
    participants: str = Form(""),
    github_repo_url: Optional[str] = Form(None),
    github_branch: str = Form("main"),
    driver=Depends(get_driver),
    llm=Depends(get_llm),
) -> IngestJobResponse:
    """Canonical artifact ingestion endpoint.

    Accepts a multipart form with an optional file upload plus metadata fields.
    Automatically classifies the artifact type when not explicitly provided.
    Returns a job_id immediately; stream progress via WebSocket at /ws/jobs/{job_id}.
    """
    raw_content: Optional[bytes] = None
    detected_mime = mime_type
    filename: Optional[str] = None

    if file:
        raw_content = await file.read()
        detected_mime = detected_mime or file.content_type
        filename = file.filename

    # Parse metadata JSON
    try:
        meta = json.loads(metadata) if metadata else {}
    except json.JSONDecodeError:
        meta = {}

    # Determine artifact type
    resolved_type = artifact_type
    if not resolved_type:
        resolved_type = classify_from_metadata(
            mime_type=detected_mime,
            filename=filename,
            title=meta.get("title") or meeting_title,
        )
        if resolved_type == "generic_text" and raw_content:
            # Try content-based classification as a second pass
            try:
                preview = raw_content[:500].decode("utf-8", errors="replace")
                resolved_type = classify_from_content_preview(preview)
            except Exception:
                pass

    participant_list = [p.strip() for p in participants.split(",") if p.strip()]

    request = ArtifactIngestRequest(
        artifact_type=resolved_type,
        source_type=source_type,
        mime_type=detected_mime,
        workspace_id=workspace_id,
        sensitivity=sensitivity,
        ingest_mode=ingest_mode,
        principal_user_id=principal_user_id,
        metadata={**meta, "filename": filename} if filename else meta,
        meeting_title=meeting_title,
        meeting_date=meeting_date,
        participants=participant_list,
        github_repo_url=github_repo_url,
        github_branch=github_branch,
    )

    artifact_title = (
        meeting_title
        or meta.get("title")
        or (filename or "")
        or github_repo_url
        or f"Artifact ({resolved_type})"
    )

    # Get pipeline stages from the router
    from app.services.artifact_router import get_artifact_router
    router_svc = get_artifact_router()
    stages = router_svc.pipeline_stages_for(resolved_type)

    job_id = str(uuid.uuid4())
    job_service.create_job(
        job_id=job_id,
        artifact_title=artifact_title,
        artifact_type=resolved_type,
        stages=stages,
    )

    asyncio.create_task(
        _run_artifact_job(job_id, request, raw_content, driver, llm)
    )

    return IngestJobResponse(job_id=job_id, artifact_type=resolved_type)


@router.post("/artifact/url", response_model=IngestJobResponse)
async def ingest_artifact_url(
    payload: dict,
    driver=Depends(get_driver),
    llm=Depends(get_llm),
) -> IngestJobResponse:
    """Ingest an artifact from a URL, GCS path, or GitHub repo reference.

    Accepts JSON body with ArtifactIngestRequest fields.
    """
    request = ArtifactIngestRequest(**payload)
    artifact_title = (
        request.meeting_title
        or request.metadata.get("title", "")
        or request.github_repo_url
        or request.source_url
        or f"Artifact ({request.artifact_type})"
    )

    from app.services.artifact_router import get_artifact_router
    router_svc = get_artifact_router()
    stages = router_svc.pipeline_stages_for(request.artifact_type)

    job_id = str(uuid.uuid4())
    job_service.create_job(
        job_id=job_id,
        artifact_title=artifact_title,
        artifact_type=request.artifact_type,
        stages=stages,
    )

    asyncio.create_task(
        _run_artifact_job(job_id, request, None, driver, llm)
    )

    return IngestJobResponse(job_id=job_id, artifact_type=request.artifact_type)


@router.post("/transcript/async", response_model=IngestJobResponse)
async def ingest_transcript_async(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    meeting_title: str = Form(...),
    meeting_date: str = Form(...),
    participants: str = Form(...),
    driver=Depends(get_driver),
    llm=Depends(get_llm),
) -> IngestJobResponse:
    """Submit an ingestion job and return a job_id immediately.
    Stream progress via WebSocket at /ws/jobs/{job_id}.
    """
    content = await file.read()
    try:
        transcript = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded text")

    participant_list = [p.strip() for p in participants.split(",") if p.strip()]
    job_id = str(uuid.uuid4())
    job_service.create_job(job_id, artifact_title=meeting_title, artifact_type="transcript")

    # Run ingestion in background so we can return the job ID immediately
    asyncio.create_task(
        _run_ingest_job(job_id, transcript, meeting_title, meeting_date, participant_list, driver, llm)
    )

    return IngestJobResponse(job_id=job_id)


@router.post("/transcript", response_model=IngestResponse)
async def ingest_transcript(
    file: UploadFile = File(...),
    meeting_title: str = Form(...),
    meeting_date: str = Form(...),
    participants: str = Form(...),
    driver=Depends(get_driver),
    llm=Depends(get_llm),
) -> IngestResponse:
    """Synchronous ingestion — blocks until complete. Legacy / test endpoint."""
    content = await file.read()
    try:
        transcript = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded text")

    participant_list = [p.strip() for p in participants.split(",") if p.strip()]
    service = IngestionService(driver, llm)
    return await service.ingest_transcript(transcript, meeting_title, meeting_date, participant_list)


@router.post("/text", response_model=IngestJobResponse)
async def ingest_text(
    payload: dict,
    driver=Depends(get_driver),
    llm=Depends(get_llm),
) -> IngestJobResponse:
    """Ingest transcript from JSON body and return a job ID for streaming."""
    transcript = payload.get("transcript", "")
    meeting_title = payload.get("meeting_title", "Untitled Meeting")
    meeting_date = payload.get("meeting_date", "2026-04-01")
    participants = payload.get("participants", [])

    job_id = str(uuid.uuid4())
    job_service.create_job(job_id, artifact_title=meeting_title, artifact_type="transcript")

    asyncio.create_task(
        _run_ingest_job(job_id, transcript, meeting_title, meeting_date, participants, driver, llm)
    )

    return IngestJobResponse(job_id=job_id)


@router.post("/bundle", response_model=dict)
async def ingest_bundle(
    payload: dict,
    driver=Depends(get_driver),
    llm=Depends(get_llm),
) -> dict:
    """Ingest a named bundle of multiple artifacts in parallel.

    Request body:
    {
        "bundle_name": "Q2 Launch Planning",
        "artifacts": [
            {"artifact_type": "prd", "source_url": "...", "metadata": {...}},
            {"artifact_type": "github_repo", "github_repo_url": "..."},
            ...
        ],
        "cross_link": true
    }

    Returns immediately with a list of job_ids, one per artifact.
    """
    bundle_name = payload.get("bundle_name", "Unnamed Bundle")
    artifacts_data = payload.get("artifacts", [])
    cross_link = payload.get("cross_link", True)

    if not artifacts_data:
        raise HTTPException(status_code=400, detail="No artifacts provided")

    job_ids: list[str] = []
    from app.services.artifact_router import get_artifact_router
    router_svc = get_artifact_router()

    for art_data in artifacts_data:
        try:
            request = ArtifactIngestRequest(**art_data)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid artifact config: {e}")

        artifact_title = (
            request.meeting_title
            or request.metadata.get("title", "")
            or request.github_repo_url
            or request.source_url
            or f"{request.artifact_type} in {bundle_name}"
        )
        stages = router_svc.pipeline_stages_for(request.artifact_type)
        job_id = str(uuid.uuid4())
        job_service.create_job(
            job_id=job_id,
            artifact_title=artifact_title,
            artifact_type=request.artifact_type,
            stages=stages,
        )
        # Launch in parallel — all artifacts ingest concurrently
        asyncio.create_task(
            _run_artifact_job(job_id, request, None, driver, llm)
        )
        job_ids.append(job_id)

    return {
        "bundle_name": bundle_name,
        "job_ids": job_ids,
        "artifact_count": len(job_ids),
        "cross_link": cross_link,
    }


@router.get("/jobs", response_model=list[JobState])
async def list_jobs(limit: int = Query(default=20, le=100)) -> list[JobState]:
    return job_service.list_jobs(limit)


@router.get("/jobs/{job_id}", response_model=JobState)
async def get_job(job_id: str) -> JobState:
    job = job_service.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/github/branches")
async def get_github_branches(repo_url: str = Query(...)) -> dict:
    """Return branch list and default branch for a GitHub repository."""
    match = re.match(
        r"https?://github\.com/([^/]+)/([^/\s?#]+?)(?:\.git)?$",
        repo_url.strip(),
    )
    if not match:
        raise HTTPException(status_code=400, detail="Invalid GitHub repository URL")

    owner, repo = match.group(1), match.group(2)
    auth = GitHubAuth()
    try:
        token = await auth.get_token()
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc))

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            repo_resp = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}",
                headers=headers,
            )
            repo_resp.raise_for_status()
            default_branch = repo_resp.json().get("default_branch", "main")

            branches_resp = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/branches",
                headers=headers,
                params={"per_page": 100},
            )
            branches_resp.raise_for_status()
            branches = [b["name"] for b in branches_resp.json()]
        except httpx.HTTPStatusError as exc:
            raise HTTPException(
                status_code=exc.response.status_code,
                detail=f"GitHub API error: {exc.response.text}",
            )

    return {"branches": branches, "default_branch": default_branch}
