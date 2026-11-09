"""E-08 Actividad management (coordination backoffice)."""
from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session
from starlette.templating import _TemplateResponse
import io
import pandas as pd
from app.database import get_db
from app.models import (
    Asistencia,
    Inscripcion,
    INSCRIPCION_ALTA,
    ESTADO_CANCELADA,
    ESTADO_CREDITOS_PENDIENTE_ENCUESTA,
    ESTADO_PUBLICADA,
    TIPO_PRESENCIAL,
    TIPO_VIRTUAL,
    Actividad,
    User
)
from app.services.consultas_comunes import get_docentes
from app.services.notifications import notify
from app.security import REQUIERE_ADMIN
from app import services 
from app.schemas.forms import ActividadForm
from app.templating import build_sort_links, redirect_to, render

router = APIRouter()


@router.get("")
def panel(
    request: Request,
    carreras_asociadas: list[str] = Query([]),
    sort: str = Query(""),
    direction: str = Query(""),
    user: User = Depends(REQUIERE_ADMIN),
    db: Session = Depends(get_db),
) -> _TemplateResponse:
    sort = sort if sort in {"nombre", "fecha", "cupo", "estado"} else ""
    defaults = {"nombre": "asc", "fecha": "desc", "cupo": "desc", "estado": "asc"}
    direction = direction if direction in {"asc", "desc"} else defaults.get(sort, "")
    items = services.actividades.list_all(
        db, carreras_ids=carreras_asociadas, orden=sort or None, direccion=direction or None
    )
    rows = [{"a": a, "cupo": services.actividades.cupo_info(db, a)} for a in items]
    resumen = {
        "publicadas": sum(1 for a in items if a.estado == ESTADO_PUBLICADA),
        "finalizadas": sum(1 for a in items if (a.estado == ESTADO_PUBLICADA and a.finalizada)),
        "canceladas": sum(1 for a in items if a.estado == ESTADO_CANCELADA),
        "vencidas": sum(1 for a in items if (a.estado != ESTADO_PUBLICADA and a.finalizada)),
        "total": len(items),
    }
    lista_carreras = services.carreras.get_carreras(db)
    return render(
        request,
        "admin/panel.html",
        user=user,
        db=db,
        rows=rows,
        resumen=resumen,
        lista_carreras=lista_carreras,
        carreras_seleccionadas=carreras_asociadas,
        sort=sort,
        direction=direction,
        sort_links=build_sort_links(
            request,
            "panel",
            ("nombre", "fecha", "cupo", "estado"),
            sort,
            direction,
            defaults,
        ),
    )


@router.get("/nueva")
def nueva(
    request: Request,
    copiar_de: int | None = Query(None),
    user: User = Depends(REQUIERE_ADMIN),
    db: Session = Depends(get_db),
):
    form_data = {}
    copiada_de = None
    duracion_inicial = "01:00"
    if copiar_de is not None:
        copiada_de = services.actividades.get(db, copiar_de)
        if copiada_de is None:
            return redirect_to(
                request,
                "panel",
                query_params={"err": "Actividad para duplicar no encontrada."},
            )
        form_data = services.actividades.actividad_edit_form_data(copiada_de)
        form_data["fecha_inicio"] = ""
        form_data["fecha_fin"] = ""
        form_data["modo_finalizacion"] = "duracion"
        duracion_inicial = str(form_data["duracion"])

    return render(
        request, "admin/form.html", user=user, db=db,
        a=None, docentes=get_docentes(db), tipos=[TIPO_PRESENCIAL, TIPO_VIRTUAL],
        lista_carreras=services.carreras.get_carreras(db),
        duracion_inicial=duracion_inicial,
        fecha_hoy=date.today().isoformat(),
        form_data=form_data,
        copiada_de=copiada_de,
    )


def _render_edit_form(
    request: Request,
    actividad: Actividad,
    user: User,
    db: Session,
    *,
    error: str | None = None,
    form_data: dict[str, object] | None = None,
) -> _TemplateResponse:
    values = services.actividades.actividad_edit_form_data(actividad)
    values.update(form_data or {})
    return render(
        request, "admin/form.html", user=user, db=db,
        a=actividad, docentes=get_docentes(db), tipos=[TIPO_PRESENCIAL, TIPO_VIRTUAL],
        lista_carreras=services.carreras.get_carreras(db),
        duracion_inicial=values["duracion"],
        fecha_hoy=date.today().isoformat(),
        error=error,
        form_data=values,
    )


