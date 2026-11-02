"""Executa migrations reais em banco temporário, incluindo backfill legado."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from alembic.config import Config
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from app.core.config import settings


class MigrationDocumentalTests(unittest.TestCase):
    def test_upgrade_preserva_dados_e_migra_vinculo_legado(self):
        with TemporaryDirectory() as directory:
            db_url='sqlite:///'+str(Path(directory)/'migration.db')
            config=Config('alembic.ini')
            with patch.object(settings,'database_url',db_url):
                command.upgrade(config,'e172d1b499a0')
                engine=create_engine(db_url)
                self.addCleanup(engine.dispose)
                with engine.begin() as connection:
                    connection.execute(text("INSERT INTO localidades (id_localidade,codigo_localidade,estado,municipio) VALUES (1,'L','PE','Recife')"))
                    connection.execute(text("INSERT INTO prefixos (id_prefixo,codigo_prefixo,nome,tipo_prefixo,situacao,id_localidade) VALUES (1,'P','P','agencia','ativo',1),(2,'Q','Q','agencia','ativo',1)"))
                    connection.execute(text("INSERT INTO usuarios (id_usuario,matricula,nome,funcao,situacao,id_prefixo) VALUES (1,'M','N','operador','ativo',1)"))
                command.upgrade(config,'head')
                command.upgrade(config,'head')
                with engine.connect() as connection:
                    self.assertEqual(connection.scalar(text('SELECT version_num FROM alembic_version')),ScriptDirectory.from_config(config).get_current_head())
                    self.assertEqual(connection.execute(text('SELECT id_usuario,id_prefixo,ativo,principal FROM usuarios_prefixos')).one(),(1,1,True,True))
                    self.assertEqual(connection.scalar(text('SELECT matricula FROM usuarios WHERE id_usuario=1')),'M')
                with self.assertRaises(IntegrityError),engine.begin() as connection:
                    connection.execute(text('INSERT INTO usuarios_prefixos (id_usuario,id_prefixo,ativo,principal) VALUES (1,2,true,true)'))


    def test_alias_upgrade_downgrade_preserva_cadastro(self):
        with TemporaryDirectory() as directory:
            url = 'sqlite:///' + str(Path(directory)/'alias.db')
            config = Config('alembic.ini')
            with patch.object(settings, 'database_url', url):
                command.upgrade(config, 'e61d4b902f30')
                engine = create_engine(url)
                self.addCleanup(engine.dispose)
                with engine.begin() as connection:
                    connection.execute(text("INSERT INTO concessionarias (id_concessionaria,cnpj,razao_social,tipo_servico) VALUES (1,'123','Cadastro preservado','energia')"))
                command.upgrade(config, 'head')
                with engine.begin() as connection:
                    self.assertTrue(connection.scalar(text('SELECT ativo FROM concessionarias WHERE id_concessionaria=1')))
                    connection.execute(text("INSERT INTO concessionaria_aliases (id_concessionaria,alias,alias_normalizado,ativo,criado_em) VALUES (1,'Histórico','HISTORICO',true,CURRENT_TIMESTAMP)"))
                with self.assertRaises(IntegrityError), engine.begin() as connection:
                    connection.execute(text("INSERT INTO concessionaria_aliases (id_concessionaria,alias,alias_normalizado,ativo,criado_em) VALUES (1,'Histórico','HISTORICO',true,CURRENT_TIMESTAMP)"))
                command.downgrade(config, 'e61d4b902f30')
                with engine.connect() as connection:
                    self.assertEqual(connection.scalar(text('SELECT razao_social FROM concessionarias')), 'Cadastro preservado')
                command.upgrade(config, 'head')
