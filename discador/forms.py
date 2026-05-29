from django import forms
from .models import ConfiguracaoAPI, RegraReciclagem, ProcessamentoBase

class ConfiguracaoAPIForm(forms.ModelForm):
    class Meta:
        model = ConfiguracaoAPI
        fields = ['nome', 'base_url', 'api_token', 'campaign_ids', 'per_page', 'is_active']
        widgets = {
            'api_token': forms.PasswordInput(render_value=True),
        }

class RegraReciclagemForm(forms.ModelForm):
    class Meta:
        model = RegraReciclagem
        fields = ['qualificacao', 'acao', 'tipo_bloqueio', 'dias_bloqueio', 'aplicar_por_telefone', 'aplicar_por_cpf', 'campanha_id', 'prioridade', 'is_active']

class AtualizarBlacklistForm(forms.Form):
    data_inicial = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))
    data_final = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))
    campanhas = forms.CharField(required=False, help_text="Separadas por vírgula")
    somente_qualificadas = forms.BooleanField(required=False, initial=True)
    ignorar_importadas = forms.BooleanField(required=False, initial=True)

class ProcessarBaseForm(forms.ModelForm):
    remover_duplicados = forms.BooleanField(required=False, initial=True)
    aplicar_blacklist = forms.BooleanField(required=False, initial=True)
    considerar_expirados = forms.BooleanField(required=False, initial=False)
    gerar_csv_bloqueados = forms.BooleanField(required=False, initial=True)
    atualizar_blacklist_antes = forms.BooleanField(required=False, initial=False)

    class Meta:
        model = ProcessamentoBase
        fields = ['nome', 'campanha_destino', 'arquivo_original', 'coluna_telefone', 'coluna_cpf']