@router.post("")
def crear(
    request: Request,
    form: Annotated[ActividadForm, Form()],
    user: User = Depends(REQUIERE_ADMIN),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    try:
        contexto = services.actividades.crear_contexto_actividad(form, db)
    except ValueError as exc:
        db.rollback()
        return redirect_to(request, "nueva", query_params={"err": str(exc)})
    services.actividades.create(
        db,
        contexto,
        created_by=user.id,
    )
    return redirect_to(
        request, "panel",
        query_params={"msg": f"{form.titulo} publicada"},
    )

@router.get("/{actividad_id}/editar", name="editar")
def editar(request: Request, actividad_id: int, user: User = Depends(REQUIERE_ADMIN), db: Session = Depends(get_db)):
    a = services.actividades.get(db, actividad_id)
    if a is None:
        return redirect_to(
            request, "panel",
            query_params={"err": "Actividad no encontrada."},
        )
    return _render_edit_form(request, a, user, db)


@router.post("/{actividad_id}", name="actualizar_actividad")
def actualizar(
    request: Request,
    actividad_id: int,
    form: Annotated[ActividadForm, Form()],
    user: User = Depends(REQUIERE_ADMIN),
    db: Session = Depends(get_db),
) -> Response:
    a = services.actividades.get(db, actividad_id)
    if a is None:
        return redirect_to(
            request, "panel",
            query_params={"err": "Actividad no encontrada."},
        )
    form_data = services.actividades.actividad_form_data(form)
    try:
        contexto = services.actividades.crear_contexto_actividad(
            form, db, actividad=a
        )
    except ValueError as exc:
        db.rollback()
        return _render_edit_form(request, a, user, db, error=str(exc), form_data=form_data)

    was_published = a.estado == ESTADO_PUBLICADA
    fecha_cambio = a.fecha_inicio != contexto.fecha_inicio
    try:
        services.actividades.update(db, a, contexto)
    except ValueError as exc:
        db.rollback()
        return _render_edit_form(
            request, a, user, db, error=str(exc), form_data=form_data
        )
    if not contexto.encuesta_obligatoria:
        estudiantes_pendientes = (
            db.query(Asistencia.user_id)
            .filter(
                Asistencia.actividad_id == actividad_id,
                Asistencia.estado_creditos == ESTADO_CREDITOS_PENDIENTE_ENCUESTA,
            )
            .all()
        )
        for (estudiante_id,) in estudiantes_pendientes:
            services.asistencia.acreditar_creditos_pendientes(
                db, actividad_id, estudiante_id
            )
        if estudiantes_pendientes:
            db.commit()
    if fecha_cambio:
        # Cambió la fecha de inicio: re-armar el recordatorio de 24h de los inscriptos.
        db.query(Inscripcion).filter(
            Inscripcion.actividad_id == actividad_id,
            Inscripcion.estado == INSCRIPCION_ALTA,
        ).update({Inscripcion.reminded: False})
        db.commit()
    if was_published:
        # Best-effort notifications; the actividad update is already committed.
        try:
            for enr in services.inscripcion.inscriptos(db, actividad_id):
                notify(
                    db, enr.user,
                    f"La actividad '{a.titulo}' fue actualizada. Revisá los nuevos datos (fecha {a.fecha_inicio.strftime('%d/%m/%Y %H:%M')}).",
                    email_subject="Cambios en una actividad inscripta",
                )
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
    return redirect_to(
        request, "panel",
        query_params={"msg": "Actividad actualizada."},
    )


@router.get("/{actividad_id}/preview")
def preview(request: Request, actividad_id: int, user: User = Depends(REQUIERE_ADMIN), db: Session = Depends(get_db)):
    a = services.actividades.get(db, actividad_id)
    if a is None:
        return redirect_to(
            request, "panel",
            query_params={"err": "Actividad no encontrada."},
        )
    return render(request, "admin/preview.html", user=user, db=db, a=a, cupo=services.actividades.cupo_info(db, a))


@router.post("/{actividad_id}/publicar")
def publicar(request: Request, actividad_id: int, user: User = Depends(REQUIERE_ADMIN), db: Session = Depends(get_db)):
    a = services.actividades.get(db, actividad_id)
    if a is None:
        return redirect_to(
            request, "panel",
            query_params={"err": "Actividad no encontrada."},
        )
    if a.finalizada:
        return redirect_to(
            request, "editar",
            actividad_id=actividad_id,
            query_params={
                "err": "La actividad ya finalizó, para publicar modificá las fechas de inicio y cierre"
            },
        )
    if not a.carreras_asociadas:
        return redirect_to(
            request, "panel",
            query_params={
                "err": "No se puede publicar una actividad sin carreras asociadas."
            },
        )
    services.actividades.update_estado(db, a, ESTADO_PUBLICADA)
    return redirect_to(
        request, "panel",
        query_params={"msg": "Actividad publicada. Ya es visible para los estudiantes."},
    )


@router.post("/{actividad_id}/cancelar")
def cancelar(request: Request, actividad_id: int, user: User = Depends(REQUIERE_ADMIN), db: Session = Depends(get_db)) -> RedirectResponse:
    a = services.actividades.get(db, actividad_id)
    if a is None:
        return redirect_to(
            request, "panel",
            query_params={"err": "Actividad no encontrada."},
        )
    if not a.finalizada:
        services.actividades.update_estado(db, a, ESTADO_CANCELADA)
        return redirect_to(
            request, "panel",
            query_params={"msg": "Actividad cancelada."},
        )
    else:
        return redirect_to(
            request, "panel",
            query_params={"msg": "No se puede cancelar una actividad terminada"},
        )
@router.get("/{actividad_id}/export.csv")
def export_csv(actividad_id: int, user: User = Depends(REQUIERE_ADMIN), db: Session = Depends(get_db)):
    df = services.inscripcion.inscriptos_dataframe(db, actividad_id)
    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=inscriptos_{actividad_id}.csv"},
    )


@router.get("/{actividad_id}/export.xlsx")
def export_xlsx(actividad_id: int, user: User = Depends(REQUIERE_ADMIN), db: Session = Depends(get_db)):
    df = services.inscripcion.inscriptos_dataframe(db, actividad_id)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Inscriptos")
    return Response(
        content=buf.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=inscriptos_{actividad_id}.xlsx"},
    )