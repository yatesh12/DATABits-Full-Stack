from fastapi import APIRouter

from api.v1.auth.routes import router as auth_router
from api.v1.datasets.routes import router as datasets_router
from api.v1.billing.routes import router as billing_router
from api.v1.health.routes import router as health_router
from api.v1.upload.routes import router as upload_router
from api.v1.ingestion.routes import router as ingestion_router
from api.v1.user.routes import router as user_router
from api.v1.jobs.routes import router as jobs_router
from api.v1.workflow.routes import router as workflow_router
from api.v1.assistant.routes import router as assistant_router
from api.v1.audit.routes import router as audit_router
from api.v1.community.routes import router as community_router
from api.v1.ecosystem.routes import router as ecosystem_router
from api.v1.network.routes import router as network_router
from api.v1.events.routes import router as events_router
from api.v1.support.routes import router as support_router
from api.v1.advanced.routes import router as advanced_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(datasets_router)
api_router.include_router(billing_router)
api_router.include_router(health_router)
api_router.include_router(upload_router)
api_router.include_router(ingestion_router)
api_router.include_router(user_router)
api_router.include_router(jobs_router)
api_router.include_router(workflow_router)
api_router.include_router(assistant_router)
api_router.include_router(audit_router)
api_router.include_router(community_router)
api_router.include_router(ecosystem_router)
api_router.include_router(network_router)
api_router.include_router(events_router)
api_router.include_router(support_router)
api_router.include_router(advanced_router)

__all__ = ["api_router"]
