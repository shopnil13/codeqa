import uuid
from datetime import datetime

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from codeqa.models.base import Base


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    source_url: Mapped[str] = mapped_column(String, nullable=False)
    local_path: Mapped[str] = mapped_column(String)
    commit_sha: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="pending")
    last_indexed_at: Mapped[datetime | None]


    