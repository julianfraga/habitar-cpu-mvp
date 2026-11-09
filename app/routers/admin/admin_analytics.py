"""E-10 Analytics & reports dashboard (coordination + director)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import REQUIERE_ADMIN
from app import services
from app.templating import redirect_to, render

router = APIRouter()


@router.get("")
def dashboard(
    request: Request,
    user: User = Depends(REQUIERE_ADMIN),
    db: Session = Depends(get_db),
):
    return render(
        request, "analytics/dashboard.html", user=user, db=db,
        overview=services.analytics.overview(db),
        top=services.analytics.top_actividades(db),
        per_actividad=services.analytics.asistencia_per_actividad(db),
        surveys=services.analytics.survey_averages(db),
    )


@router.get("/actividad_{actividad_id}")
def detalle(
    request: Request,
    actividad_id: int,
    user: User = Depends(REQUIERE_ADMIN),
    db: Session = Depends(get_db),
):
    a = services.actividades.get(db, actividad_id)
    if a is None:
        return redirect_to(
            request, "panel",
            query_params={"err": "Actividad no encontrada."},
        )
    return render(
        request,
        "analytics/actividad.html",
        user=user,
        db=db,
        a=a,
        **services.analytics.actividad_detalle(db, a),
    )
