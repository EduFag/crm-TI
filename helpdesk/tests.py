from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from core.models import CustomUser, Equipe
from helpdesk.forms import TicketCreateForm, TicketUpdateForm
from helpdesk.models import Ticket, TicketCategory, Comment, TicketContestation
from helpdesk.ticket_access import (
    filtrar_chamados_para_usuario,
    usuario_pode_acessar_chamado,
    usuario_pode_comentar_chamado,
    usuario_pode_contestar_chamado,
    usuario_pode_operar_kanban,
    usuario_ve_todos_chamados,
)


class SupervisorRequesterTestCase(TestCase):
    def setUp(self):
        self.equipe1 = Equipe.objects.create(name="TI", is_active=True)
        self.equipe2 = Equipe.objects.create(name="Suporte", is_active=True)
        self.categoria = TicketCategory.objects.create(name="Dúvidas", is_active=True)

        self.supervisor = CustomUser.objects.create_user(
            username="test_supervisor",
            password="password123",
            first_name="Supervisor",
            last_name="Test",
            role=CustomUser.RoleChoices.SUPERVISOR,
        )
        self.supervisor.equipes.add(self.equipe1)

        self.admin = CustomUser.objects.create_user(
            username="test_admin",
            password="password123",
            first_name="Admin",
            last_name="Test",
            role=CustomUser.RoleChoices.ADMIN,
        )

    def test_supervisor_create_form_fields_and_validation(self):
        form = TicketCreateForm(user=self.supervisor)
        self.assertIn('tipo_solicitante', form.fields)
        choices = form.fields['tipo_solicitante'].choices
        self.assertEqual(len(choices), 2)
        self.assertEqual(choices[0][0], 'eu')
        self.assertEqual(choices[1][0], 'texto')
        self.assertNotIn('requester_user', form.fields)
        self.assertIn('requester_name', form.fields)

        data_eu = {
            'tipo_solicitante': 'eu',
            'title': 'Test ticket by self',
            'description': 'Description of test ticket',
            'category': self.categoria.id,
        }
        form_eu = TicketCreateForm(data=data_eu, user=self.supervisor)
        self.assertTrue(form_eu.is_valid(), form_eu.errors)
        ticket_eu = form_eu.save(created_by=self.supervisor)
        self.assertEqual(ticket_eu.requester_name, "Supervisor Test")
        self.assertEqual(ticket_eu.requester_user, self.supervisor)

        data_texto = {
            'tipo_solicitante': 'texto',
            'requester_name': 'Fulano de Tal',
            'title': 'Test ticket by text name',
            'description': 'Description of test ticket',
            'category': self.categoria.id,
        }
        form_texto = TicketCreateForm(data=data_texto, user=self.supervisor)
        self.assertTrue(form_texto.is_valid(), form_texto.errors)
        ticket_texto = form_texto.save(created_by=self.supervisor)
        self.assertEqual(ticket_texto.requester_name, "Fulano de Tal")
        self.assertIsNone(ticket_texto.requester_user)

    def test_admin_create_form_fields(self):
        form = TicketCreateForm(user=self.admin)
        self.assertIn('tipo_solicitante', form.fields)
        choices = form.fields['tipo_solicitante'].choices
        self.assertEqual(len(choices), 2)
        self.assertEqual(choices[0][0], 'texto')
        self.assertEqual(choices[1][0], 'usuario')
        self.assertIn('requester_user', form.fields)
        self.assertIn('requester_name', form.fields)

    def test_supervisor_update_form_fields_and_initial_values(self):
        ticket_eu = Ticket.objects.create(
            title="Ticket original eu",
            description="Desc original",
            category=self.categoria,
            created_by=self.supervisor,
            requester_name=self.supervisor.get_full_name(),
            requester_user=self.supervisor,
        )
        ticket_outro_user = Ticket.objects.create(
            title="Ticket original outro",
            description="Desc original",
            category=self.categoria,
            created_by=self.supervisor,
            requester_name=self.admin.get_full_name(),
            requester_user=self.admin,
        )
        ticket_nome_livre = Ticket.objects.create(
            title="Ticket original nome livre",
            description="Desc original",
            category=self.categoria,
            created_by=self.supervisor,
            requester_name="Beltrano",
        )

        form_eu = TicketUpdateForm(instance=ticket_eu, user=self.supervisor)
        self.assertEqual(form_eu.fields['tipo_solicitante'].initial, 'eu')

        form_outro = TicketUpdateForm(instance=ticket_outro_user, user=self.supervisor)
        self.assertEqual(form_outro.fields['tipo_solicitante'].initial, 'texto')

        form_livre = TicketUpdateForm(instance=ticket_nome_livre, user=self.supervisor)
        self.assertEqual(form_livre.fields['tipo_solicitante'].initial, 'texto')
        self.assertEqual(form_livre.fields['requester_name'].initial, "Beltrano")


