"""SQLAlchemy 2.0 + SQLite : utilisateurs, résultats, complétions, métacognition."""
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "futura.db"
engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False)


def now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(40), unique=True)
    xp: Mapped[int] = mapped_column(Integer, default=0)
    pin_hash: Mapped[str | None] = mapped_column(String(200), nullable=True)


class ExerciseResult(Base):
    __tablename__ = "exercise_results"
    __table_args__ = (UniqueConstraint("user_id", "parcours_id", "exercise_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    parcours_id: Mapped[str] = mapped_column(String(80))
    exercise_id: Mapped[str] = mapped_column(String(20))
    correct: Mapped[bool] = mapped_column(default=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0)


class Completion(Base):
    __tablename__ = "completions"
    __table_args__ = (UniqueConstraint("user_id", "parcours_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    parcours_id: Mapped[str] = mapped_column(String(80))
    xp: Mapped[int] = mapped_column(Integer)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Reflection(Base):
    __tablename__ = "reflections"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    parcours_id: Mapped[str] = mapped_column(String(80))
    confidence: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str] = mapped_column(Text, default="")
    prediction_result: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Prediction(Base):
    __tablename__ = "predictions"
    __table_args__ = (UniqueConstraint("user_id", "parcours_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    parcours_id: Mapped[str] = mapped_column(String(80))
    text: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


def init_db() -> None:
    from .content import USERS
    Base.metadata.create_all(engine)
    with engine.begin() as c:  # migration légère pour les bases créées avant l'ajout du PIN
        if "pin_hash" not in [r[1] for r in c.exec_driver_sql("PRAGMA table_info(users)")]:
            c.exec_driver_sql("ALTER TABLE users ADD COLUMN pin_hash VARCHAR(200)")
        if "prediction_result" not in [r[1] for r in c.exec_driver_sql("PRAGMA table_info(reflections)")]:
            c.exec_driver_sql("ALTER TABLE reflections ADD COLUMN prediction_result VARCHAR(10)")
    with SessionLocal() as db:
        for name in USERS:
            if not db.scalar(select(User).where(User.name == name)):
                db.add(User(name=name))
        db.commit()


def get_db():
    with SessionLocal() as db:
        yield db
