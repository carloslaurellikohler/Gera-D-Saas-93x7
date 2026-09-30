from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from app.api.deps import get_analysis_service
from app.core.constants import Objective
from app.models.analysis import AnalysisStatus
from app.schemas.analysis import (
    AnalysisListItem,
    AnalysisResponse,
    AnalysisResultResponse,
    AnalysisStatusResponse,
    AnalysisTranscriptionResponse,
)
from app.schemas.common import PaginatedResponse
from app.services.analysis_service import AnalysisService
from app.services.validation import CorruptedFileError, FileTooLargeError, UnsupportedFileTypeError
from app.workers.tasks import process_analysis_task

router = APIRouter(prefix="/analyses", tags=["analyses"])

_TRANSCRIPTION_READY_STATUSES = {
    AnalysisStatus.TRANSCRIBED,
    AnalysisStatus.ANALYZING,
    AnalysisStatus.GENERATING_REPORTS,
    AnalysisStatus.COMPLETED,
}


def _get_or_404(service: AnalysisService, analysis_id: uuid.UUID):
    analysis = service.repo.get(analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Análise não encontrada.")
    return analysis


@router.post("", response_model=AnalysisResponse, status_code=201)
def create_analysis(
    participant_name: str = Form(...),
    objective: Objective = Form(...),
    objective_complement: str | None = Form(None),
    duration_minutes: int | None = Form(None),
    interaction_date: date | None = Form(None),
    file: UploadFile = File(...),
    service: AnalysisService = Depends(get_analysis_service),
):
    content = file.file.read()
    try:
        analysis = service.create_and_store(
            participant_name=participant_name,
            objective=objective.value,
            objective_complement=objective_complement,
            duration_minutes=duration_minutes,
            interaction_date=interaction_date,
            file_name=file.filename or "arquivo",
            file_content=content,
        )
    except (UnsupportedFileTypeError, FileTooLargeError, CorruptedFileError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    process_analysis_task.delay(str(analysis.id))
    return analysis


@router.get("", response_model=PaginatedResponse[AnalysisListItem])
def list_analyses(
    status: AnalysisStatus | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: AnalysisService = Depends(get_analysis_service),
):
    offset = (page - 1) * page_size
    items = service.repo.list(status=status, offset=offset, limit=page_size)
    return PaginatedResponse(items=items, total=len(items), page=page, page_size=page_size)


@router.get("/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(analysis_id: uuid.UUID, service: AnalysisService = Depends(get_analysis_service)):
    return _get_or_404(service, analysis_id)


@router.get("/{analysis_id}/status", response_model=AnalysisStatusResponse)
def get_analysis_status(
    analysis_id: uuid.UUID, service: AnalysisService = Depends(get_analysis_service)
):
    return _get_or_404(service, analysis_id)


@router.get("/{analysis_id}/transcription", response_model=AnalysisTranscriptionResponse)
def get_transcription(
    analysis_id: uuid.UUID, service: AnalysisService = Depends(get_analysis_service)
):
    analysis = _get_or_404(service, analysis_id)
    if analysis.status not in _TRANSCRIPTION_READY_STATUSES:
        raise HTTPException(status_code=409, detail="Transcrição ainda não está disponível.")
    return AnalysisTranscriptionResponse(id=analysis.id, transcription=analysis.transcription)


@router.get("/{analysis_id}/report")
def get_report(
    analysis_id: uuid.UUID,
    kind: str = Query("executivo", pattern="^(executivo|detalhado)$"),
    response_format: str = Query("pdf", pattern="^(pdf|json)$", alias="format"),
    service: AnalysisService = Depends(get_analysis_service),
):
    analysis = _get_or_404(service, analysis_id)
    if analysis.status != AnalysisStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="A análise ainda não foi concluída.")

    if response_format == "json":
        return AnalysisResultResponse(id=analysis.id, analysis_result=analysis.analysis_result)

    ref = analysis.executive_report_path if kind == "executivo" else analysis.detailed_report_path
    if ref is None:
        raise HTTPException(status_code=409, detail="Relatório ainda não foi gerado.")
    return FileResponse(
        service.storage.path(ref), media_type="application/pdf", filename=f"{kind}.pdf"
    )


@router.delete("/{analysis_id}", status_code=204)
def delete_analysis(analysis_id: uuid.UUID, service: AnalysisService = Depends(get_analysis_service)):
    analysis = _get_or_404(service, analysis_id)
    for ref in (analysis.file_path, analysis.executive_report_path, analysis.detailed_report_path):
        if ref:
            service.storage.delete(ref)
    service.repo.delete(analysis_id)
