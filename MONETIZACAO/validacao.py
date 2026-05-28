import re


def validar_cpf(cpf: str) -> bool:
    cpf = re.sub(r'\D', '', cpf)
    if len(cpf) != 11 or len(set(cpf)) == 1:
        return False
    for i in range(9, 11):
        soma = sum(int(cpf[j]) * (i + 1 - j) for j in range(i))
        digito = (soma * 10) % 11
        if digito == 10:
            digito = 0
        if digito != int(cpf[i]):
            return False
    return True


def validar_cnpj(cnpj: str) -> bool:
    cnpj = re.sub(r'\D', '', cnpj)
    if len(cnpj) != 14 or len(set(cnpj)) == 1:
        return False
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    pesos2 = [6] + pesos1
    for pesos, pos in [(pesos1, 12), (pesos2, 13)]:
        soma = sum(int(cnpj[i]) * pesos[i] for i in range(pos))
        r = soma % 11
        d = 0 if r < 2 else 11 - r
        if d != int(cnpj[pos]):
            return False
    return True


def validar_cpf_cnpj(valor: str) -> bool:
    digits = re.sub(r'\D', '', valor)
    if len(digits) == 11:
        return validar_cpf(digits)
    if len(digits) == 14:
        return validar_cnpj(digits)
    return False
