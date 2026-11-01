from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.usuario import Usuario
    from app.models.prefixo import Prefixo
from app.models.base import Base


class UsuarioPrefixo(Base):
    __tablename__ = "usuarios_prefixos"
    __table_args__ = (
        CheckConstraint("NOT principal OR ativo", name="ck_usuario_prefixo_principal_ativo"),
        Index("uq_usuario_prefixo_principal", "id_usuario", unique=True,
              sqlite_where=text("principal = true AND ativo = true"),
              postgresql_where=text("principal = true AND ativo = true")),
    )
    id_usuario: Mapped[int] = mapped_column(ForeignKey("usuarios.id_usuario"), primary_key=True)
    id_prefixo: Mapped[int] = mapped_column(ForeignKey("prefixos.id_prefixo"), primary_key=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    principal: Mapped[bool] = mapped_column(Boolean, default=False)

    usuario: Mapped["Usuario"] = relationship(back_populates="vinculos_prefixos")
    prefixo: Mapped["Prefixo"] = relationship()
