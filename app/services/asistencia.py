"""Asistencia service: registro de asistencia y acreditación de créditos."""
from __future__ import annotations

import base64
import io
import json
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

import qrcode
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    Actividad,
    Asistencia,
    Inscripcion,
    Estudiante,
    User,
    VentanaAsistencia,
    ESTADO_CREDITOS_ACREDITADO,
    ESTADO_CREDITOS_PENDIENTE_ENCUESTA,
    ESTADO_PUBLICADA,
    INSCRIPCION_ALTA,
    ROL_COORDINACION,
    ROL_ESTUDIANTE,
)
from app.services.encuestas import estudiante_completo_encuesta
from app.services.consultas_comunes import is_enrolled
from app.config import settings
from app.services.mailing import send_email

class AsistenciaError(Exception):
    pass


def qr_data_uri(text: str) -> str:
    qr_image = qrcode.make(text)
    buffer = io.BytesIO()
    qr_image.save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def puede_gestionar_actividad(actividad: Actividad, user: User) -> bool:
    return user.rol == ROL_COORDINACION or (
        user.docente_id is not None
        and any(docente.id == user.docente_id for docente in actividad.docentes)
    )
        
    
def _acreditar_creditos(
    db: Session, actividad_id: int, user_id: int, cantidad: float
) -> bool:
    '''Comprueba si el estudiante ya tiene acreditados los créditos de la 
    actividad y, si no, si ha completado la encuesta los acredita.
    '''
    asistencia = (
        db.query(Asistencia)
        .filter(
            Asistencia.actividad_id == actividad_id,
            Asistencia.user_id == user_id,
        )
        .one_or_none()
    )
    if asistencia is None:
        raise AsistenciaError("No se encontró la asistencia para acreditar.")
    
    # validar estado y early return si ya están acreditados
    if asistencia.estado_creditos == ESTADO_CREDITOS_ACREDITADO:
        return True
    
    if asistencia.estado_creditos != ESTADO_CREDITOS_PENDIENTE_ENCUESTA:
        raise AsistenciaError("La asistencia tiene un estado de créditos inválido.")

    # verificar completitud de la encuesta
    if not estudiante_completo_encuesta(db, user_id, actividad_id):
        return False
    
    # intentar actualizar el estado de la asistencia (con control de concurrencia)
    marked = db.execute(
        update(Asistencia)
        .where(
            Asistencia.actividad_id == actividad_id,
            Asistencia.user_id == user_id,
            Asistencia.estado_creditos == ESTADO_CREDITOS_PENDIENTE_ENCUESTA,
        )
        .values(estado_creditos=ESTADO_CREDITOS_ACREDITADO)
    )
    
    # si hubo un conflicto de concurrencia, re-verificar estado actual
    if marked.rowcount != 1:
        asistencia = (
            db.query(Asistencia)
            .filter(
                Asistencia.actividad_id == actividad_id,
                Asistencia.user_id == user_id,
            )
            .one_or_none()
        )
        if asistencia is None:
            raise AsistenciaError("No se encontró la asistencia para acreditar.")
        return asistencia.estado_creditos == ESTADO_CREDITOS_ACREDITADO
    
    # actualizar créditos del estudiante de forma segura
    result = db.execute(
        update(Estudiante)
        .where(Estudiante.user_id == user_id)
        .values(creditos_acreditados=Estudiante.creditos_acreditados + float(cantidad))
    )
    if result.rowcount != 1:
        raise AsistenciaError("No se pudo actualizar el registro de créditos del estudiante.")
        
    return True


def creditos_pendientes_encuesta(db: Session, actividad_id: int, user_id: int) -> bool:
    return (
        db.query(Asistencia.id)
        .filter(
            Asistencia.actividad_id == actividad_id,
            Asistencia.user_id == user_id,
            Asistencia.estado_creditos == ESTADO_CREDITOS_PENDIENTE_ENCUESTA,
        )
        .first()
        is not None
    )


def acreditar_creditos_pendientes(
    db: Session, actividad_id: int, user_id: int
) -> float:
    '''Acredita los créditos pendientes de encuesta para un estudiante en una actividad.
    Devuelve la cantidad de créditos acreditados (0.0 si no se acreditó nada).
    '''
    actividad = db.get(Actividad, actividad_id)
    if actividad is None:
        return 0.0
    pendientes = (
        db.query(Asistencia)
        .filter(
            Asistencia.actividad_id == actividad_id,
            Asistencia.user_id == user_id,
            Asistencia.estado_creditos == ESTADO_CREDITOS_PENDIENTE_ENCUESTA,
        )
        .all()
    )
    acreditados = 0.0
    for _ in pendientes:
        cantidad = float(actividad.creditos)
        if _acreditar_creditos(db, actividad_id, user_id, cantidad):
            acreditados += cantidad
    return acreditados


