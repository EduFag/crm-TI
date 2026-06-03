from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.utils import timezone
from .models import ConfiguracaoAPI, RegraReciclagem, Blacklist, ImportacaoAPI, ProcessamentoBase
from .forms import ConfiguracaoAPIForm, RegraReciclagemForm, AtualizarBlacklistForm, ProcessarBaseForm
from .services.api_3cplus import Api3CPlusService
from .services.blacklist import BlacklistService
from .services.csv_processor import CsvProcessorService

class DashboardView(LoginRequiredMixin, View):
    def get(self, request):
        total_blacklist = Blacklist.objects.filter(is_active=True).count()
        total_bases = ProcessamentoBase.objects.count()
        ultimas_bases = ProcessamentoBase.objects.order_by('-created_at')[:5]
        
        context = {
            'total_blacklist': total_blacklist,
            'total_bases': total_bases,
            'ultimas_bases': ultimas_bases,
        }
        return render(request, 'discador/dashboard.html', context)

class ConfiguracoesAPIView(LoginRequiredMixin, View):
    def get(self, request):
        config = ConfiguracaoAPI.objects.first()
        form = ConfiguracaoAPIForm(instance=config)
        return render(request, 'discador/configuracoes_api.html', {'form': form, 'config': config})

    def post(self, request):
        config = ConfiguracaoAPI.objects.first()
        form = ConfiguracaoAPIForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Configurações salvas com sucesso!')
            return redirect('discador:configuracoes_api')
        return render(request, 'discador/configuracoes_api.html', {'form': form, 'config': config})

class AtualizarBlacklistView(LoginRequiredMixin, View):
    def get(self, request):
        form = AtualizarBlacklistForm()
        return render(request, 'discador/atualizar_blacklist.html', {'form': form})

    def post(self, request):
        form = AtualizarBlacklistForm(request.POST)
        if form.is_valid():
            # TODO: Obter datas e chamar API
            # data_inicial = form.cleaned_data['data_inicial']
            # data_final = form.cleaned_data['data_final']
            api_service = Api3CPlusService()
            ligacoes = api_service.buscar_ligacoes("2023-01-01", "2023-12-31")
            
            BlacklistService.atualizar_blacklist(ligacoes)
            
            # TODO: Salvar registro em ImportacaoAPI
            messages.success(request, 'Blacklist atualizada com sucesso (simulação)!')
            return redirect('discador:blacklist_ativa')
        return render(request, 'discador/atualizar_blacklist.html', {'form': form})

class RegrasReciclagemView(LoginRequiredMixin, View):
    def get(self, request):
        regras = RegraReciclagem.objects.all().order_by('-prioridade')
        form = RegraReciclagemForm()
        return render(request, 'discador/regras_reciclagem.html', {'regras': regras, 'form': form})

    def post(self, request):
        form = RegraReciclagemForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Regra criada com sucesso!')
            return redirect('discador:regras_reciclagem')
        regras = RegraReciclagem.objects.all().order_by('-prioridade')
        return render(request, 'discador/regras_reciclagem.html', {'regras': regras, 'form': form})

class ReciclarBasesView(LoginRequiredMixin, View):
    def get(self, request):
        form = ProcessarBaseForm()
        return render(request, 'discador/reciclar_bases.html', {'form': form})

    def post(self, request):
        form = ProcessarBaseForm(request.POST, request.FILES)
        if form.is_valid():
            processamento = form.save(commit=False)
            processamento.criado_por = request.user
            processamento.status = 'Aguardando'
            processamento.save()
            
            # Executa o processamento sincrono no MVP (depois poderia ser async com Celery)
            CsvProcessorService.processar(processamento)
            
            messages.success(request, 'Base processada com sucesso!')
            return redirect('discador:historico_processamentos')
        return render(request, 'discador/reciclar_bases.html', {'form': form})

class BlacklistView(LoginRequiredMixin, View):
    def get(self, request):
        bloqueios = Blacklist.objects.all().order_by('-bloqueado_em')[:100]
        return render(request, 'discador/blacklist.html', {'bloqueios': bloqueios})

class ConsultaTelefoneView(LoginRequiredMixin, View):
    def get(self, request):
        telefone = request.GET.get('telefone')
        resultado = None
        if telefone:
            resultado = Blacklist.objects.filter(telefone_original__icontains=telefone).first()
            if not resultado:
                # normalizar para checar
                from .utils.phones import normalizar_telefone
                tel_norm = normalizar_telefone(telefone)
                resultado = Blacklist.objects.filter(telefone_normalizado=tel_norm).first()
                
        return render(request, 'discador/consulta_telefone.html', {'resultado': resultado, 'telefone': telefone})

class HistoricoImportacoesView(LoginRequiredMixin, View):
    def get(self, request):
        importacoes = ImportacaoAPI.objects.order_by('-created_at')[:50]
        return render(request, 'discador/historico_importacoes.html', {'importacoes': importacoes})

class HistoricoProcessamentosView(LoginRequiredMixin, View):
    def get(self, request):
        processamentos = ProcessamentoBase.objects.order_by('-created_at')[:50]
        return render(request, 'discador/historico_processamentos.html', {'processamentos': processamentos})
