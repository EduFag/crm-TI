from django import forms
from emails.models import EmailAccount, EmailDomain
from chips.models import Chip

INPUT_CLASS = (
    'w-full text-base p-3 border border-slate-300 rounded-lg '
    'focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none shadow-sm transition-all'
)
SELECT_CLASS = (
    'w-full text-base p-3 border border-slate-300 rounded-lg '
    'focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none shadow-sm font-medium text-slate-700 bg-white'
)


class EmailAccountForm(forms.ModelForm):
    chip = forms.ModelChoiceField(
        queryset=Chip.objects.select_related('operator').all().order_by('-created_at', '-id'),
        required=False,
        label="Linha Telefônica (Chip)",
        empty_label="-- Sem linha vinculada --",
        widget=forms.Select(attrs={'class': SELECT_CLASS, 'id': 'id_chip'})
    )

    class Meta:
        model = EmailAccount
        fields = ['username', 'domain', 'employee_name', 'password', 'status']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            current_chip = self.instance.chip
            if current_chip:
                self.fields['chip'].initial = current_chip.pk

    def save(self, commit=True):
        instance = super().save(commit=commit)
        if commit:
            self.save_chip_link(instance)
        return instance

    def save_chip_link(self, instance):
        selected_chip = self.cleaned_data.get('chip')
        previous_chip = instance.chip

        if previous_chip and previous_chip != selected_chip:
            previous_chip.email_vinculado = None
            previous_chip.save(update_fields=['email_vinculado'])

        if selected_chip:
            selected_chip.email_vinculado = instance
            selected_chip.save(update_fields=['email_vinculado'])
