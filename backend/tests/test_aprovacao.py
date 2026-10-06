"""Regras humanas, atomicidade e HTTP usando SQLite em memória."""
import unittest
from decimal import Decimal
from unittest.mock import patch

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app import models, schemas, services
from app.services.exceptions import (
    ApprovalOrderChangeNotAllowedError,
    InsufficientApprovalLimitError, SelfApprovalNotAllowedError,
)
from tests.test_api import ApiTestCase, ENTITIES


class ApprovalTests(ApiTestCase):
    def setUp(self):
        super().setUp()
        # Pais reais criados pelo CRUD; aprovador é um segundo Usuario.
        for resource, _, payload, _ in ENTITIES[:-1]:
            response = self.client.post('/api/v1/' + resource, json=payload)
            self.assertEqual(response.status_code, 201, response.text)
        self.ensure_checker('aprovacoes')
        self.session = Session(self.engine, autoflush=False)
        self.addCleanup(self.session.close)
        self.service = services.AprovacaoService(self.session)
        self.payload = {**ENTITIES[-1][2], 'decisao': 'aprovado'}

    def create(self, **changes):
        return self.service.create(schemas.AprovacaoCreate(**{**self.payload, **changes}))

    def limit(self, value):
        self.session.get(models.Alcada, 1).limite_financeiro = Decimal(value)
        self.session.commit()

    def no_limit(self):
        self.session.get(models.Usuario, 2).id_alcada = None
        self.session.commit()

    def assert_order(self, status):
        with Session(self.engine) as reader:
            self.assertEqual(reader.get(models.OrdemPagamento, 1).situacao, status)

    def test_sufficient_limit_approves_and_updates_order(self):
        with patch.object(self.session, 'commit', wraps=self.session.commit) as commit:
            approval = self.create(decisao=' APROVADO ')
            commit.assert_called_once_with()
        self.assertEqual(approval.id_usuario, 2)
        self.assert_order('aprovada')

    def test_self_approval_and_rejection_denied(self):
        for decision in ('aprovado', 'rejeitado', 'APROVADO'):
            with self.subTest(decision=decision), self.assertRaises(SelfApprovalNotAllowedError):
                self.create(id_usuario=1, decisao=decision)
        self.assertEqual(self.service.list(), [])
        self.assert_order('pendente')

    def test_no_limit_denied(self):
        self.no_limit()
        with self.assertRaises(InsufficientApprovalLimitError):
            self.create()
        self.assertEqual(self.service.list(), [])

    def test_lower_limit_denied(self):
        self.limit('117.27')
        with self.assertRaises(InsufficientApprovalLimitError):
            self.create()
        self.assert_order('pendente')

    def test_equal_limit_allowed(self):
        self.limit('117.28')
        self.create()
        self.assert_order('aprovada')

    def test_rejection_without_sufficient_limit(self):
        self.limit('0')
        self.create(decisao='REJEITADO')
        self.assert_order('rejeitada')

    def test_rejection_without_limit(self):
        self.no_limit()
        self.create(decisao='rejeitado')
        self.assert_order('rejeitada')

    def test_commit_failure_rolls_back_both_and_session_recovers(self):
        with patch.object(self.session, 'commit', side_effect=RuntimeError('falha')), patch.object(self.session, 'rollback', wraps=self.session.rollback) as rollback:
            with self.assertRaises(RuntimeError):
                self.create()
            rollback.assert_called_once_with()
        self.assertEqual(self.service.list(), [])
        self.assert_order('pendente')
        self.create()
        self.assert_order('aprovada')

    def test_order_write_failure_rolls_back_approval(self):
        with patch('app.services.aprovacao.OrdemPagamentoRepository.update', side_effect=RuntimeError('falha')):
            with self.assertRaises(RuntimeError):
                self.create()
        self.assertEqual(self.service.list(), [])
        self.assert_order('pendente')
        self.create()

    def test_patch_revalidates_creator_and_limit(self):
        self.create(decisao='rejeitado')
        with self.assertRaises(SelfApprovalNotAllowedError):
            self.service.update(1, schemas.AprovacaoUpdate(id_usuario=1))
        self.no_limit()
        with self.assertRaises(InsufficientApprovalLimitError):
            self.service.update(1, schemas.AprovacaoUpdate(decisao='APROVADO'))
        self.assertEqual(self.service.get_by_id(1).decisao, 'rejeitado')
        self.assert_order('rejeitada')

    def test_patch_valid_decision_updates_order(self):
        self.create(decisao='rejeitado')
        self.service.update(1, schemas.AprovacaoUpdate(decisao='aprovado'))
        self.assert_order('aprovada')

    def test_patch_order_link_immutable(self):
        self.create()
        payload = ENTITIES[13][2]
        order = services.OrdemPagamentoService(self.session).create(schemas.OrdemPagamentoCreate(**payload))
        with self.assertRaises(ApprovalOrderChangeNotAllowedError):
            self.service.update(1, schemas.AprovacaoUpdate(id_ordem=order.id_ordem))
        self.assertEqual(self.service.get_by_id(1).id_ordem, 1)
        self.assertEqual(order.situacao, 'pendente')

    def test_patch_integrity_failure_recovers(self):
        self.create()
        with self.assertRaises(IntegrityError):
            self.service.update(1, schemas.AprovacaoUpdate(decisao='rejeitado', data_hora=None))
        self.assert_order('aprovada')
        self.assertEqual(self.service.get_by_id(1).decisao, 'aprovado')
        self.service.update(1, schemas.AprovacaoUpdate(decisao='rejeitado'))
        self.assert_order('rejeitada')

    def test_http_self_approval_409(self):
        response = self.client.post('/api/v1/aprovacoes', json={**self.payload, 'id_usuario': 1})
        self.assertEqual(response.status_code, 409, response.text)

    def test_http_limit_403(self):
        for limit in ('none', '0'):
            self.no_limit() if limit == 'none' else self.limit(limit)
            response = self.client.post('/api/v1/aprovacoes', json=self.payload)
            self.assertEqual(response.status_code, 403, response.text)

    def test_http_missing_order_user_limit_404(self):
        for field in ('id_ordem', 'id_usuario'):
            response = self.client.post('/api/v1/aprovacoes', json={**self.payload, field: 999})
            self.assertEqual(response.status_code, 404, response.text)
        # Simula referência legada inválida sem desabilitar FKs do SQLite.
        with patch('app.services.aprovacao.AlcadaRepository.get_by_id', return_value=None):
            response = self.client.post('/api/v1/aprovacoes', json=self.payload)
        self.assertEqual(response.status_code, 404, response.text)
        self.assertIn('Alcada', response.json()['detail'])

    def test_http_patch_protected(self):
        self.create(decisao='rejeitado')
        response = self.client.patch('/api/v1/aprovacoes/1', json={'id_usuario': 1})
        self.assertEqual(response.status_code, 409, response.text)
        self.no_limit()
        response = self.client.patch('/api/v1/aprovacoes/1', json={'decisao': 'aprovado'})
        self.assertEqual(response.status_code, 403, response.text)
        response = self.client.patch('/api/v1/aprovacoes/1', json={'id_ordem': 999})
        self.assertEqual(response.status_code, 404, response.text)
