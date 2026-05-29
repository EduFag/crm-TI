import re

def normalizar_telefone(telefone: str) -> str:
    """
    Normaliza um número de telefone para manter apenas números.
    Remove DDI 55 e zeros à esquerda desnecessários.
    Exemplo:
    +55 51 99999-9999 -> 51999999999
    (51) 99999-9999 -> 51999999999
    05551999999999 -> 51999999999
    """
    if not telefone:
        return ""
    
    # Remove caracteres não numéricos
    numero = re.sub(r'\D', '', str(telefone))
    
    # Remove DDI 55
    if numero.startswith('055'):
        numero = numero[3:]
    elif numero.startswith('55') and len(numero) > 11:
        numero = numero[2:]
        
    # Remove zero inicial (para DDDs que vêm como 051)
    if numero.startswith('0') and len(numero) > 10:
        numero = numero[1:]
        
    return numero

def normalizar_cpf(cpf: str) -> str:
    """Remove caracteres não numéricos do CPF."""
    if not cpf:
        return ""
    return re.sub(r'\D', '', str(cpf))
