"""Seed the coordinator account and careers required by the application."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Carrera, ROL_COORDINACION, TipoCarrera, User
from app.models.persona import Persona
from app.security import hash_password, verify_password


COORDINATOR_EMAIL = "coordinacion@unsam.edu.ar"
COORDINATOR_NAME = ("Laura", "Rasia")

CARRERAS = [
    ("Ambiental", "Ingeniería", 20),
    ("Biomédica", "Ingeniería", 20),
    ("Electrónica", "Ingeniería", 20),
    ("Energía", "Ingeniería", 20),
    ("Industrial", "Ingeniería", 20),
    ("Sistemas Espaciales", "Ingeniería", 20),
    ("Telecomunicaciones", "Ingeniería", 20),
    ("Transporte", "Ingeniería", 20),
    ("Desarrollo de Software", "Licenciatura", 10),
    ("Biotecnología", "Licenciatura", 10),
    ("Ciencia de Datos", "Licenciatura", 10),
    ("Física Médica", "Licenciatura", 10),
]


def _get_or_create_coordinator(db: Session, password: str) -> User:
    persona = db.scalar(select(Persona).where(Persona.email == COORDINATOR_EMAIL))
    if persona is None:
        persona = Persona(
            email=COORDINATOR_EMAIL,
            nombre=COORDINATOR_NAME[0],
            apellido=COORDINATOR_NAME[1],
        )
        db.add(persona)
        db.flush()

    user = persona.usuario
    if user is None:
        user = User(
            persona=persona,
            pw_hash=hash_password(password),
            rol=ROL_COORDINACION,
        )
        db.add(user)
    elif user.rol != ROL_COORDINACION:
        raise ValueError(
            f"El usuario {COORDINATOR_EMAIL} ya existe con un rol distinto de coordinación."
        )
    elif not verify_password(password, user.pw_hash):
        user.pw_hash = hash_password(password)

    return user


def _seed_carreras(db: Session) -> None:
    tipos_por_nombre: dict[str, TipoCarrera] = {}
    for tipo_nombre in dict.fromkeys(tipo for _, tipo, _ in CARRERAS):
        tipo = db.scalar(select(TipoCarrera).where(TipoCarrera.nombre == tipo_nombre))
        if tipo is None:
            tipo = TipoCarrera(nombre=tipo_nombre)
            db.add(tipo)
            db.flush()
        tipos_por_nombre[tipo_nombre] = tipo

    for nombre, tipo_nombre, creditos_requeridos in CARRERAS:
        carrera_id = db.scalar(select(Carrera.id).where(Carrera.nombre == nombre))
        if carrera_id is None:
            db.add(
                Carrera(
                    nombre=nombre,
                    tipo_id=tipos_por_nombre[tipo_nombre].id,
                    creditos_requeridos=creditos_requeridos,
                )
            )


def seed_all(db: Session) -> None:
    password = settings.DEMO_PASSWORD.strip()
    if not password:
        raise RuntimeError("DEMO_PASSWORD debe estar configurada para ejecutar el seeding.")

    _get_or_create_coordinator(db, password)
    _seed_carreras(db)
    db.commit()
