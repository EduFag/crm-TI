import csv
import io
from django.core.files.base import ContentFile
from django.utils import timezone
from .blacklist import BlacklistService
from ..utils.phones import normalizar_telefone, normalizar_cpf

class CsvProcessorService:
    @staticmethod
    def processar(processamento):
        """
        Lê o CSV, aplica blacklist, remove duplicados e salva 2 novos arquivos (reciclado e bloqueados).
        """
        processamento.status = 'Em Processamento'
        processamento.save()

        try:
            # Lendo arquivo original
            processamento.arquivo_original.open(mode='rb')
            linhas = processamento.arquivo_original.read().decode('utf-8', errors='replace').splitlines()
            processamento.arquivo_original.close()

            if not linhas:
                raise ValueError("Arquivo CSV vazio.")

            reader = csv.DictReader(linhas, delimiter=';')
            # Fallback para vírgula
            if not reader.fieldnames or len(reader.fieldnames) == 1:
                reader = csv.DictReader(linhas, delimiter=',')

            if not reader.fieldnames:
                raise ValueError("Formato CSV inválido ou não foi possível identificar as colunas.")

            # Normaliza os nomes das colunas (remover espaços, lower)
            colunas_originais = reader.fieldnames
            col_telefone = processamento.coluna_telefone
            col_cpf = processamento.coluna_cpf

            # TODO: validar se as colunas existem
            
            liberados = []
            bloqueados = []
            telefones_processados = set()

            total_duplicadas = 0
            
            # Adicionando colunas extras no bloqueados
            colunas_bloqueados = list(colunas_originais) + [
                'motivo_bloqueio', 'qualificacao_origem', 'bloqueado_ate', 'tipo_bloqueio', 'campanha_origem'
            ]

            for row in reader:
                tel = row.get(col_telefone, '')
                cpf = row.get(col_cpf, '') if col_cpf else ''

                tel_norm = normalizar_telefone(tel)
                cpf_norm = normalizar_cpf(cpf)

                # Remoção de duplicados na própria base
                # Se o usuário marcou para remover duplicados (isso seria pego do forms, vamos assumir que queremos limpar)
                # O ideal era passar as flags para este service. Vamos considerar sempre limpar pra base
                if tel_norm in telefones_processados:
                    total_duplicadas += 1
                    continue
                if tel_norm:
                    telefones_processados.add(tel_norm)

                # Verifica blacklist
                # TODO: Otimizar para evitar N queries no banco. Carregar blacklist em memória se a base for gigante.
                if BlacklistService.is_bloqueado(tel_norm, cpf_norm):
                    # Aqui poderiamos buscar qual regra bloqueou, mas vamos simplificar no MVP
                    row['motivo_bloqueio'] = 'Na Blacklist'
                    row['qualificacao_origem'] = 'Desconhecida'
                    row['bloqueado_ate'] = ''
                    row['tipo_bloqueio'] = 'permanente'
                    row['campanha_origem'] = ''
                    bloqueados.append(row)
                else:
                    liberados.append(row)

            # Criar arquivos de saída
            reciclado_io = io.StringIO()
            writer_reciclado = csv.DictWriter(reciclado_io, fieldnames=colunas_originais, delimiter=';')
            writer_reciclado.writeheader()
            writer_reciclado.writerows(liberados)

            bloqueados_io = io.StringIO()
            writer_bloqueados = csv.DictWriter(bloqueados_io, fieldnames=colunas_bloqueados, delimiter=';')
            writer_bloqueados.writeheader()
            writer_bloqueados.writerows(bloqueados)

            # Salvar no BD
            nome_base = processamento.arquivo_original.name.split('/')[-1]
            
            processamento.arquivo_reciclado.save(
                f'reciclado_{nome_base}', 
                ContentFile(reciclado_io.getvalue().encode('utf-8'))
            )
            
            processamento.arquivo_bloqueados.save(
                f'bloqueados_{nome_base}', 
                ContentFile(bloqueados_io.getvalue().encode('utf-8'))
            )

            processamento.total_linhas = len(linhas) - 1
            processamento.total_liberadas = len(liberados)
            processamento.total_bloqueadas = len(bloqueados)
            processamento.total_duplicadas = total_duplicadas
            processamento.status = 'Concluído'
            processamento.finalizado_em = timezone.now()
            processamento.save()

        except Exception as e:
            processamento.status = 'Erro'
            processamento.log = str(e)
            processamento.finalizado_em = timezone.now()
            processamento.save()
            raise e
