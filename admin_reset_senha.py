#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilitario de administracao — resetar senha de usuario
"""
import sys
import re
from MONETIZACAO.db import get_conn
from werkzeug.security import generate_password_hash

def validar_email(email):
    """Valida formato de email simples."""
    return re.match(r'^[^@]+@[^@]+\.[^@]+$', email)

def listar_usuarios():
    """Lista todos os usuarios do banco."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, cliente_nome, cliente_email, status FROM assinaturas ORDER BY id"
    ).fetchall()
    conn.close()
    
    if not rows:
        print("Nenhum usuario cadastrado.")
        return
    
    print("\n=== USUARIOS CADASTRADOS ===\n")
    for row in rows:
        print(f"ID {row[0]:2d} | {row[1]:20s} | {row[2]:25s} | {row[3]}")
    print()

def resetar_senha(email, nova_senha):
    """Reseta a senha de um usuario."""
    if not validar_email(email):
        print(f"Erro: Email invalido: {email}")
        return False
    
    if len(nova_senha) < 6:
        print("Erro: Senha deve ter no minimo 6 caracteres.")
        return False
    
    conn = get_conn()
    
    # Verifica se usuario existe
    row = conn.execute(
        "SELECT id, cliente_nome FROM assinaturas WHERE LOWER(cliente_email)=?",
        (email.lower(),)
    ).fetchone()
    
    if not row:
        print(f"Erro: Usuario com email '{email}' nao encontrado.")
        conn.close()
        return False
    
    # Hash da nova senha
    senha_hash = generate_password_hash(nova_senha)
    
    # Atualiza banco
    conn.execute(
        "UPDATE assinaturas SET cliente_senha_hash=? WHERE LOWER(cliente_email)=?",
        (senha_hash, email.lower())
    )
    conn.commit()
    conn.close()
    
    print(f"\nSucesso!")
    print(f"  Usuario: {row[1]}")
    print(f"  Email: {email}")
    print(f"  Nova senha: {nova_senha}")
    print("\nO usuario pode fazer login com estas credenciais.\n")
    return True

def main():
    if len(sys.argv) < 2:
        print("Uso: python admin_reset_senha.py [comando]")
        print("\nComandos:")
        print("  list                    — Listar todos os usuarios")
        print("  reset EMAIL SENHA       — Resetar senha de um usuario")
        print("\nExemplos:")
        print("  python admin_reset_senha.py list")
        print("  python admin_reset_senha.py reset maria@teste.com minhasenha123")
        print()
        return
    
    cmd = sys.argv[1].lower()
    
    if cmd == 'list':
        listar_usuarios()
    elif cmd == 'reset':
        if len(sys.argv) < 4:
            print("Uso: python admin_reset_senha.py reset EMAIL SENHA")
            print("Exemplo: python admin_reset_senha.py reset maria@teste.com minhasenha123")
            print()
            return
        email = sys.argv[2]
        senha = sys.argv[3]
        resetar_senha(email, senha)
    else:
        print(f"Comando desconhecido: {cmd}")
        print("Use 'list' ou 'reset'")
        print()

if __name__ == '__main__':
    main()