def _now() -> datetime:
    return datetime.now(timezone.utc)


def asegurar_ventana_asistencia(
    db: Session, actividad_id: int
) -> VentanaAsistencia:
    '''Asegura que exista una ventana de asistencia para la actividad, creándola si no existe.
    Devuelve la ventana existente o recién creada.
    '''
    ventana_asistencia = (
        db.query(VentanaAsistencia)
        .filter(VentanaAsistencia.actividad_id == actividad_id)
        .one_or_none()
    )
    if ventana_asistencia is not None:
        return ventana_asistencia
    ventana_asistencia = VentanaAsistencia(
        actividad_id=actividad_id,
        codigo=_codigo_asistencia_unico(db),
        codigo_cierre=secrets.token_urlsafe(48),
    )
    db.add(ventana_asistencia)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        ventana_asistencia = (
            db.query(VentanaAsistencia)
            .filter(VentanaAsistencia.actividad_id == actividad_id)
            .one_or_none()
        )
        if ventana_asistencia is None:
            raise
    db.refresh(ventana_asistencia)
    return ventana_asistencia


def _codigo_asistencia_unico(db: Session) -> str:
    for _ in range(100):
        code = f"{secrets.randbelow(1_000_000):06d}"
        if not db.query(VentanaAsistencia).filter(
            VentanaAsistencia.codigo == code
        ).first():
            return code
    raise RuntimeError("No se pudo generar un código de asistencia único.")


def cerrar_ventana_asistencia(
    db: Session,
    close_code: str,
    *,
    now: datetime | None = None,
) -> bool:
    '''Cierra manualmente la ventana de asistencia asociada al código de cierre.'''
    ventana_asistencia = (
        db.query(VentanaAsistencia)
        .filter(VentanaAsistencia.codigo_cierre == close_code)
        .one_or_none()
    )
    if ventana_asistencia is None or ventana_asistencia.cerrada_manualmente:
        return False
    actividad = db.get(Actividad, ventana_asistencia.actividad_id)
    if actividad is None or not puede_cerrar_ventana_asistencia(actividad, now=now):
        return False
    ventana_asistencia.cerrada_manualmente = True
    db.commit()
    return True


def puede_cerrar_ventana_asistencia(
    actividad: Actividad, *, now: datetime | None = None
) -> bool:
    '''Indica si la ventana de asistencia puede cerrarse manualmente (E-09).'''
    inicio = actividad.fecha_inicio
    if inicio.tzinfo is None:
        inicio = inicio.replace(tzinfo=timezone.utc)
    current = now or _now()
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    else:
        current = current.astimezone(timezone.utc)
    return current >= inicio


def ventana_asistencia_abierta(
    actividad: Actividad,
    ventana_asistencia: VentanaAsistencia,
    *,
    now: datetime | None = None,
) -> bool:
    '''Indica si la ventana de asistencia está abierta para registrar asistencia (E-09).'''
    if ventana_asistencia.cerrada_manualmente:
        return False
    start = actividad.fecha_inicio
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    current = now or _now()
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    else:
        current = current.astimezone(timezone.utc)
    return actividad.estado == ESTADO_PUBLICADA and (
        start - timedelta(minutes=30) <= current < start + timedelta(hours=6)
    )



