from fastapi import APIRouter, Depends

from app.core.security import get_current_user_id
from app.services.history_service import get_case_history_service, log_report_export_service


router = APIRouter(
    prefix="/history",
    tags=["History"]
)


@router.get("/cases/{caso_id}")
def get_case_history_route(
    caso_id: str,
    current_user_id: str = Depends(get_current_user_id)
):
    return get_case_history_service(
        current_user_id,
        caso_id
    )


@router.post("/cases/{caso_id}/export", status_code=201)
def log_report_export_route(
    caso_id: str,
    formato: str = "PDF",
    current_user_id: str = Depends(get_current_user_id)
):
    # formato é só um texto para o histórico; limita o tamanho e os valores
    formato = formato.upper() if formato.upper() in ("PDF", "CSV") else "PDF"
    return log_report_export_service(current_user_id, caso_id, formato)
