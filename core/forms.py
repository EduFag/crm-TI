from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.password_validation import validate_password
from django.db.models import Q

from core.models import CustomUser, Equipe


class EquipeForm(forms.ModelForm):
    """Formulário de criação e edição de equipes."""

    class Meta:
        model = Equipe
        fields = ('name', 'is_active')
        labels = {
            'name': 'Nome da Equipe',
            'is_active': 'Ativa',
        }


class CustomUserCreateForm(UserCreationForm):
    """Formulário de criação de usuário (gestão de usuários / IT_USER e superuser)."""

    equipes = forms.ModelMultipleChoiceField(
        queryset=Equipe.objects.none(),
        widget=forms.CheckboxSelectMultiple(),
        required=False,
        label='Equipes',
        help_text='Equipes do usuário (opcional; atribuída pelo administrador).'
    )

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'equipes', 'is_active')
        labels = {
            'username': 'Nome de Usuário',
            'email': 'E-mail',
            'first_name': 'Nome',
            'last_name': 'Sobrenome',
            'role': 'Tipo de Usuário',
            'is_active': 'Ativo',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['equipes'].queryset = Equipe.objects.filter(is_active=True).order_by('name')
        # Labels em pt-br para os campos de senha herdados do UserCreationForm
        self.fields['password1'].label = 'Senha'
        self.fields['password2'].label = 'Confirmação de senha'
        # Modal HTMX: autofocus nativo conflita com a busca já focada na listagem
        self.fields['username'].widget.attrs.pop('autofocus', None)



class CustomUserUpdateForm(forms.ModelForm):
    """Formulário de edição; senha é opcional."""

    nova_senha = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        label='Nova senha',
        help_text='Deixe em branco para manter a senha atual.',
    )

    equipes = forms.ModelMultipleChoiceField(
        queryset=Equipe.objects.none(),
        widget=forms.CheckboxSelectMultiple(),
        required=False,
        label='Equipes',
        help_text='Equipes do usuário (opcional; atribuída pelo administrador).'
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'equipes', 'is_active')
        labels = {
            'username': 'Nome de Usuário',
            'email': 'E-mail',
            'first_name': 'Nome',
            'last_name': 'Sobrenome',
            'role': 'Tipo de Usuário',
            'is_active': 'Ativo',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['equipes'].queryset = Equipe.objects.filter(is_active=True).order_by('name')
        
        if self.instance and self.instance.pk:
            inativas_vinculadas = self.instance.equipes.filter(is_active=False)
            if inativas_vinculadas.exists():
                self.fields['equipes'].queryset = Equipe.objects.filter(
                    Q(is_active=True) | Q(pk__in=inativas_vinculadas)
                ).distinct().order_by('name')

    def clean_nova_senha(self):
        senha = self.cleaned_data.get('nova_senha') or ''
        if senha:
            # Reutiliza as regras de senha do Django (mesmas do cadastro)
            validate_password(senha, self.instance)
        return senha

    def save(self, commit=True):
        usuario = super().save(commit=False)
        senha = self.cleaned_data.get('nova_senha')
        if senha:
            usuario.set_password(senha)
        if commit:
            usuario.save()
            self.save_m2m()
        return usuario