def _normalizar_utc(dt: datetime) -> datetime:
    """Asegura que la fecha tenga zona horaria UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _obtener_actividades_candidatas(db: Session, current_time: datetime) -> list:
    """Obtiene las actividades publicadas y no finalizadas."""
    stmt = (
        select(Actividad)
        .where(Actividad.estado == ESTADO_PUBLICADA)
        .where(Actividad.fecha_fin > current_time)
    )
    return db.scalars(stmt).all()


def _esta_en_ventana_cierre(actividad:Actividad, current_time: datetime) -> bool:
    """Verifica si la actividad inició hace menos de 24 horas o está por iniciar."""
    start = _normalizar_utc(actividad.fecha_inicio)
    return start <= current_time + timedelta(hours=24)


def _generar_adjunto_qr(actividad_id: int, codigo: str) -> tuple:
    """Genera la imagen QR y prepara el archivo adjunto para el correo."""
    qr_buffer = io.BytesIO()
    qr_image = qrcode.make(codigo)
    qr_image.save(qr_buffer, format="PNG")
    
    # Debug/Testing 
    # TODO esto no va en produ
    qr_dir = Path("./data/qr")
    qr_dir.mkdir(parents=True, exist_ok=True)
    qr_image.save(qr_dir / f"asistencia-{actividad_id}.png", format="PNG")
    
    return (
        f"asistencia-{actividad_id}.png",
        qr_buffer.getvalue(),
        "image/png",
    )


def _construir_cuerpo_correo(db: Session, actividad:Actividad, ventana_asistencia:VentanaAsistencia) -> str:
    """Construye el cuerpo del mensaje en formato Markdown con el roster de inscriptos."""
    inscriptos = (
        db.query(Inscripcion)
        .filter(
            Inscripcion.actividad_id == actividad.id,
            Inscripcion.estado == INSCRIPCION_ALTA,
        )
        .all()
    )
    
    roster = []
    for inscripto in inscriptos:
        estudiante = inscripto.user
        carrera = estudiante.carrera
        carrera_name = (
            f"{carrera.tipo.nombre} {carrera.nombre}" if carrera else "Sin carrera"
        )
        roster.append(
            f"| {estudiante.nombre} | {estudiante.apellido} | {estudiante.email} | {carrera_name} |"
        )

    close_url = f"{settings.PUBLIC_BASE_URL}/docente/asistencia/cerrar/{ventana_asistencia.codigo_cierre}"
    
    tabla_inscriptos = (
        "| Nombre | Apellido | Mail | Carrera |\n"
        "| --- | --- | --- | --- |\n"
        + "\n".join(roster)
        if roster
        else "- No hay inscriptos."
    )

    return (
        f"Inscripción cerrada para '{actividad.titulo}'.\n\n"
        f"Inicio: {actividad.fecha_inicio.strftime('%d/%m/%Y %H:%M')}\n"
        f"Código de validación: {ventana_asistencia.codigo}\n"
        f"Ventana de asistencia: desde 30 minutos antes del inicio hasta 6 horas después del inicio.\n"
        f"Cierre manual: {close_url}\n\n"
        f"Inscriptos:\n{tabla_inscriptos}"
    )


def _enviar_correos_docentes(
    db: Session,
    ventana_asistencia,
    docentes: dict,
    notified_emails: set,
    titulo_actividad: str,
    body: str,
    attachment: tuple
) -> int:
    """Itera sobre los docentes y envía los correos pendientes, actualizando la base de datos."""
    delivered = 0
    for email in docentes:
        if email in notified_emails:
            continue
        if send_email(
            email,
            f"Inscripción cerrada: {titulo_actividad}",
            body,
            attachments=[attachment],
        ):
            notified_emails.add(email)
            ventana_asistencia.correos_enviados = json.dumps(sorted(notified_emails))
            db.commit()
            delivered += 1
    return delivered

def procesar_mails_actividades_cerradas(
    db: Session, *, now: datetime | None = None
) -> int:
    """Envía correos a los docentes de actividades cuya inscripción se cerró en las últimas 24h,

    con el listado de inscriptos y el código de asistencia. Devuelve la cantidad de correos enviados.
    """
    current_time = _normalizar_utc(now or _now())
    actividades = _obtener_actividades_candidatas(db, current_time)
    
    delivered = 0
    for actividad in actividades:
        if not _esta_en_ventana_cierre(actividad, current_time):
            continue
            
        ventana_asistencia = asegurar_ventana_asistencia(db, actividad.id)
        notified_emails = set(json.loads(ventana_asistencia.correos_enviados))
        
        docentes = {d.email: d.nombre_completo for d in actividad.docentes}
        if not docentes or set(docentes).issubset(notified_emails):
            continue
            
        attachment = _generar_adjunto_qr(actividad.id, ventana_asistencia.codigo)
        body = _construir_cuerpo_correo(db, actividad, ventana_asistencia)
        
        delivered += _enviar_correos_docentes(
            db=db,
            ventana_asistencia=ventana_asistencia,
            docentes=docentes,
            notified_emails=notified_emails,
            titulo_actividad=actividad.titulo,
            body=body,
            attachment=attachment
        )
        
    return delivered

def check_in(db: Session, token: str, user_id: int) -> Actividad:
    """Validate a scanned token and mark the estudiante present. Raises AsistenciaError."""
    token = token.strip()
    ventana_asistencia = (
        db.query(VentanaAsistencia)
        .filter(VentanaAsistencia.codigo == token)
        .one_or_none()
    )
    if ventana_asistencia is None:
        raise AsistenciaError("Código inválido.")
    actividad = db.get(Actividad, ventana_asistencia.actividad_id)
    if actividad is None or not ventana_asistencia_abierta(actividad, ventana_asistencia):
        raise AsistenciaError("La actividad no está abierta para registrar asistencia.")
    if not is_enrolled(db, ventana_asistencia.actividad_id, user_id):
        raise AsistenciaError("No estás inscripto en esta actividad.")

    already = (
        db.query(Asistencia)
        .filter(
            Asistencia.actividad_id == ventana_asistencia.actividad_id,
            Asistencia.user_id == user_id,
        )
        .first()
    )
    if already:
        raise AsistenciaError("Tu asistencia ya fue registrada.")

    db.add(
        Asistencia(
            actividad_id=ventana_asistencia.actividad_id,
            user_id=user_id,
            validated_by=None,
            estado_creditos=ESTADO_CREDITOS_PENDIENTE_ENCUESTA,
        )
    )
    try:
        db.flush()
        _acreditar_creditos(db, ventana_asistencia.actividad_id, user_id, actividad.creditos)
        db.commit()
    except IntegrityError:
        # Concurrent double-scan: the unique constraint already recorded it.
        db.rollback()
        raise AsistenciaError("Tu asistencia ya fue registrada.")
    return actividad


def present_user_ids(db: Session, actividad_id: int) -> set[int]:
    rows = db.query(Asistencia.user_id).filter(Asistencia.actividad_id == actividad_id).all()
    return {r[0] for r in rows}

def mark_present_manual(
    db: Session, actividad_id: int, user_id: int, validated_by: int
) -> bool:
    """Admin/docente manual override (E-09 supervision).

    Mirrors the guards in check_in(): the target must be a real estudiante enrolled
    in the actividad, so asistencia/credits cannot be fabricated for arbitrary ids.
    """
    target = db.get(User, user_id)
    if target is None or target.rol != ROL_ESTUDIANTE:
        raise AsistenciaError("El usuario indicado no es un estudiante válido.")
    actividad = db.get(Actividad, actividad_id)
    if actividad is None:
        raise AsistenciaError("No se pudo actualizar el registro de créditos del estudiante.")
    if not is_enrolled(db, actividad_id, user_id):
        raise AsistenciaError("El estudiante no está inscripto en esta actividad.")
    existing = (
        db.query(Asistencia)
        .filter(Asistencia.actividad_id == actividad_id, Asistencia.user_id == user_id)
        .first()
    )
    if existing:
        credited = _acreditar_creditos(
            db, actividad_id, user_id, actividad.creditos
        )
        db.commit()
        return credited
    attendance = Asistencia(
        actividad_id=actividad_id,
        user_id=user_id,
        validated_by=validated_by,
        estado_creditos=ESTADO_CREDITOS_PENDIENTE_ENCUESTA,
    )
    db.add(attendance)
    try:
        db.flush()
        credited = _acreditar_creditos(db, actividad_id, user_id, actividad.creditos)
        db.commit()
        return credited
    except IntegrityError:
        db.rollback()
        return False


def revoke_present(db: Session, actividad_id: int, user_id: int) -> bool:
    """Remove a estudiante's attendance and reverse credits already awarded for it."""
    attendance = (
        db.query(Asistencia)
        .filter(
            Asistencia.actividad_id == actividad_id,
            Asistencia.user_id == user_id,
        )
        .one_or_none()
    )
    if attendance is None:
        return False
    if attendance.estado_creditos == ESTADO_CREDITOS_ACREDITADO:
        actividad = db.get(Actividad, actividad_id)
        estudiante = db.get(Estudiante, user_id)
        if actividad is None or estudiante is None:
            raise AsistenciaError("No se pudieron revertir los créditos de la asistencia.")
        estudiante.creditos_acreditados -= float(actividad.creditos)
        if estudiante.creditos_acreditados < 0:
            raise AsistenciaError("No se pudieron revertir los créditos de la asistencia.")
    db.delete(attendance)
    db.commit()
    return True
