
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Numeric, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    # PostgreSQL NUMERIC does not shorten itself: 18450 + -650.00 stays
    # 17800.00 with two decimals. With no type here SQLAlchemy infers one from
    # the operands, and on SQLite (used in tests) that falls back to float.
    type_annotation_map = {Decimal: Numeric(18, 2)}


class TimestampMixin:
    """Adds created/updated timestamps to a model."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )