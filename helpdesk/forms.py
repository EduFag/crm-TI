from django import forms

from core.models import CustomUser
from helpdesk.models import Ticket, TicketCategory


class TicketCreateForm(forms.ModelForm):
    """Formulário de criação de chamado com solicitante por texto ou usuário do sistema."""

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
            'class': 'w-full text-sm p-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-slate-50 focus:bg-white transition-colors',
        }),
    )
    requester_user = forms.ModelChoiceField(
        queryset=CustomUser.objects.filter(is_active=True).order_by('first_name', 'last_name', 'username'),
        required=False,
        label='Usuário solicitante',
        empty_label='Selecione um usuário',
        widget=forms.Select(attrs={
            'class': 'w-full text-sm p-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50 focus:bg-white transition-colors',
        }),
    )

    class Meta:
        model = Ticket
        fields = ['title', 'description', 'priority', 'category']
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Resumo curto da solicitação',
                'class': 'w-full text-sm p-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 bg-slate-50 focus:bg-white transition-colors',
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Descreva o cenário, erros apresentados, prints...',
                'class': 'w-full text-sm p-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50 focus:bg-white transition-colors resize-y',
            }),
            'priority': forms.Select(attrs={
                'class': 'w-full text-sm p-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50 focus:bg-white transition-colors',
            }),
            'category': forms.Select(attrs={
                'class': 'w-full text-sm p-2.5 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-slate-50 focus:bg-white transition-colors',
            }),
        }

    def __init__(self, *args, **kwargs):
        nome_padrao = kwargs.pop('nome_solicitante_padrao', '')
        categoria_inicial = kwargs.pop('categoria_inicial', None)
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = TicketCategory.objects.filter(is_active=True).order_by('name')
        if not self.is_bound and nome_padrao:
            self.fields['requester_name'].initial = nome_padrao
        if not self.is_bound:
            if categoria_inicial:
                self.fields['category'].initial = categoria_inicial
            else:
                padrao = TicketCategory.objects.filter(is_active=True, name__iexact='Outros').first()
                if padrao:
                    self.fields['category'].initial = padrao.pk
        self.fields['requester_user'].label_from_instance = self._rotulo_usuario

    @staticmethod
    def _rotulo_usuario(usuario):
        nome = usuario.get_full_name().strip()
        if nome:
            return f'{nome} ({usuario.username})'
        return usuario.username

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

    def save(self, commit=True, created_by=None):
        ticket = super().save(commit=False)
        ticket.requester_name = self.cleaned_data['requester_name']
        ticket.requester_user = self.cleaned_data.get('requester_user')
        if created_by is not None:
            ticket.created_by = created_by
        if commit:
            ticket.save()
        return ticket
