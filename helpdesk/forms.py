from django import forms

from core.models import CustomUser
from helpdesk.models import Ticket, TicketCategory
from helpdesk.ticket_access import (
    usuario_pode_definir_prioridade,
    usuarios_solicitantes_equipe,
    usuarios_tecnicos_para_transferencia,
)


INPUT_CLASS = 'w-full text-sm p-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-slate-50 focus:bg-white transition-colors'
SELECT_CLASS = 'w-full text-sm p-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50 focus:bg-white transition-colors'


class TicketCreateForm(forms.ModelForm):
    """Formulário de criação de chamado com campos condicionais por papel do usuário."""

    TIPO_TEXTO = 'texto'
    TIPO_USUARIO = 'usuario'

    tipo_solicitante = forms.ChoiceField(
        choices=[
            (TIPO_TEXTO, 'Nome livre'),
            (TIPO_USUARIO, 'Usuário do sistema'),
        ],
        initial=TIPO_TEXTO,
        widget=forms.RadioSelect,
        label='Tipo de solicitante',
    )
    requester_name = forms.CharField(
        required=False,
        max_length=150,
        label='Nome do solicitante',
        widget=forms.TextInput(attrs={
            'placeholder': 'Nome de quem solicita o chamado',
            'class': INPUT_CLASS,
        }),
    )
    requester_user = forms.ModelChoiceField(
        queryset=CustomUser.objects.none(),
        required=False,
        label='Usuário solicitante',
        empty_label='Selecione um usuário',
        widget=forms.Select(attrs={'class': SELECT_CLASS}),
    )

    class Meta:
        model = Ticket
        fields = ['title', 'description', 'priority', 'category']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Resumo curto da solicitação',
                'class': INPUT_CLASS,
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Descreva o cenário, erros apresentados, prints...',
                'class': INPUT_CLASS + ' resize-y',
            }),
            'priority': forms.Select(attrs={'class': SELECT_CLASS}),
            'category': forms.Select(attrs={'class': SELECT_CLASS}),
        }

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        nome_padrao = kwargs.pop('nome_solicitante_padrao', '')
        categoria_inicial = kwargs.pop('categoria_inicial', None)
        super().__init__(*args, **kwargs)

        self.fields['category'].queryset = TicketCategory.objects.filter(is_active=True).order_by('name')
        if not self.is_bound and categoria_inicial:
            self.fields['category'].initial = categoria_inicial
        elif not self.is_bound:
            padrao = TicketCategory.objects.filter(is_active=True, name__iexact='Outros').first()
            if padrao:
                self.fields['category'].initial = padrao.pk

        self._configurar_por_papel(nome_padrao)

    def _configurar_por_papel(self, nome_padrao):
        if not self.user:
            return

        role = getattr(self.user, 'role', CustomUser.RoleChoices.USER)
        if self.user.is_superuser:
            role = CustomUser.RoleChoices.ADMIN

        if role == CustomUser.RoleChoices.USER:
            self._remover_campo('tipo_solicitante')
            self._remover_campo('requester_name')
            self._remover_campo('requester_user')
            self._remover_campo('priority')
            return

        if role == CustomUser.RoleChoices.MANAGER:
            self._remover_campo('priority')
            self.fields['requester_user'].queryset = usuarios_solicitantes_equipe(self.user)
            self.fields['requester_user'].label_from_instance = self._rotulo_usuario
            if not self.is_bound and nome_padrao:
                self.fields['requester_name'].initial = nome_padrao
            if not self.user.equipe_id:
                self._remover_campo('tipo_solicitante')
                self._remover_campo('requester_user')
            return

        # ADMIN ou superuser
        self.fields['requester_user'].queryset = CustomUser.objects.filter(
            is_active=True,
        ).order_by('first_name', 'last_name', 'username')
        self.fields['requester_user'].label_from_instance = self._rotulo_usuario
        if not self.is_bound and nome_padrao:
            self.fields['requester_name'].initial = nome_padrao
        if not usuario_pode_definir_prioridade(self.user):
            self._remover_campo('priority')
        else:
            self.fields['priority'].required = False
            self.fields['priority'].empty_label = 'Sem prioridade (triagem posterior)'

    def _remover_campo(self, nome):
        if nome in self.fields:
            del self.fields[nome]

    @staticmethod
    def _rotulo_usuario(usuario):
        nome = usuario.get_full_name().strip()
        if nome:
            return f'{nome} ({usuario.username})'
        return usuario.username

    def clean(self):
        cleaned = super().clean()
        role = getattr(self.user, 'role', CustomUser.RoleChoices.USER)

        if role == CustomUser.RoleChoices.USER and not self.user.is_superuser:
            cleaned['requester_name'] = self.user.get_full_name() or self.user.username
            cleaned['requester_user'] = self.user
            cleaned['priority'] = None
            return cleaned

        if role == CustomUser.RoleChoices.MANAGER:
            cleaned['priority'] = None
            if not self.user.equipe_id:
                requester_name = (cleaned.get('requester_name') or '').strip()
                if not requester_name:
                    self.add_error('requester_name', 'Informe o nome do solicitante.')
                else:
                    cleaned['requester_name'] = requester_name
                    cleaned['requester_user'] = None
                return cleaned

        tipo = cleaned.get('tipo_solicitante')
        requester_name = (cleaned.get('requester_name') or '').strip()
        requester_user = cleaned.get('requester_user')

        if tipo == self.TIPO_USUARIO:
            if not requester_user:
                self.add_error('requester_user', 'Selecione um usuário do sistema.')
            else:
                cleaned['requester_name'] = (
                    requester_user.get_full_name() or requester_user.username
                )
                cleaned['requester_user'] = requester_user
        else:
            if not requester_name:
                self.add_error('requester_name', 'Informe o nome do solicitante.')
            else:
                cleaned['requester_name'] = requester_name
                cleaned['requester_user'] = None

        if not usuario_pode_definir_prioridade(self.user):
            cleaned['priority'] = None

        return cleaned

    def save(self, commit=True, created_by=None):
        ticket = super().save(commit=False)
        ticket.requester_name = self.cleaned_data['requester_name']
        ticket.requester_user = self.cleaned_data.get('requester_user')
        if not usuario_pode_definir_prioridade(self.user):
            ticket.priority = None
        if created_by is not None:
            ticket.created_by = created_by
        if commit:
            ticket.save()
        return ticket