class RbacHelpdeskTestCase(TestCase):
    def setUp(self):
        self.equipe = Equipe.objects.create(name="Comercial", is_active=True)
        self.categoria = TicketCategory.objects.create(name="Software", is_active=True)

        self.it_user = CustomUser.objects.create_user(
            username="ti_user", password="x", role=CustomUser.RoleChoices.IT_USER,
        )
        self.supervisor = CustomUser.objects.create_user(
            username="supervisor", password="x", role=CustomUser.RoleChoices.SUPERVISOR,
        )
        self.team_leader = CustomUser.objects.create_user(
            username="lider", password="x", role=CustomUser.RoleChoices.TEAM_LEADER,
        )
        self.multiplier = CustomUser.objects.create_user(
            username="multi", password="x", role=CustomUser.RoleChoices.MULTIPLIER,
        )
        self.standard = CustomUser.objects.create_user(
            username="padrao", password="x", role=CustomUser.RoleChoices.STANDARD,
        )
        self.colega = CustomUser.objects.create_user(
            username="colega", password="x", role=CustomUser.RoleChoices.STANDARD,
        )

        self.team_leader.equipes.add(self.equipe)
        self.supervisor.equipes.add(self.equipe)
        self.multiplier.equipes.add(self.equipe)
        self.colega.equipes.add(self.equipe)

        self.ticket_equipe = Ticket.objects.create(
            title="Chamado equipe",
            description="Desc",
            category=self.categoria,
            equipe=self.equipe,
            created_by=self.colega,
            requester_name="Colega",
            requester_user=self.colega,
        )
        self.ticket_outro = Ticket.objects.create(
            title="Chamado externo",
            description="Desc",
            category=self.categoria,
            created_by=self.standard,
            requester_name="Padrao",
            requester_user=self.standard,
        )

    def test_supervisor_ve_apenas_equipe(self):
        self.assertFalse(usuario_ve_todos_chamados(self.supervisor))
        qs = filtrar_chamados_para_usuario(Ticket.objects.all(), self.supervisor)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().pk, self.ticket_equipe.pk)

    def test_lider_ve_apenas_equipe(self):
        qs = filtrar_chamados_para_usuario(Ticket.objects.all(), self.team_leader)
        self.assertEqual(qs.count(), 1)
        self.assertEqual(qs.first().pk, self.ticket_equipe.pk)

    def test_lider_nao_comenta_chamado_alheio(self):
        self.assertTrue(usuario_pode_acessar_chamado(self.team_leader, self.ticket_equipe))
        self.assertFalse(usuario_pode_comentar_chamado(self.team_leader, self.ticket_equipe))

    def test_lider_comenta_proprio_chamado(self):
        self.ticket_equipe.created_by = self.team_leader
        self.ticket_equipe.save(update_fields=['created_by'])
        self.assertTrue(usuario_pode_comentar_chamado(self.team_leader, self.ticket_equipe))

    def test_supervisor_comenta_apenas_visiveis(self):
        self.assertFalse(usuario_pode_comentar_chamado(self.supervisor, self.ticket_outro))
        self.assertTrue(usuario_pode_comentar_chamado(self.supervisor, self.ticket_equipe))

    def test_supervisor_nao_move_kanban(self):
        self.assertFalse(usuario_pode_operar_kanban(self.supervisor))

    def test_it_user_move_kanban(self):
        self.assertTrue(usuario_pode_operar_kanban(self.it_user))

    def test_multiplicador_co_autor(self):
        form = TicketCreateForm(user=self.multiplier)
        self.assertEqual(len(form.fields['tipo_solicitante'].choices), 2)
        self.assertNotIn('co_autor_user', form.fields)

        data = {
            'tipo_solicitante': 'texto',
            'requester_name': self.colega.get_full_name() or self.colega.username,
            'title': 'Chamado multiplicador',
            'description': 'Descricao',
            'category': self.categoria.id,
        }
        form = TicketCreateForm(data=data, user=self.multiplier)
        self.assertTrue(form.is_valid(), form.errors)
        ticket = form.save(created_by=self.multiplier)
        self.assertTrue(ticket.co_authors.filter(pk=self.colega.pk).exists())
        self.assertTrue(usuario_pode_acessar_chamado(self.colega, ticket))
        self.assertTrue(usuario_pode_comentar_chamado(self.colega, ticket))

    def test_multiplicador_ve_apenas_proprios_e_co_autor(self):
        ticket = Ticket.objects.create(
            title="Proprio",
            description="Desc",
            category=self.categoria,
            created_by=self.multiplier,
            requester_name="Multi",
            requester_user=self.multiplier,
        )
        qs = filtrar_chamados_para_usuario(Ticket.objects.all(), self.multiplier)
        self.assertEqual(qs.count(), 1)
        self.ticket_equipe.co_authors.add(self.multiplier)
        qs = filtrar_chamados_para_usuario(Ticket.objects.all(), self.multiplier)
        self.assertEqual(qs.count(), 2)


