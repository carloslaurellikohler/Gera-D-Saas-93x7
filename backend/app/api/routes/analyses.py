from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_analysis_service, get_current_user
from app.core.constants import Objective
from app.core.farol import get_farol_level
from app.db.session import get_db
from app.models.analysis import Analysis, AnalysisStatus
from app.models.user import User, UserRole
from app.repositories.methodology_repository import MethodologyRepository
from app.schemas.analysis import (
    AnalysisListItem,
    AnalysisResponse,
    AnalysisResultResponse,
    AnalysisStatusResponse,
    AnalysisTranscriptionResponse,
)
from app.schemas.common import PaginatedResponse
from app.services.analysis_service import AnalysisService
from app.services.upload_streaming import buffer_upload
from app.services.validation import CorruptedFileError, FileTooLargeError, UnsupportedFileTypeError
from app.workers.tasks import process_analysis_task

router = APIRouter(prefix="/analyses", tags=["analyses"])

_TRANSCRIPTION_READY_STATUSES = {
    AnalysisStatus.TRANSCRIBED,
    AnalysisStatus.ANALYZING,
    AnalysisStatus.GENERATING_REPORTS,
    AnalysisStatus.COMPLETED,
}


def _get_owned_or_404(
    service: AnalysisService, analysis_id: uuid.UUID, current_user: User
) -> Analysis:
    analysis = service.repo.get(analysis_id)
    # Dono ou ADMIN podem ver/alterar; qualquer outro usuário autenticado recebe o
    # mesmo 404 de "não existe", para não revelar a existência de IDs alheios.
    if analysis is None or (
        current_user.role != UserRole.ADMIN and analysis.user_id != current_user.id
    ):
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
    current_user: User = Depends(get_current_user),
):
    try:
        with buffer_upload(
            file.file, service.settings.MAX_UPLOAD_MB, service.settings.STORAGE_DIR
        ) as streamed:
            analysis = service.create_and_store(
                current_user=current_user,
                participant_name=participant_name,
                objective=objective.value,
                objective_complement=objective_complement,
                duration_minutes=duration_minutes,
                interaction_date=interaction_date,
                file_name=file.filename or "arquivo",
                temp_file_path=streamed.path,
                file_size_bytes=streamed.size_bytes,
                file_header=streamed.header,
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
    current_user: User = Depends(get_current_user),
):
    offset = (page - 1) * page_size
    user_id = None if current_user.role == UserRole.ADMIN else current_user.id
    items = service.repo.list(status=status, user_id=user_id, offset=offset, limit=page_size)
    return PaginatedResponse(items=items, total=len(items), page=page, page_size=page_size)


@router.get("/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(
    analysis_id: uuid.UUID,
    service: AnalysisService = Depends(get_analysis_service),
    current_user: User = Depends(get_current_user),
):
    return _get_owned_or_404(service, analysis_id, current_user)


@router.get("/{analysis_id}/status", response_model=AnalysisStatusResponse)
def get_analysis_status(
    analysis_id: uuid.UUID,
    service: AnalysisService = Depends(get_analysis_service),
    current_user: User = Depends(get_current_user),
):
    return _get_owned_or_404(service, analysis_id, current_user)


@router.get("/{analysis_id}/transcription", response_model=AnalysisTranscriptionResponse)
def get_transcription(
    analysis_id: uuid.UUID,
    service: AnalysisService = Depends(get_analysis_service),
    current_user: User = Depends(get_current_user),
):
    analysis = _get_owned_or_404(service, analysis_id, current_user)
    if analysis.status not in _TRANSCRIPTION_READY_STATUSES:
        raise HTTPException(status_code=409, detail="Transcrição ainda não está disponível.")
    return AnalysisTranscriptionResponse(id=analysis.id, transcription=analysis.transcription)


@router.get("/{analysis_id}/report")
def get_report(
    analysis_id: uuid.UUID,
    kind: str = Query("executivo", pattern="^(executivo|detalhado)$"),
    response_format: str = Query("pdf", pattern="^(pdf|json)$", alias="format"),
    service: AnalysisService = Depends(get_analysis_service),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    analysis = _get_owned_or_404(service, analysis_id, current_user)
    if analysis.status != AnalysisStatus.COMPLETED:
        raise HTTPException(status_code=409, detail="A análise ainda não foi concluída.")

    if response_format == "json":
        label_color_map = MethodologyRepository(db).get_label_color_map()
        overall_farol_level = get_farol_level(
            analysis.analysis_result.get("overall_band_label"), label_color_map
        )
        analysis_result = {**analysis.analysis_result, "overall_farol_level": overall_farol_level}
        return AnalysisResultResponse(id=analysis.id, analysis_result=analysis_result)

    ref = analysis.executive_report_path if kind == "executivo" else analysis.detailed_report_path
    if ref is None:
        raise HTTPException(status_code=409, detail="Relatório ainda não foi gerado.")
    return FileResponse(
        service.storage.path(ref), media_type="application/pdf", filename=f"{kind}.pdf"
    )


@router.delete("/{analysis_id}", status_code=204)
def delete_analysis(
    analysis_id: uuid.UUID,
    service: AnalysisService = Depends(get_analysis_service),
    current_user: User = Depends(get_current_user),
):
    analysis = _get_owned_or_404(service, analysis_id, current_user)
    for ref in (analysis.file_path, analysis.executive_report_path, analysis.detailed_report_path):
        if ref:
            service.storage.delete(ref)
    service.repo.delete(analysis_id)
