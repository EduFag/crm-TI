from django.test import TestCase
from emails.models import EmailAccount, EmailDomain
from chips.models import Chip, Operator
from emails.forms import EmailAccountForm


class EmailChipLinkTestCase(TestCase):
    def setUp(self):
        self.operator = Operator.objects.create(name="Claro")
        self.domain = EmailDomain.objects.create(name="empresa.com.br")
        self.chip1 = Chip.objects.create(line_number="11999990001", operator=self.operator)
        self.chip2 = Chip.objects.create(line_number="11999990002", operator=self.operator)

    def test_create_email_with_chip_link(self):
        form_data = {
            'username': 'joao.silva',
            'domain': self.domain.pk,
            'employee_name': 'João Silva',
            'password': '123',
            'status': 'ACTIVE',
            'chip': self.chip2.pk,
        }
        form = EmailAccountForm(data=form_data)
        self.assertTrue(form.is_valid(), form.errors)
        account = form.save()

        self.chip2.refresh_from_db()
        self.assertEqual(account.chip, self.chip2)
        self.assertEqual(self.chip2.email_vinculado, account)

    def test_update_email_chip_link(self):
        account = EmailAccount.objects.create(
            username='maria.souza',
            domain=self.domain,
            employee_name='Maria Souza'
        )
        self.chip1.email_vinculado = account
        self.chip1.save()

        # Switch to chip2
        form_data = {
            'username': 'maria.souza',
            'domain': self.domain.pk,
            'employee_name': 'Maria Souza',
            'password': '',
            'status': 'ACTIVE',
            'chip': self.chip2.pk,
        }
        form = EmailAccountForm(data=form_data, instance=account)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        self.chip1.refresh_from_db()
        self.chip2.refresh_from_db()

        self.assertIsNone(self.chip1.email_vinculado)
        self.assertEqual(self.chip2.email_vinculado, account)
        self.assertEqual(account.chip, self.chip2)
