"""Vínculos cadastrais e autorização, sem autenticação/SSO."""
from sqlalchemy import select
from app.models import Usuario, Prefixo, Concessionaria, UsuarioPrefixo, UnidadeConsumidora
from app.services.exceptions import EntityNotFoundError, ContextoOperacionalError


class ContextoOperacionalService:
    def __init__(self, session):
        self.session = session

    def usuario(self, user_id, lock=False):
        query = select(Usuario).where(Usuario.id_usuario == user_id)
        user = self.session.scalar(query.with_for_update() if lock else query)
        if user is None:
            raise EntityNotFoundError("Usuario", user_id)
        return user

    def ativos(self, user_id):
        return list(self.session.scalars(select(Prefixo).join(UsuarioPrefixo).where(
            UsuarioPrefixo.id_usuario == user_id, UsuarioPrefixo.ativo.is_(True),
            Prefixo.situacao == "ativo").order_by(Prefixo.id_prefixo)))

    def resolver(self, user_id, prefix_id=None):
        user = self.usuario(user_id)
        if user.situacao != "ativo":
            raise ContextoOperacionalError("Usuário não está ativo")
        prefixes = self.ativos(user_id)
        if not prefixes:
            raise ContextoOperacionalError("Usuário operacional precisa de ao menos um prefixo ativo")
        if prefix_id is None:
            if len(prefixes) != 1:
                raise ContextoOperacionalError("Selecione um dos prefixos autorizados")
            return prefixes[0]
        for prefix in prefixes:
            if prefix.id_prefixo == prefix_id:
                return prefix
        raise ContextoOperacionalError("Prefixo não autorizado para o usuário")

    def definir(self, user_id, entries, commit=True):
        try:
            user = self.usuario(user_id, lock=True)
            ids = [e.id_prefixo for e in entries]
            if len(set(ids)) != len(ids):
                raise ContextoOperacionalError("Vínculos duplicados")
            if sum(e.principal for e in entries) > 1 or any(e.principal and not e.ativo for e in entries):
                raise ContextoOperacionalError("Somente um prefixo ativo pode ser principal")
            active = []
            for entry in entries:
                prefix = self.session.get(Prefixo, entry.id_prefixo)
                if prefix is None:
                    raise EntityNotFoundError("Prefixo", entry.id_prefixo)
                if entry.ativo:
                    if prefix.situacao != "ativo":
                        raise ContextoOperacionalError("Vínculo ativo exige prefixo ativo")
                    active.append(prefix)
            if not active:
                raise ContextoOperacionalError("Usuário operacional precisa de ao menos um prefixo ativo")
            old = list(self.session.scalars(select(UsuarioPrefixo).where(UsuarioPrefixo.id_usuario == user_id)))
            # Libera o índice parcial antes da troca do principal.
            for link in old:
                link.principal = False
            self.session.flush()
            existing = {link.id_prefixo: link for link in old}
            for link in old:
                if link.id_prefixo not in ids:
                    link.ativo = False
            for entry in entries:
                link = existing.get(entry.id_prefixo)
                if link is None:
                    link = UsuarioPrefixo(id_usuario=user_id, id_prefixo=entry.id_prefixo)
                    self.session.add(link)
                link.ativo, link.principal = entry.ativo, entry.principal
            principal = next((e.id_prefixo for e in entries if e.principal), None)
            user.id_prefixo = principal or active[0].id_prefixo
            self.session.flush()
            from app.services.validacao_documental import revalidar_contextos
            revalidar_contextos(self.session)
            if commit:
                self.session.commit()
            return entries
        except Exception:
            if commit:
                self.session.rollback()
            raise

    def cadastrar_unidade(self, data):
        try:
            for model, key in ((Prefixo, data.id_prefixo), (Concessionaria, data.id_concessionaria)):
                if self.session.get(model, key) is None:
                    raise EntityNotFoundError(model.__name__, key)
            if self.session.scalar(select(UnidadeConsumidora).where(
                UnidadeConsumidora.id_concessionaria == data.id_concessionaria,
                UnidadeConsumidora.unidade_consumidora == data.unidade_consumidora)):
                raise ContextoOperacionalError("Unidade já cadastrada para essa concessionária")
            unit = UnidadeConsumidora(**data.model_dump())
            self.session.add(unit)
            self.session.flush()
            from app.services.validacao_documental import revalidar_contextos
            revalidar_contextos(self.session)
            self.session.commit()
            return unit
        except Exception:
            self.session.rollback()
            raise

    def atualizar_unidade(self, unit_id, data):
        try:
            unit = self.session.scalar(select(UnidadeConsumidora).where(
                UnidadeConsumidora.id_unidade_consumidora == unit_id).with_for_update())
            if unit is None:
                raise EntityNotFoundError("UnidadeConsumidora", unit_id)
            values = data.model_dump(exclude_unset=True)
            if "ativo" in values and values["ativo"] is None:
                raise ContextoOperacionalError("Ativo não pode ser nulo")
            for name, value in values.items():
                setattr(unit, name, value)
            self.session.flush()
            from app.services.validacao_documental import revalidar_contextos
            revalidar_contextos(self.session)
            self.session.commit()
            return unit
        except Exception:
            self.session.rollback()
            raise
