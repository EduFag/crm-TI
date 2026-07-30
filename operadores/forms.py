from django import forms
from core.models import Equipe
from .models import Operador, WhatsAppAccount, PA, Ilha
from chips.models import Chip

class PABatchForm(forms.Form):
    equipe = forms.ModelChoiceField(
        queryset=Equipe.objects.filter(is_active=True).order_by('name'),
        label="Setor / Equipe",
        help_text="Selecione a equipe/setor (puxado do módulo de Equipes)."
    )
    num_ilhas = forms.IntegerField(
        min_value=1,
        initial=1,
        label="Quantidade de Ilhas",
        help_text="Número de ilhas a serem criadas (ex: 2)."
    )
    pas_per_ilha = forms.IntegerField(
        min_value=1,
        initial=10,
        label="PAs por Ilha",
        help_text="Quantidade de PAs em cada ilha (ex: 10)."
    )
    ilha_prefix = forms.CharField(
        max_length=50,
        initial="Ilha",
        label="Prefixo do Nome das Ilhas",
        help_text="Ex: 'Ilha' gerará 'Ilha 01', 'Ilha 02'..."
    )
    pa_prefix = forms.CharField(
        max_length=50,
        initial="PA",
        label="Prefixo do Nome das PAs",
        help_text="Ex: 'PA' gerará 'PA 01', 'PA 02'..."
    )

class PAForm(forms.ModelForm):
    class Meta:
        model = PA
        fields = ['name', 'ilha']
        labels = {
            'name': 'Nome da PA',
            'ilha': 'Ilha',
        }

INPUT_CLASS = (
    'w-full text-sm p-2.5 border border-slate-300 rounded-lg '
    'focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50'
)
SELECT_CLASS = (
    'w-full text-sm p-2.5 border border-slate-300 rounded-lg '
    'focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50'
)

class IlhaForm(forms.ModelForm):
    class Meta:
        model = Ilha
        fields = ['name', 'setor']
        labels = {
            'name': 'Nome da Ilha',
            'setor': 'Setor / Equipe',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'setor': forms.Select(attrs={'class': SELECT_CLASS}),
        }

class OperadorForm(forms.ModelForm):
    class Meta:
        model = Operador
        fields = ['name', 'pa']
        labels = {
            'name': 'Nome do Funcionário / Operador',
            'pa': 'Posição de Atendimento (PA)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = PA.objects.filter(operador__isnull=True)
        if self.instance and self.instance.pk and self.instance.pa:
            queryset = queryset | PA.objects.filter(pk=self.instance.pa.pk)
        self.fields['pa'].queryset = queryset.order_by('ilha__name', 'name')

class WhatsAppAccountForm(forms.ModelForm):
    class Meta:
        model = WhatsAppAccount
        fields = ['chip', 'account_type', 'status', 'operador']
        labels = {
            'chip': 'Linha Vinculada (Chip)',
            'account_type': 'Tipo de Conta WhatsApp',
            'status': 'Status da Conta',
            'operador': 'Funcionário / Operador',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        operador_id = self.initial.get('operador') or (self.data.get('operador') if self.is_bound else None)
        if self.instance and self.instance.pk and self.instance.operador_id:
            operador_id = self.instance.operador_id

        from django.db.models import Q, OuterRef, Subquery
        from chips.models import ChipMovement

        ultima_mov = ChipMovement.objects.filter(
            chip=OuterRef('pk'),
            action__in=[ChipMovement.ActionChoices.DELIVERY, ChipMovement.ActionChoices.TRANSFER]
        ).order_by('-timestamp')

        qs = Chip.objects.filter(is_active=True).annotate(
            current_operador_id=Subquery(ultima_mov.values('employee_operador_id')[:1])
        )

        q_filter = Q(usage_status=Chip.UsageChoices.AVAILABLE)
        if operador_id:
            q_filter |= Q(current_operador_id=operador_id)

        if self.instance and self.instance.pk and self.instance.chip_id:
            q_filter |= Q(pk=self.instance.chip_id)

        self.fields['chip'].queryset = qs.filter(q_filter).distinct().order_by('line_number')
        self.fields['chip'].required = True

    def clean(self):
        cleaned_data = super().clean()
        chip = cleaned_data.get('chip')
        operador = cleaned_data.get('operador')
        account_type = cleaned_data.get('account_type')

        if not chip:
            raise forms.ValidationError("Selecione uma Linha Vinculada (Chip) para esta conta WhatsApp.")

        if chip:
            cleaned_data['phone_number'] = chip.line_number

        if operador and account_type:
            qs = WhatsAppAccount.objects.filter(operador=operador)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.count() >= 2:
                raise forms.ValidationError(f"O operador '{operador.name}' já possui o limite máximo de 2 contas WhatsApp vinculadas.")

            if qs.filter(account_type=account_type).exists():
                type_display = dict(WhatsAppAccount.AccountTypeChoices.choices).get(account_type, account_type)
                raise forms.ValidationError(f"O operador '{operador.name}' já possui uma conta '{type_display}' vinculada. É permitido no máximo 1 conta Business e 1 conta Normal por operador.")

        return cleaned_data

class AlocarOperadorForm(forms.Form):
    operador = forms.ModelChoiceField(
        queryset=Operador.objects.all(),
        label="Selecione o Operador",
        help_text="Escolha um operador cadastrado na aba de Operadores.",
    )

    def __init__(self, *args, **kwargs):
        pa = kwargs.pop('pa', None)
        super().__init__(*args, **kwargs)
        self.fields['operador'].queryset = Operador.objects.select_related('pa', 'pa__ilha', 'pa__ilha__setor').all().order_by('name')
        
        self.fields['operador'].label_from_instance = lambda obj: (
            f"{obj.name} (Disponível / Sem PA)" if not obj.pa else
            (f"{obj.name} (Atual nesta PA)" if pa and obj.pa.pk == pa.pk else
             f"{obj.name} (Alocado em: {obj.pa.ilha.setor.name} - {obj.pa.name})")
        )
