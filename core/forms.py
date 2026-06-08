from django import forms
from django.contrib.auth.forms import UserCreationForm

from core.models import CustomUser


class CustomUserCreateForm(UserCreationForm):
    """Formulário de criação de usuário (apenas ADMIN via gestão de usuários)."""

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'is_active')


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
        fields = ('username', 'email', 'first_name', 'last_name', 'role', 'is_active')

    def save(self, commit=True):
        usuario = super().save(commit=False)
        senha = self.cleaned_data.get('nova_senha')
        if senha:
            usuario.set_password(senha)
        if commit:
            usuario.save()
        return usuario
