from django.test import TestCase
from django.utils import timezone
from datetime import timedelta

from core.models import CustomUser, Equipe
from helpdesk.forms import TicketCreateForm, TicketUpdateForm
from helpdesk.models import Ticket, TicketCategory
from helpdesk.ticket_access import (
    filtrar_chamados_para_usuario,
    usuario_pode_acessar_chamado,
    usuario_pode_comentar_chamado,
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

    def test_supervisor_ve_todos_chamados(self):
        self.assertTrue(usuario_ve_todos_chamados(self.supervisor))
        qs = filtrar_chamados_para_usuario(Ticket.objects.all(), self.supervisor)
        self.assertEqual(qs.count(), 2)

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

    def test_supervisor_comenta_qualquer(self):
        self.assertTrue(usuario_pode_comentar_chamado(self.supervisor, self.ticket_outro))

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