class ArquivamentoAutomaticoTestCase(TestCase):
    def setUp(self):
        self.categoria = TicketCategory.objects.create(name="Rede", is_active=True)

    def test_arquiva_resolvido_apos_24h_por_resolved_at(self):
        """Comentários não devem adiar arquivamento — usa resolved_at, não updated_at."""
        ticket = Ticket.objects.create(
            title="Chamado antigo",
            description="Desc",
            category=self.categoria,
            requester_name="Teste",
            status=Ticket.StatusChoices.RESOLVED,
            resolved_at=timezone.now() - timedelta(hours=25),
        )
        ticket.updated_at = timezone.now()
        ticket.save(update_fields=['updated_at'])

        Ticket.archive_old_tickets()
        ticket.refresh_from_db()
        self.assertTrue(ticket.is_archived)

    def test_nao_arquiva_resolvido_recente(self):
        ticket = Ticket.objects.create(
            title="Chamado novo",
            description="Desc",
            category=self.categoria,
            requester_name="Teste",
            status=Ticket.StatusChoices.RESOLVED,
            resolved_at=timezone.now() - timedelta(hours=2),
        )
        Ticket.archive_old_tickets()
        ticket.refresh_from_db()
        self.assertFalse(ticket.is_archived)

    def test_arquiva_mesmo_com_resolved_at_recente_se_comentario_antigo(self):
        """resolved_at errado (updated_at recente) não deve impedir arquivamento."""
        ticket = Ticket.objects.create(
            title="Finalizado há dias",
            description="Desc",
            category=self.categoria,
            requester_name="Teste",
            status=Ticket.StatusChoices.RESOLVED,
            resolved_at=timezone.now(),
        )
        Comment.objects.create(
            ticket=ticket,
            text='Chamado finalizado.\nObservação: ok',
        )
        Comment.objects.filter(ticket=ticket).update(
            created_at=timezone.now() - timedelta(hours=30),
        )
        # Simula resolved_at preenchido errado pelo backfill antigo
        Ticket.objects.filter(pk=ticket.pk).update(
            resolved_at=timezone.now(),
        )

        Ticket.archive_old_tickets()
        ticket.refresh_from_db()
        self.assertTrue(ticket.is_archived)
        self.assertLess(ticket.resolved_at, timezone.now() - timedelta(hours=24))

    def test_save_define_resolved_at_ao_finalizar(self):
        ticket = Ticket.objects.create(
            title="Em atendimento",
            description="Desc",
            category=self.categoria,
            requester_name="Teste",
            status=Ticket.StatusChoices.IN_PROGRESS,
        )
        ticket.status = Ticket.StatusChoices.RESOLVED
        ticket.save()
        ticket.refresh_from_db()
        self.assertIsNotNone(ticket.resolved_at)