class TicketUpdateForm(forms.ModelForm):
    """Formulário de edição de chamado (somente ADMIN/superuser)."""

    TIPO_TEXTO = 'texto'
    TIPO_USUARIO = 'usuario'

    tipo_solicitante = forms.ChoiceField(
        choices=[
            (TIPO_TEXTO, 'Nome livre'),
            (TIPO_USUARIO, 'Usuário do sistema'),
        ],
        widget=forms.RadioSelect,
        label='Tipo de solicitante',
    )
    requester_name = forms.CharField(
        required=False,
        max_length=150,
        label='Nome do solicitante',
        widget=forms.TextInput(attrs={'class': INPUT_CLASS}),
    )
    requester_user = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(is_active=True).order_by('first_name', 'last_name', 'username'),
        required=False,
        label='Usuário solicitante',
        empty_label='Selecione um usuário',
        widget=forms.Select(attrs={'class': SELECT_CLASS}),
    )

    class Meta:
        model = Ticket
        fields = ['title', 'description', 'category', 'priority', 'status', 'assigned_to']
        widgets = {
            'title': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': INPUT_CLASS + ' resize-y'}),
            'category': forms.Select(attrs={'class': SELECT_CLASS}),
            'priority': forms.Select(attrs={'class': SELECT_CLASS}),
            'status': forms.Select(attrs={'class': SELECT_CLASS}),
            'assigned_to': forms.Select(attrs={'class': SELECT_CLASS}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = TicketCategory.objects.filter(is_active=True).order_by('name')
        self.fields['assigned_to'].queryset = usuarios_tecnicos_para_transferencia()
        self.fields['assigned_to'].required = False
        self.fields['assigned_to'].empty_label = 'Não atribuído'
        self.fields['priority'].required = False
        self.fields['priority'].empty_label = 'Sem prioridade'
        self.fields['requester_user'].label_from_instance = TicketCreateForm._rotulo_usuario

        if self.instance and self.instance.pk:
            if self.instance.requester_user_id:
                self.fields['tipo_solicitante'].initial = self.TIPO_USUARIO
                self.fields['requester_user'].initial = self.instance.requester_user_id
            else:
                self.fields['tipo_solicitante'].initial = self.TIPO_TEXTO
                self.fields['requester_name'].initial = self.instance.requester_name

    def clean(self):
        cleaned = super().clean()
        tipo = cleaned.get('tipo_solicitante')
        requester_name = (cleaned.get('requester_name') or '').strip()
        requester_user = cleaned.get('requester_user')

        if tipo == self.TIPO_USUARIO:
            if not requester_user:
                self.add_error('requester_user', 'Selecione um usuário do sistema.')
            else:
                cleaned['requester_name'] = (
                    requester_user.get_full_name() or requester_user.username
                )
                cleaned['requester_user'] = requester_user
        else:
            if not requester_name:
                self.add_error('requester_name', 'Informe o nome do solicitante.')
            else:
                cleaned['requester_name'] = requester_name
                cleaned['requester_user'] = None

        return cleaned

    def save(self, commit=True):
        ticket = super().save(commit=False)
        ticket.requester_name = self.cleaned_data['requester_name']
        ticket.requester_user = self.cleaned_data.get('requester_user')
        if commit:
            ticket.save()
        return ticket
