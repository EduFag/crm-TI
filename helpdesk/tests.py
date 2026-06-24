from django.test import TestCase
from core.models import CustomUser, Equipe
from helpdesk.models import Ticket, TicketCategory
from helpdesk.forms import TicketCreateForm, TicketUpdateForm

class SupervisorRequesterTestCase(TestCase):
    def setUp(self):
        # Criar equipes de teste
        self.equipe1 = Equipe.objects.create(name="TI", is_active=True)
        self.equipe2 = Equipe.objects.create(name="Suporte", is_active=True)

        # Criar categorias
        self.categoria = TicketCategory.objects.create(name="Dúvidas", is_active=True)

        # Criar usuários de teste
        self.supervisor = CustomUser.objects.create_user(
            username="test_supervisor",
            password="password123",
            first_name="Supervisor",
            last_name="Test",
            role=CustomUser.RoleChoices.SUPERVISOR
        )
        self.supervisor.equipes.add(self.equipe1)

        self.admin = CustomUser.objects.create_user(
            username="test_admin",
            password="password123",
            first_name="Admin",
            last_name="Test",
            role=CustomUser.RoleChoices.ADMIN
        )

    def test_supervisor_create_form_fields_and_validation(self):
        """Testa se as opções do formulário de criação de chamados para supervisor estão corretas."""
        form = TicketCreateForm(user=self.supervisor)
        
        # Verificar se as escolhas de tipo_solicitante são apenas "Eu mesmo(a)" e "Nome livre"
        self.assertIn('tipo_solicitante', form.fields)
        choices = form.fields['tipo_solicitante'].choices
        self.assertEqual(len(choices), 2)
        self.assertEqual(choices[0][0], 'eu')
        self.assertEqual(choices[1][0], 'texto')

        # Verificar se requester_user foi removido, mas requester_name permanece
        self.assertNotIn('requester_user', form.fields)
        self.assertIn('requester_name', form.fields)

        # Caso 1: Supervisor selecionando "Eu mesmo"
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

        # Caso 2: Supervisor selecionando "Nome livre"
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
        """Testa se o admin continua com os campos originais de criação."""
        form = TicketCreateForm(user=self.admin)
        self.assertIn('tipo_solicitante', form.fields)
        choices = form.fields['tipo_solicitante'].choices
        self.assertEqual(len(choices), 2)
        self.assertEqual(choices[0][0], 'texto')
        self.assertEqual(choices[1][0], 'usuario')

        # Admin deve ter requester_user e requester_name
        self.assertIn('requester_user', form.fields)
        self.assertIn('requester_name', form.fields)

    def test_supervisor_update_form_fields_and_initial_values(self):
        """Testa o formulário de edição de chamado para o supervisor."""
        # Chamado original cujo solicitante é o próprio supervisor
        ticket_eu = Ticket.objects.create(
            title="Ticket original eu",
            description="Desc original",
            category=self.categoria,
            created_by=self.supervisor,
            requester_name=self.supervisor.get_full_name(),
            requester_user=self.supervisor
        )

        # Chamado original cujo solicitante é outro usuário do sistema (e.g. o admin)
        ticket_outro_user = Ticket.objects.create(
            title="Ticket original outro",
            description="Desc original",
            category=self.categoria,
            created_by=self.supervisor,
            requester_name=self.admin.get_full_name(),
            requester_user=self.admin
        )

        # Chamado original cujo solicitante é um nome livre
        ticket_nome_livre = Ticket.objects.create(
            title="Ticket original nome livre",
            description="Desc original",
            category=self.categoria,
            created_by=self.supervisor,
            requester_name="Beltrano"
        )

        # Testar formulário para ticket_eu
        form_eu = TicketUpdateForm(instance=ticket_eu, user=self.supervisor)
        self.assertEqual(form_eu.fields['tipo_solicitante'].initial, 'eu')
        self.assertNotIn('requester_user', form_eu.fields)
        self.assertIn('requester_name', form_eu.fields)

        # Salvar edições do supervisor no ticket_eu
        data_eu = {
            'tipo_solicitante': 'eu',
            'title': 'Ticket original eu (editado)',
            'description': 'Desc original',
            'category': self.categoria.id,
        }
        form_eu_save = TicketUpdateForm(data=data_eu, instance=ticket_eu, user=self.supervisor)
        self.assertTrue(form_eu_save.is_valid(), form_eu_save.errors)
        ticket_eu_saved = form_eu_save.save()
        self.assertEqual(ticket_eu_saved.requester_name, self.supervisor.get_full_name())
        self.assertEqual(ticket_eu_saved.requester_user, self.supervisor)

        # Testar formulário para ticket_outro_user
        form_outro = TicketUpdateForm(instance=ticket_outro_user, user=self.supervisor)
        self.assertEqual(form_outro.fields['tipo_solicitante'].initial, 'texto')
        self.assertEqual(form_outro.fields['requester_name'].initial, self.admin.get_full_name())

        # Testar formulário para ticket_nome_livre
        form_livre = TicketUpdateForm(instance=ticket_nome_livre, user=self.supervisor)
        self.assertEqual(form_livre.fields['tipo_solicitante'].initial, 'texto')
        self.assertEqual(form_livre.fields['requester_name'].initial, "Beltrano")
