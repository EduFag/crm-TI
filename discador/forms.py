from django import forms
from django.db.models import Q

from core.models import CustomUser
from discador.models import AcessoDiscador, Campanha, Discador, Ramal
from discador.services import get_or_create_joytec

INPUT_CLASS = (
    'w-full text-sm p-2.5 border border-slate-300 rounded-lg '
    'focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50'
)
SELECT_CLASS = (
    'w-full text-sm p-2.5 border border-slate-300 rounded-lg '
    'focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50'
)


class TipoTitularFormMixin(forms.Form):
    """Radio nome livre / usuário do sistema (padrão chips)."""

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
    titular_nome = forms.CharField(
        required=False,
        max_length=150,
        label='Nome do titular',
        widget=forms.TextInput(attrs={
            'placeholder': 'Nome de quem usa o discador',
            'class': INPUT_CLASS,
        }),
    )
    titular_user = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(is_active=True).order_by(
            'first_name', 'last_name', 'username'
        ),
        required=False,
        label='Usuário titular',
        empty_label='Selecione um usuário',
        widget=forms.Select(attrs={'class': SELECT_CLASS}),
    )

    def clean_titular(self):
        cleaned = self.cleaned_data
        tipo = cleaned.get('tipo_titular', self.TIPO_TEXTO)
        titular_nome = (cleaned.get('titular_nome') or '').strip()
        titular_user = cleaned.get('titular_user')

        if tipo == self.TIPO_USUARIO:
            if not titular_user:
                self.add_error('titular_user', 'Selecione um usuário do sistema.')
                return None, None
            nome = titular_user.get_full_name() or titular_user.username
            return nome, titular_user

        if not titular_nome:
            self.add_error('titular_nome', 'Informe o nome do titular.')
            return None, None
        return titular_nome, None


class RamalForm(forms.ModelForm):
    class Meta:
        model = Ramal
        fields = ['numero', 'status']
        widgets = {
            'numero': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Ex: 2750012'}),
            'status': forms.Select(attrs={'class': SELECT_CLASS}),
        }
        labels = {
            'numero': 'Número do ramal',
            'status': 'Status',
        }


class CampanhaForm(forms.ModelForm):
    class Meta:
        model = Campanha
        fields = ['nome', 'is_active']
        widgets = {
            'nome': forms.TextInput(attrs={'class': INPUT_CLASS, 'placeholder': 'Nome da campanha'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-slate-300'}),
        }
        labels = {
            'nome': 'Nome',
            'is_active': 'Campanha ativa',
        }


class ContratoForm(forms.ModelForm):
    observacao = forms.CharField(
        required=False,
        max_length=255,
        label='Observação (histórico)',
        widget=forms.TextInput(attrs={
            'class': INPUT_CLASS,
            'placeholder': 'Motivo da alteração (opcional)',
        }),
    )

    class Meta:
        model = Discador
        fields = ['valor_por_licenca', 'licencas_contratadas']
        widgets = {
            'valor_por_licenca': forms.NumberInput(attrs={
                'class': INPUT_CLASS,
                'step': '0.01',
                'min': '0',
            }),
            'licencas_contratadas': forms.NumberInput(attrs={
                'class': INPUT_CLASS,
                'min': '0',
            }),
        }
        labels = {
            'valor_por_licenca': 'Valor por licença (R$)',
            'licencas_contratadas': 'Licenças contratadas',
        }


class AcessoDiscadorForm(forms.ModelForm):
    """Form de acesso com titular dual (nome livre ou usuário do sistema)."""

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
    titular_nome = forms.CharField(
        required=False,
        max_length=150,
        label='Nome do titular',
        widget=forms.TextInput(attrs={
            'placeholder': 'Nome de quem usa o discador',
            'class': INPUT_CLASS,
        }),
    )
    titular_user = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(is_active=True).order_by(
            'first_name', 'last_name', 'username'
        ),
        required=False,
        label='Usuário titular',
        empty_label='Selecione um usuário',
        widget=forms.Select(attrs={'class': SELECT_CLASS}),
    )

    class Meta:
        model = AcessoDiscador
        fields = ['login_discador', 'ramal', 'campanha', 'tipo']
        widgets = {
            'login_discador': forms.TextInput(attrs={
                'class': INPUT_CLASS,
                'placeholder': 'Login no discador',
            }),
            'ramal': forms.Select(attrs={'class': SELECT_CLASS}),
            'campanha': forms.Select(attrs={'class': SELECT_CLASS}),
            'tipo': forms.Select(attrs={'class': SELECT_CLASS}),
        }
        labels = {
            'login_discador': 'Login do discador',
            'ramal': 'Ramal',
            'campanha': 'Campanha',
            'tipo': 'Tipo',
        }

    def __init__(self, *args, discador=None, **kwargs):
        self.discador = discador or get_or_create_joytec()
        super().__init__(*args, **kwargs)

        instance = self.instance if self.instance and self.instance.pk else None
        ramais_ocupados = AcessoDiscador.objects.filter(discador=self.discador)
        if instance:
            ramais_ocupados = ramais_ocupados.exclude(pk=instance.pk)
            if instance.titular_user_id:
                self.fields['tipo_titular'].initial = self.TIPO_USUARIO
            else:
                self.fields['tipo_titular'].initial = self.TIPO_TEXTO
            self.fields['titular_nome'].initial = instance.titular_nome
            self.fields['titular_user'].initial = instance.titular_user_id

        ocupados_ids = list(ramais_ocupados.values_list('ramal_id', flat=True))
        ramais_qs = Ramal.objects.filter(discador=self.discador).exclude(pk__in=ocupados_ids)
        if instance:
            ramais_qs = (
                Ramal.objects.filter(discador=self.discador, pk=instance.ramal_id)
                | ramais_qs
            ).distinct()

        self.fields['ramal'].queryset = ramais_qs.order_by('numero')
        self.fields['campanha'].queryset = Campanha.objects.filter(
            discador=self.discador,
            is_active=True,
        ).order_by('nome')
        if instance and instance.campanha_id:
            self.fields['campanha'].queryset = Campanha.objects.filter(
                discador=self.discador,
            ).filter(
                Q(is_active=True) | Q(pk=instance.campanha_id)
            ).order_by('nome')

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get('tipo_titular', self.TIPO_TEXTO)
        titular_nome = (cleaned.get('titular_nome') or '').strip()
        titular_user = cleaned.get('titular_user')

        if tipo == self.TIPO_USUARIO:
            if not titular_user:
                self.add_error('titular_user', 'Selecione um usuário do sistema.')
            else:
                cleaned['titular_nome'] = titular_user.get_full_name() or titular_user.username
                cleaned['titular_user'] = titular_user
        else:
            if not titular_nome:
                self.add_error('titular_nome', 'Informe o nome do titular.')
            else:
                cleaned['titular_nome'] = titular_nome
                cleaned['titular_user'] = None
        return cleaned
