from fastapi import APIRouter


# Mantido registrado em app.main para a interface HTML/HTMX da próxima etapa.
router = APIRouter(prefix="/comments", tags=["comments"])