class HistoryExportCsvTestCase(TestCase):
    def setUp(self):
        self.categoria = TicketCategory.objects.create(name="Hardware", is_active=True)
        self.it_user = CustomUser.objects.create_user(
            username="ti_export",
            password="x",
            role=CustomUser.RoleChoices.IT_USER,
        )
        self.supervisor = CustomUser.objects.create_user(
            username="super_export",
            password="x",
            role=CustomUser.RoleChoices.SUPERVISOR,
        )
        self.ticket_novo = Ticket.objects.create(
            title="Impressora quebrada",
            description="Não imprime",
            category=self.categoria,
            requester_name="João Silva",
            status=Ticket.StatusChoices.NEW,
        )
        self.ticket_resolvido = Ticket.objects.create(
            title="VPN lenta",
            description="Conexão instável",
            category=self.categoria,
            requester_name="Maria",
            status=Ticket.StatusChoices.RESOLVED,
        )
        Ticket.objects.filter(pk=self.ticket_novo.pk).update(
            created_at=timezone.now() - timedelta(days=5),
        )
        Ticket.objects.filter(pk=self.ticket_resolvido.pk).update(
            created_at=timezone.now() - timedelta(days=3),
        )
        self.ticket_novo.refresh_from_db()
        self.ticket_resolvido.refresh_from_db()

        self.date_from = (timezone.now() - timedelta(days=10)).strftime('%Y-%m-%d')
        self.date_to = timezone.now().strftime('%Y-%m-%d')

    def _url_export(self, **params):
        from django.urls import reverse
        base = reverse('helpdesk:history_export')
        query = {'date_from': self.date_from, 'date_to': self.date_to, **params}
        return f"{base}?{'&'.join(f'{k}={v}' for k, v in query.items())}"

    def test_it_user_exporta_csv_com_dados(self):
        self.client.force_login(self.it_user)
        response = self.client.get(self._url_export())
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        self.assertIn('attachment', response['Content-Disposition'])
        conteudo = response.content.decode('utf-8-sig')
        self.assertIn('ID;Título;Descrição;Solicitante', conteudo)
        self.assertIn('Impressora quebrada', conteudo)
        self.assertIn('João Silva', conteudo)
        self.assertIn('Hardware', conteudo)

    def test_supervisor_sem_permissao_export(self):
        self.client.force_login(self.supervisor)
        response = self.client.get(self._url_export())
        self.assertEqual(response.status_code, 403)

    def test_export_sem_periodo_redireciona_com_erro(self):
        self.client.force_login(self.it_user)
        from django.urls import reverse
        response = self.client.get(reverse('helpdesk:history_export'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('erro=export_periodo', response.url)

    def test_export_respeita_filtro_status(self):
        self.client.force_login(self.it_user)
        response = self.client.get(self._url_export(status=Ticket.StatusChoices.RESOLVED))
        self.assertEqual(response.status_code, 200)
        conteudo = response.content.decode('utf-8-sig')
        self.assertIn('VPN lenta', conteudo)
        self.assertNotIn('Impressora quebrada', conteudo)


class HistoricoFiltroArquivadoTestCase(TestCase):
    def setUp(self):
        self.categoria = TicketCategory.objects.create(name="Rede", is_active=True)
        self.it_user = CustomUser.objects.create_user(
            username="ti_historico",
            password="x",
            role=CustomUser.RoleChoices.IT_USER,
        )
        self.ticket_ativo = Ticket.objects.create(
            title="Chamado ativo",
            description="Desc",
            category=self.categoria,
            requester_name="Teste",
            status=Ticket.StatusChoices.NEW,
            is_archived=False,
        )
        self.ticket_arquivado = Ticket.objects.create(
            title="Chamado arquivado",
            description="Desc",
            category=self.categoria,
            requester_name="Teste",
            status=Ticket.StatusChoices.RESOLVED,
            is_archived=True,
            resolved_at=timezone.now() - timedelta(hours=48),
        )
        Ticket.objects.filter(pk=self.ticket_arquivado.pk).update(
            created_at=timezone.now() - timedelta(days=30),
        )

    def _aplicar_filtro(self, archived=None):
        from django.test import RequestFactory
        from helpdesk.views.history import aplicar_filtros_historico, queryset_historico_base

        rf = RequestFactory()
        query = {}
        if archived is not None:
            query['archived'] = archived
        request = rf.get('/helpdesk/history/', query)
        qs = queryset_historico_base(self.it_user)
        return aplicar_filtros_historico(qs, request)

    def test_filtro_sim_so_arquivados(self):
        qs = self._aplicar_filtro('yes')
        self.assertEqual(qs.count(), 1)
        self.assertTrue(qs.filter(pk=self.ticket_arquivado.pk).exists())
        self.assertFalse(qs.filter(pk=self.ticket_ativo.pk).exists())

    def test_filtro_nao_so_nao_arquivados(self):
        qs = self._aplicar_filtro('no')
        self.assertEqual(qs.count(), 1)
        self.assertTrue(qs.filter(pk=self.ticket_ativo.pk).exists())
        self.assertFalse(qs.filter(pk=self.ticket_arquivado.pk).exists())

    def test_filtro_ambos_inclui_os_dois(self):
        qs = self._aplicar_filtro('')
        self.assertEqual(qs.count(), 2)
        self.assertTrue(qs.filter(pk=self.ticket_ativo.pk).exists())
        self.assertTrue(qs.filter(pk=self.ticket_arquivado.pk).exists())

    def test_filtro_ambos_sem_parametro(self):
        from django.test import RequestFactory
        from helpdesk.views.history import aplicar_filtros_historico, queryset_historico_base

        rf = RequestFactory()
        request = rf.get('/helpdesk/history/')
        qs = aplicar_filtros_historico(queryset_historico_base(self.it_user), request)
        self.assertEqual(qs.count(), 2)

    def test_ambos_paginacao_exibe_arquivados_em_pagina_seguinte(self):
        from django.urls import reverse

        agora = timezone.now()
        for i in range(22):
            ticket = Ticket.objects.create(
                title=f"Recente {i}",
                description="Desc",
                category=self.categoria,
                requester_name="Teste",
                status=Ticket.StatusChoices.NEW,
                is_archived=False,
            )
            Ticket.objects.filter(pk=ticket.pk).update(
                created_at=agora - timedelta(hours=i),
            )
        for i in range(8):
            ticket = Ticket.objects.create(
                title=f"Arquivado antigo {i}",
                description="Desc",
                category=self.categoria,
                requester_name="Teste",
                status=Ticket.StatusChoices.RESOLVED,
                is_archived=True,
                resolved_at=agora - timedelta(days=10),
            )
            Ticket.objects.filter(pk=ticket.pk).update(
                created_at=agora - timedelta(days=30, hours=i),
            )

        self.client.force_login(self.it_user)
        url = reverse('helpdesk:history')

        response_p1 = self.client.get(url)
        self.assertEqual(response_p1.status_code, 200)
        self.assertContains(response_p1, 'Página 1 de')
        self.assertNotContains(response_p1, 'Arquivado antigo 0')

        response_p2 = self.client.get(f'{url}?page=2')
        self.assertEqual(response_p2.status_code, 200)
        self.assertContains(response_p2, 'Arquivado antigo')
        self.assertContains(response_p2, 'Arq')


class ComentarioFinalizadoTestCase(TestCase):
    def setUp(self):
        self.categoria = TicketCategory.objects.create(name="Software", is_active=True)
        self.it_user = CustomUser.objects.create_user(
            username="ti_final", password="x", role=CustomUser.RoleChoices.IT_USER,
        )
        self.admin = CustomUser.objects.create_user(
            username="admin_final", password="x", role=CustomUser.RoleChoices.ADMIN,
        )
        self.supervisor = CustomUser.objects.create_user(
            username="sup_final", password="x", role=CustomUser.RoleChoices.SUPERVISOR,
        )
        self.standard = CustomUser.objects.create_user(
            username="pad_final", password="x", role=CustomUser.RoleChoices.STANDARD,
        )
        self.ticket = Ticket.objects.create(
            title="Chamado resolvido",
            description="Desc",
            category=self.categoria,
            created_by=self.standard,
            requester_name="Padrao",
            requester_user=self.standard,
            status=Ticket.StatusChoices.RESOLVED,
            resolved_at=timezone.now(),
        )

    def test_standard_nao_comenta_finalizado(self):
        self.assertFalse(usuario_pode_comentar_chamado(self.standard, self.ticket))

    def test_supervisor_nao_comenta_finalizado(self):
        self.assertFalse(usuario_pode_comentar_chamado(self.supervisor, self.ticket))

    def test_it_user_comenta_finalizado(self):
        self.assertTrue(usuario_pode_comentar_chamado(self.it_user, self.ticket))

    def test_admin_comenta_finalizado(self):
        self.assertTrue(usuario_pode_comentar_chamado(self.admin, self.ticket))

    def test_standard_comenta_nao_finalizado(self):
        self.ticket.status = Ticket.StatusChoices.NEW
        self.ticket.save()
        self.assertTrue(usuario_pode_comentar_chamado(self.standard, self.ticket))


class ContestacaoChamadoTestCase(TestCase):
    def setUp(self):
        self.categoria = TicketCategory.objects.create(name="Rede", is_active=True)
        self.it_user = CustomUser.objects.create_user(
            username="ti_contest", password="x", role=CustomUser.RoleChoices.IT_USER,
        )
        self.standard = CustomUser.objects.create_user(
            username="sol_contest", password="x", role=CustomUser.RoleChoices.STANDARD,
        )
        self.outro = CustomUser.objects.create_user(
            username="outro_contest", password="x", role=CustomUser.RoleChoices.STANDARD,
        )
        self.resolved_at = timezone.now() - timedelta(hours=2)
        self.ticket = Ticket.objects.create(
            title="Chamado para contestar",
            description="Desc",
            category=self.categoria,
            created_by=self.standard,
            requester_name="Solicitante",
            requester_user=self.standard,
            status=Ticket.StatusChoices.RESOLVED,
            resolved_at=self.resolved_at,
            resolved_by=self.it_user,
            assigned_to=self.it_user,
        )

    def test_solicitante_pode_contestar(self):
        self.assertTrue(usuario_pode_contestar_chamado(self.standard, self.ticket))

    def test_operador_nao_contesta(self):
        self.assertFalse(usuario_pode_contestar_chamado(self.it_user, self.ticket))

    def test_usuario_alheio_nao_contesta(self):
        self.assertFalse(usuario_pode_contestar_chamado(self.outro, self.ticket))

    def test_arquivado_nao_contesta(self):
        self.ticket.is_archived = True
        self.ticket.save()
        self.assertFalse(usuario_pode_contestar_chamado(self.standard, self.ticket))

    def test_nao_finalizado_nao_contesta(self):
        self.ticket.status = Ticket.StatusChoices.IN_PROGRESS
        self.ticket.save()
        self.assertFalse(usuario_pode_contestar_chamado(self.standard, self.ticket))

    def test_co_autor_pode_contestar(self):
        self.ticket.created_by = self.outro
        self.ticket.requester_user = self.outro
        self.ticket.co_authors.add(self.standard)
        self.ticket.save()
        self.assertTrue(usuario_pode_contestar_chamado(self.standard, self.ticket))

    def test_recusado_pode_ser_contestado(self):
        self.ticket.is_rejected = True
        self.ticket.rejection_reason = 'Fora de escopo'
        self.ticket.save()
        self.assertTrue(usuario_pode_contestar_chamado(self.standard, self.ticket))

    def test_post_contest_reabre_como_novo(self):
        from django.urls import reverse
        import json

        self.client.force_login(self.standard)
        url = reverse('helpdesk:ticket_contest', args=[self.ticket.pk])
        response = self.client.post(
            url,
            data=json.dumps({'reason': 'Problema persiste'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, Ticket.StatusChoices.NEW)
        self.assertFalse(self.ticket.is_rejected)
        self.assertIsNone(self.ticket.resolved_at)
        self.assertIsNone(self.ticket.resolved_by)
        self.assertTrue(self.ticket.unread_by_tech)

        contestacao = TicketContestation.objects.get(ticket=self.ticket)
        self.assertEqual(contestacao.contested_by, self.standard)
        self.assertEqual(contestacao.finalized_by, self.it_user)
        self.assertEqual(contestacao.reason, 'Problema persiste')
        self.assertFalse(contestacao.was_rejected)

        comentario = Comment.objects.filter(ticket=self.ticket, text__startswith='Contestação do chamado').first()
        self.assertIsNotNone(comentario)
        self.assertIn('Problema persiste', comentario.text)
        self.assertIn(self.it_user.get_full_name() or self.it_user.username, comentario.text)

    def test_post_contest_sem_permissao(self):
        from django.urls import reverse
        import json

        self.client.force_login(self.outro)
        url = reverse('helpdesk:ticket_contest', args=[self.ticket.pk])
        response = self.client.post(
            url,
            data=json.dumps({'reason': 'Tentativa inválida'}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)


class DestinatariosNotificacaoTestCase(TestCase):
    def setUp(self):
        self.categoria = TicketCategory.objects.create(name='Cat Notif', is_active=True)
        self.admin = CustomUser.objects.create_user(
            username='notif_admin', password='pass', role=CustomUser.RoleChoices.ADMIN,
        )
        self.it_user = CustomUser.objects.create_user(
            username='notif_it', password='pass', role=CustomUser.RoleChoices.IT_USER,
        )
        self.it_user2 = CustomUser.objects.create_user(
            username='notif_it2', password='pass', role=CustomUser.RoleChoices.IT_USER,
        )
        self.supervisor = CustomUser.objects.create_user(
            username='notif_sup', password='pass', role=CustomUser.RoleChoices.SUPERVISOR,
        )
        self.standard = CustomUser.objects.create_user(
            username='notif_std', password='pass', role=CustomUser.RoleChoices.STANDARD,
        )
        self.ticket = Ticket.objects.create(
            title='Chamado notif',
            description='Desc',
            category=self.categoria,
            created_by=self.standard,
            requester_user=self.standard,
            requester_name='Std',
            status=Ticket.StatusChoices.NEW,
        )

    def test_broadcast_novos_so_operadores_ti_sem_supervisor(self):
        from helpdesk.notifications import destinatarios_notificacao
        ids = {u.pk for u in destinatarios_notificacao(self.ticket, self.standard)}
        self.assertIn(self.admin.pk, ids)
        self.assertIn(self.it_user.pk, ids)
        self.assertNotIn(self.supervisor.pk, ids)
        self.assertNotIn(self.standard.pk, ids)

    def test_silencio_ti_nao_notifica_outro_ti(self):
        from helpdesk.notifications import destinatarios_notificacao
        self.ticket.assigned_to = self.it_user
        self.ticket.save(update_fields=['assigned_to'])
        ids = {u.pk for u in destinatarios_notificacao(self.ticket, self.it_user2)}
        self.assertNotIn(self.admin.pk, ids)
        self.assertNotIn(self.it_user.pk, ids)
        self.assertIn(self.standard.pk, ids)

    def test_finalizacao_so_nao_operadores(self):
        from helpdesk.notifications import destinatarios_finalizacao
        self.ticket.assigned_to = self.it_user
        self.ticket.save(update_fields=['assigned_to'])
        ids = {u.pk for u in destinatarios_finalizacao(self.ticket, self.it_user)}
        self.assertIn(self.standard.pk, ids)
        self.assertNotIn(self.admin.pk, ids)
        self.assertNotIn(self.it_user2.pk, ids)


class MentionAccessTestCase(TestCase):
    def setUp(self):
        self.categoria = TicketCategory.objects.create(name='Cat Mention', is_active=True)
        self.admin = CustomUser.objects.create_user(
            username='mention_admin', password='pass', role=CustomUser.RoleChoices.ADMIN,
        )
        self.standard = CustomUser.objects.create_user(
            username='mention_alvo', password='pass', role=CustomUser.RoleChoices.STANDARD,
        )
        self.outro = CustomUser.objects.create_user(
            username='mention_outro', password='pass', role=CustomUser.RoleChoices.STANDARD,
        )
        self.ticket = Ticket.objects.create(
            title='Chamado menção',
            description='Desc',
            category=self.categoria,
            created_by=self.outro,
            requester_user=self.outro,
            requester_name='Outro',
            status=Ticket.StatusChoices.IN_PROGRESS,
        )

    def test_mencao_concede_acesso_e_cria_ticketmention(self):
        from helpdesk.mentions import processar_mencoes
        from helpdesk.models import TicketMention

        self.assertFalse(usuario_pode_acessar_chamado(self.standard, self.ticket))
        comment = Comment.objects.create(
            ticket=self.ticket,
            author=self.admin,
            text='Olá @mention_alvo, pode verificar?',
        )
        mencionados = processar_mencoes(self.ticket, comment, self.admin)
        self.assertEqual(len(mencionados), 1)
        self.assertEqual(mencionados[0].pk, self.standard.pk)
        self.assertTrue(usuario_pode_acessar_chamado(self.standard, self.ticket))
        self.assertTrue(
            TicketMention.objects.filter(
                ticket=self.ticket, user=self.standard, comment=comment, seen_at__isnull=True,
            ).exists()
        )

    def test_usuario_nao_operador_nao_processa_mencao(self):
        from helpdesk.mentions import processar_mencoes
        comment = Comment.objects.create(
            ticket=self.ticket,
            author=self.outro,
            text='@mention_alvo teste',
        )
        mencionados = processar_mencoes(self.ticket, comment, self.outro)
        self.assertEqual(mencionados, [])
        self.assertFalse(usuario_pode_acessar_chamado(self.standard, self.ticket))

    def test_ti_menciona_outro_ti_entra_no_nao_lido(self):
        """Menção TI→TI gera badge mesmo com silêncio geral entre operadores."""
        from helpdesk.models import TicketUnread
        from helpdesk.views.kanban import adicionar_nao_lido

        it_alvo = CustomUser.objects.create_user(
            username='mention_it_alvo',
            password='pass',
            role=CustomUser.RoleChoices.IT_USER,
        )
        comment = Comment.objects.create(
            ticket=self.ticket,
            author=self.admin,
            text='Ei @mention_it_alvo, olha isso',
        )
        from helpdesk.mentions import processar_mencoes
        mencionados = processar_mencoes(self.ticket, comment, self.admin)
        self.assertEqual([u.pk for u in mencionados], [it_alvo.pk])

        adicionar_nao_lido(self.ticket, self.admin, usuarios_extra=mencionados)
        self.assertTrue(
            TicketUnread.objects.filter(ticket=self.ticket, user=it_alvo).exists()
        )


class FilaPosicaoTestCase(TestCase):
    def setUp(self):
        self.categoria = TicketCategory.objects.create(name='Cat Fila', is_active=True)
        self.user = CustomUser.objects.create_user(
            username='fila_user', password='pass', role=CustomUser.RoleChoices.STANDARD,
        )

    def _criar(self, pk_force, priority, status=Ticket.StatusChoices.NEW):
        t = Ticket(
            title=f'T{pk_force}',
            description='d',
            category=self.categoria,
            created_by=self.user,
            requester_name='u',
            priority=priority,
            status=status,
        )
        t.save()
        # Ajusta pk via update só se necessário — usamos ordem natural dos ids criados
        return t

    def test_ordem_exemplo_plano(self):
        from helpdesk.queue import calcular_posicoes_fila

        # Cria na ordem dos números do exemplo (mais antigo primeiro)
        t123 = self._criar(123, Ticket.PriorityChoices.HIGH)
        t234 = self._criar(234, Ticket.PriorityChoices.LOW)
        t456 = self._criar(456, Ticket.PriorityChoices.MEDIUM)
        t567 = self._criar(567, Ticket.PriorityChoices.MEDIUM)
        t789 = self._criar(789, Ticket.PriorityChoices.URGENT)

        # Garante pks relativos iguais à ordem de criação
        tickets = [t123, t234, t456, t567, t789]
        self.assertEqual(
            [t.pk for t in tickets],
            sorted(t.pk for t in tickets),
        )

        posicoes = calcular_posicoes_fila(tickets)
        # Urgente (último criado = maior pk) em 1º; depois High; Medias por pk; Low por último
        ordem = sorted(tickets, key=lambda t: posicoes[t.pk])
        self.assertEqual(
            [t.priority for t in ordem],
            [
                Ticket.PriorityChoices.URGENT,
                Ticket.PriorityChoices.HIGH,
                Ticket.PriorityChoices.MEDIUM,
                Ticket.PriorityChoices.MEDIUM,
                Ticket.PriorityChoices.LOW,
            ],
        )
        self.assertEqual(ordem[0].pk, t789.pk)
        self.assertEqual(ordem[1].pk, t123.pk)
        self.assertEqual(ordem[2].pk, t456.pk)
        self.assertEqual(ordem[3].pk, t567.pk)
        self.assertEqual(ordem[4].pk, t234.pk)

    def test_in_progress_entra_no_ranking(self):
        from helpdesk.queue import calcular_posicoes_fila

        novo = self._criar(1, Ticket.PriorityChoices.HIGH, Ticket.StatusChoices.NEW)
        andamento = self._criar(2, Ticket.PriorityChoices.URGENT, Ticket.StatusChoices.IN_PROGRESS)
        posicoes = calcular_posicoes_fila([novo, andamento])
        self.assertEqual(posicoes[andamento.pk], 1)
        self.assertEqual(posicoes[novo.pk], 2)

    def test_em_atendimento_pesa_mais_que_novo(self):
        """
        Novo: 123 Média, 125 Alta, 126 Baixa
        Em Atendimento: 124 Média, 120 Alta, 127 Urgente
        Ordem: 127, 120, 124, 125, 123, 126
        """
        from helpdesk.queue import calcular_posicoes_fila

        t123 = self._criar(123, Ticket.PriorityChoices.MEDIUM, Ticket.StatusChoices.NEW)
        t125 = self._criar(125, Ticket.PriorityChoices.HIGH, Ticket.StatusChoices.NEW)
        t126 = self._criar(126, Ticket.PriorityChoices.LOW, Ticket.StatusChoices.NEW)
        t124 = self._criar(124, Ticket.PriorityChoices.MEDIUM, Ticket.StatusChoices.IN_PROGRESS)
        t120 = self._criar(120, Ticket.PriorityChoices.HIGH, Ticket.StatusChoices.IN_PROGRESS)
        t127 = self._criar(127, Ticket.PriorityChoices.URGENT, Ticket.StatusChoices.IN_PROGRESS)

        tickets = [t123, t125, t126, t124, t120, t127]
        posicoes = calcular_posicoes_fila(tickets)
        ordem = sorted(tickets, key=lambda t: posicoes[t.pk])
        self.assertEqual(
            [t.pk for t in ordem],
            [t127.pk, t120.pk, t124.pk, t125.pk, t123.pk, t126.pk],
        )

    def test_posicao_global_igual_para_usuario_com_visao_filtrada(self):
        """Usuário padrão vê só o próprio card, mas a posição é a da fila global."""
        from helpdesk.queue import aplicar_posicoes_fila, calcular_posicoes_fila_global

        outros = [
            self._criar(i, Ticket.PriorityChoices.URGENT)
            for i in range(4)
        ]
        meu = self._criar(99, Ticket.PriorityChoices.LOW)

        posicoes_globais = calcular_posicoes_fila_global()
        # Só o card do usuário na lista “visível”
        aplicar_posicoes_fila([meu], [])
        self.assertEqual(meu.queue_position, posicoes_globais[meu.pk])
        self.assertEqual(meu.queue_position, len(outros) + 1)


class ChamadoRestritoCriador25TestCase(TestCase):
    """Chamados do criador restrito só aparecem para o TI exclusivo (e stakeholders)."""

    def setUp(self):
        from unittest.mock import patch
        self.categoria = TicketCategory.objects.create(name='Cat Restrito', is_active=True)
        self.criador = CustomUser.objects.create_user(
            username='criador_restrito', password='pass', role=CustomUser.RoleChoices.STANDARD,
        )
        self.ti_exclusivo = CustomUser.objects.create_user(
            username='ti_exclusivo', password='pass', role=CustomUser.RoleChoices.IT_USER,
        )
        self.outro_ti = CustomUser.objects.create_user(
            username='outro_ti', password='pass', role=CustomUser.RoleChoices.IT_USER,
        )
        self.admin = CustomUser.objects.create_user(
            username='admin_restrito', password='pass', role=CustomUser.RoleChoices.ADMIN,
        )
        self.ticket = Ticket.objects.create(
            title='Chamado restrito',
            description='d',
            category=self.categoria,
            created_by=self.criador,
            requester_user=self.criador,
            requester_name='Criador',
        )
        self._patcher = patch.multiple(
            'helpdesk.ticket_access',
            CRIADOR_CHAMADOS_RESTRITOS_ID=self.criador.pk,
            TI_VISUALIZADOR_EXCLUSIVO_ID=self.ti_exclusivo.pk,
        )
        self._patcher.start()

    def tearDown(self):
        self._patcher.stop()

    def test_ti_exclusivo_ve_e_outro_ti_nao(self):
        self.assertTrue(usuario_pode_acessar_chamado(self.ti_exclusivo, self.ticket))
        self.assertFalse(usuario_pode_acessar_chamado(self.outro_ti, self.ticket))
        self.assertFalse(usuario_pode_acessar_chamado(self.admin, self.ticket))

        qs_ti = filtrar_chamados_para_usuario(Ticket.objects.all(), self.ti_exclusivo)
        qs_outro = filtrar_chamados_para_usuario(Ticket.objects.all(), self.outro_ti)
        self.assertIn(self.ticket, qs_ti)
        self.assertNotIn(self.ticket, qs_outro)

    def test_criador_ainda_ve_proprio_chamado(self):
        self.assertTrue(usuario_pode_acessar_chamado(self.criador, self.ticket))

    def test_solicitante_restrito_mesmo_com_outro_criador(self):
        """User 25 como solicitante também esconde o chamado dos outros TI."""
        outro_user = CustomUser.objects.create_user(
            username='abre_para_restrito', password='pass', role=CustomUser.RoleChoices.STANDARD,
        )
        ticket = Ticket.objects.create(
            title='Aberto para solicitante restrito',
            description='d',
            category=self.categoria,
            created_by=outro_user,
            requester_user=self.criador,
            requester_name='Criador Restrito',
        )
        self.assertTrue(usuario_pode_acessar_chamado(self.ti_exclusivo, ticket))
        self.assertFalse(usuario_pode_acessar_chamado(self.outro_ti, ticket))
        self.assertTrue(usuario_pode_acessar_chamado(self.criador, ticket))
        self.assertTrue(usuario_pode_acessar_chamado(outro_user, ticket))

        qs_outro = filtrar_chamados_para_usuario(Ticket.objects.all(), self.outro_ti)
        self.assertNotIn(ticket, qs_outro)
