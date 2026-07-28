from django.core.management.base import BaseCommand
from chips.models import Chip
from chips.queries import chips_operacionais, _calcular_ciclo

class Command(BaseCommand):
    help = 'Verifica e cancela chips cuja data de recarga expirou (> 90 dias sem recarga)'

    def handle(self, *args, **options):
        chips = chips_operacionais()
        count = 0
        
        for chip in chips:
            recharge_due_at, days_to_recharge, status = _calcular_ciclo(chip)
            
            if status == 'overdue':
                # Altera o status para Cancelado. 
                # A lógica em Chip.save() preserva usage_status = IN_USE e o titular.
                chip.status = Chip.StatusChoices.CANCELED
                chip.save()
                count += 1
                self.stdout.write(f'Chip {chip.line_number} cancelado (vencido em {recharge_due_at})')
                
        self.stdout.write(self.style.SUCCESS(f'Concluído. {count} chips cancelados por vencimento.'))
