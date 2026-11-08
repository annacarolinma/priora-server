from fastapi import APIRouter

from app.api.routes.user_routes import router as user_router
from app.api.routes.case_routes import router as case_router
from app.api.routes.access_routes import router as access_router
from app.api.routes.evidence_routes import router as evidence_router
from app.api.routes.suspect_routes import router as suspect_router
from app.api.routes.analysis_routes import router as analysis_router
from app.api.routes.contact_routes import router as contact_router
from app.api.routes import bayes_routes
from app.api.routes.investigation_board_routes import router as investigation_board_router
from app.api.routes.priority_routes import router as priority_router
from app.api.routes.history_routes import router as history_router
from app.api.routes.support import router as support_router
from app.api.routes.notification_routes import router as notification_router

router = APIRouter()

router.include_router(user_router)
router.include_router(case_router)
router.include_router(access_router)
router.include_router(evidence_router)
router.include_router(suspect_router)
router.include_router(analysis_router)
router.include_router(contact_router)
router.include_router(bayes_routes.router)
router.include_router(investigation_board_router)
router.include_router(priority_router)
router.include_router(history_router)
router.include_router(support_router)
router.include_router(notification_router)
