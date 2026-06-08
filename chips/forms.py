from django import forms

from core.models import CustomUser
from chips.models import Batch, Chip, Operator


INPUT_CLASS = (
    'w-full text-sm p-2.5 border border-slate-300 rounded-lg '
    'focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50'
)
SELECT_CLASS = (
    'w-full text-sm p-2.5 border border-slate-300 rounded-lg '
    'focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50'
)


class TipoTitularFormMixin(forms.Form):
    """Mixin com radio nome livre / usuário do sistema (padrão helpdesk).

    Precisa herdar forms.Form para o metaclass remover os campos da classe
    e o template receber BoundField (iterável) em vez do ChoiceField cru.
    """

    TIPO_TEXTO = 'texto'
    TIPO_USUARIO = 'usuario'

    tipo_titular = forms.ChoiceField(
        choices=[
            (TIPO_TEXTO, 'Nome livre'),
            (TIPO_USUARIO, 'Usuário do sistema'),
        ],
        initial=TIPO_TEXTO,
        widget=forms.RadioSelect,
        label='Tipo de titular',
    )
    employee_name = forms.CharField(
        required=False,
        max_length=150,
        label='Nome do titular',
        widget=forms.TextInput(attrs={
            'placeholder': 'Nome de quem está usando o chip',
            'class': INPUT_CLASS,
        }),
    )
    employee_user = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(is_active=True).order_by(
            'first_name', 'last_name', 'username'
        ),
        required=False,
        label='Usuário titular',
        empty_label='Selecione um usuário',
        widget=forms.Select(attrs={'class': SELECT_CLASS}),
    )

    def clean_titular(self):
        """Retorna (employee_name, employee_user) validados."""
        cleaned = self.cleaned_data
        tipo = cleaned.get('tipo_titular', self.TIPO_TEXTO)
        employee_name = (cleaned.get('employee_name') or '').strip()
        employee_user = cleaned.get('employee_user')

        if tipo == self.TIPO_USUARIO:
            if not employee_user:
                self.add_error('employee_user', 'Selecione um usuário do sistema.')
                return None, None
            nome = employee_user.get_full_name() or employee_user.username
            return nome, employee_user

        if not employee_name:
            self.add_error('employee_name', 'Informe o nome do titular.')
            return None, None
        return employee_name, None


class AssignmentForm(TipoTitularFormMixin):
    chip_id = forms.IntegerField(label='Chip', widget=forms.HiddenInput())

    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned
        nome, usuario = self.clean_titular()
        if nome:
            cleaned['employee_name'] = nome
            cleaned['employee_user'] = usuario
        return cleaned


class TransferForm(TipoTitularFormMixin):
    def clean(self):
        cleaned = super().clean()
        if self.errors:
            return cleaned
        nome, usuario = self.clean_titular()
        if nome:
            cleaned['employee_name'] = nome
            cleaned['employee_user'] = usuario
        return cleaned


class ReturnToTiForm(forms.Form):
    envelope = forms.ModelChoiceField(
        queryset=Batch.objects.filter(
            tipo=Batch.TipoChoices.ENVELOPE,
            status=Batch.StatusChoices.OPEN,
        ).order_by('identifier'),
        label='Envelope na TI',
        empty_label='Selecione o envelope',
        widget=forms.Select(attrs={'class': SELECT_CLASS}),
    )


class ChipGridCreateForm(forms.Form):
    line_number = forms.CharField(max_length=20, label='Número da linha')
    operator = forms.ModelChoiceField(
        queryset=Operator.objects.filter(status=Operator.StatusChoices.ACTIVE),
        label='Operadora',
    )
    custody = forms.ChoiceField(
        choices=Chip.CustodyChoices.choices,
        initial=Chip.CustodyChoices.WITH_PERSON,
        label='Custódia',
    )
    tipo_titular = forms.ChoiceField(
        choices=[
            (TipoTitularFormMixin.TIPO_TEXTO, 'Nome livre'),
            (TipoTitularFormMixin.TIPO_USUARIO, 'Usuário do sistema'),
        ],
        initial=TipoTitularFormMixin.TIPO_TEXTO,
        required=False,
    )
    employee_name = forms.CharField(required=False, max_length=150)
    employee_user = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(is_active=True),
        required=False,
    )
    activated_at = forms.DateField(required=False)
    batch = forms.ModelChoiceField(
        queryset=Batch.objects.filter(
            tipo=Batch.TipoChoices.ENVELOPE,
            status=Batch.StatusChoices.OPEN,
        ),
        required=False,
    )

    def clean(self):
        cleaned = super().clean()
        custody = cleaned.get('custody')
        if custody == Chip.CustodyChoices.WITH_PERSON:
            tipo = cleaned.get('tipo_titular', TipoTitularFormMixin.TIPO_TEXTO)
            if tipo == TipoTitularFormMixin.TIPO_USUARIO:
                user = cleaned.get('employee_user')
                if not user:
                    self.add_error('employee_user', 'Selecione o titular.')
                else:
                    cleaned['employee_name'] = user.get_full_name() or user.username
            elif not (cleaned.get('employee_name') or '').strip():
                self.add_error('employee_name', 'Informe o titular.')
        elif custody == Chip.CustodyChoices.WITH_TI:
            if not cleaned.get('batch'):
                self.add_error('batch', 'Selecione o envelope na TI.')
        return cleaned
