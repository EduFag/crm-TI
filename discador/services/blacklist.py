from django.utils import timezone
from django.db.models import Q
from ..models import RegraReciclagem, Blacklist
from ..utils.phones import normalizar_telefone, normalizar_cpf
from datetime import timedelta

class BlacklistService:
    @staticmethod
    def atualizar_blacklist(ligacoes: list):
        """
        Recebe uma lista de ligações da API e atualiza a blacklist
        de acordo com as regras de reciclagem ativas.
        """
        regras = RegraReciclagem.objects.filter(is_active=True).order_by('-prioridade')
        
        # Mapear regras para facilitar a busca
        regras_map = {}
        for r in regras:
            regras_map[r.qualificacao] = r

        for ligacao in ligacoes:
            qualificacao = ligacao.get('qualificacao')
            regra = regras_map.get(qualificacao)

            if not regra or regra.acao != 'bloquear':
                continue

            telefone = normalizar_telefone(ligacao.get('telefone'))
            cpf = normalizar_cpf(ligacao.get('cpf', ''))
            
            # TODO: Obter datetime correto baseado na ligação
            agora = timezone.now()
            bloqueado_ate = None
            if regra.tipo_bloqueio == 'temporario':
                bloqueado_ate = agora + timedelta(days=regra.dias_bloqueio)

            # Evitar substituir bloqueio permanente por temporário
            existente = Blacklist.objects.filter(telefone_normalizado=telefone, is_active=True).first()
            if existente and existente.tipo_bloqueio == 'permanente':
                continue

            Blacklist.objects.update_or_create(
                telefone_normalizado=telefone,
                defaults={
                    'telefone_original': ligacao.get('telefone'),
                    'cpf': cpf,
                    'qualificacao_origem': qualificacao,
                    'campanha_id': ligacao.get('campanha_id'),
                    'campanha_nome': ligacao.get('campanha_nome'),
                    'call_id': ligacao.get('call_id'),
                    'data_ligacao': ligacao.get('data_ligacao') or agora,
                    'tipo_bloqueio': regra.tipo_bloqueio,
                    'bloqueado_em': agora,
                    'bloqueado_ate': bloqueado_ate,
                    'origem': 'api',
                    'is_active': True,
                    'payload_original': ligacao.get('payload_original', {})
                }
            )

    @staticmethod
    def is_bloqueado(telefone: str, cpf: str = None) -> bool:
        """
        Verifica se um telefone ou CPF está na blacklist ativa.
        Considera a validade do bloqueio temporário.
        """
        telefone_norm = normalizar_telefone(telefone)
        cpf_norm = normalizar_cpf(cpf) if cpf else None

        agora = timezone.now()
        
        query = Blacklist.objects.filter(is_active=True)
        
        if cpf_norm:
            query = query.filter(Q(telefone_normalizado=telefone_norm) | Q(cpf=cpf_norm))
        else:
            query = query.filter(telefone_normalizado=telefone_norm)

        for bloqueio in query:
            if bloqueio.tipo_bloqueio == 'permanente':
                return True
            if bloqueio.bloqueado_ate and bloqueio.bloqueado_ate >= agora:
                return True
                
        return False
