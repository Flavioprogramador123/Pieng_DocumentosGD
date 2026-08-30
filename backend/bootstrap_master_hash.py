#!/usr/bin/env python3
"""
Gera MASTER_PASSWORD_HASH para colocar no .env (nunca commite a senha em texto plano).

Uso (local, uma vez):
  python bootstrap_master_hash.py
  python bootstrap_master_hash.py "SuaSenhaSegura"
"""

import getpass
import sys

from werkzeug.security import generate_password_hash


def main():
    if len(sys.argv) > 1:
        password = sys.argv[1]
    else:
        password = getpass.getpass('Senha master: ')
        confirm = getpass.getpass('Confirme: ')
        if password != confirm:
            print('Senhas não conferem.', file=sys.stderr)
            sys.exit(1)

    if len(password) < 8:
        print('Use pelo menos 8 caracteres.', file=sys.stderr)
        sys.exit(1)

    print('\nAdicione ao .env (raiz ou backend/.env):\n')
    print(f'MASTER_USERNAME=pieng')
    print(f'MASTER_PASSWORD_HASH={generate_password_hash(password)}')
    print('\nNunca commite a senha em texto plano — só o hash acima.')


if __name__ == '__main__':
    main()
