from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q

from core.models import CustomUser, Equipe


class EquipeForm(forms.ModelForm):
    """Formulário de criação e edição de equipes."""

    class Meta:
        model = Equipe
        fields = ('name', 'is_active')


class CustomUserCreateForm(UserCreationForm):
    """Formulário de criação de usuário (apenas ADMIN via gestão de usuários)."""

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'equipe', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['equipe'].queryset = Equipe.objects.filter(is_active=True).order_by('name')
        self.fields['equipe'].required = False
        self.fields['equipe'].empty_label = 'Sem equipe'


class CustomUserUpdateForm(forms.ModelForm):
    """Formulário de edição; senha é opcional."""

    nova_senha = forms.CharField(
        required=False,
        widget=forms.PasswordInput(render_value=False),
        label='Nova senha',
        help_text='Deixe em branco para manter a senha atual.',
    )

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'equipe', 'is_active')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['equipe'].queryset = Equipe.objects.filter(is_active=True).order_by('name')
        self.fields['equipe'].required = False
        self.fields['equipe'].empty_label = 'Sem equipe'
        if self.instance and self.instance.equipe_id and not self.instance.equipe.is_active:
            self.fields['equipe'].queryset = Equipe.objects.filter(
                Q(is_active=True) | Q(pk=self.instance.equipe_id)
            ).order_by('name')

    def save(self, commit=True):
        usuario = super().save(commit=False)
        senha = self.cleaned_data.get('nova_senha')
        if senha:
            usuario.set_password(senha)
        if commit:
            usuario.save()
        return usuario
