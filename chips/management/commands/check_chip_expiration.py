from django.core.management.base import BaseCommand
from chips.services import recalcular_status_chips

class Command(BaseCommand):
    help = 'Verifica e cancela chips cuja data de recarga expirou (> 90 dias sem recarga)'

    def handle(self, *args, **options):
        count = recalcular_status_chips()
        self.stdout.write(self.style.SUCCESS(f'Concluído. {count} chips cancelados por vencimento.'))
