import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from codeqa.models.base import Base


class IndexJob(Base):
    __tablename__ = "index_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String, default="pending")
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]
    files_processed: Mapped[int] = mapped_column(default=0)
    chunks_created: Mapped[int] = mapped_column(default=0)
    error: Mapped[str | None] = mapped_column(String)
