"""
Rotas de autenticação e gestão de usuários secundários (somente master).
"""

from __future__ import annotations

import os
from datetime import timedelta

from flask import jsonify, request, session

from auth_store import (
    authenticate,
    create_secondary_user,
    delete_secondary_user,
    is_master_username,
    list_secondary_users,
    master_configured,
    MASTER_USERNAME,
    normalize_username,
    reset_secondary_password,
    set_secondary_user_active,
)
from device_trust import (
    confirm_device_verification,
    create_device_verification,
    device_verify_enabled,
    get_pending_verification,
    is_device_trusted,
    MASTER_VERIFY_EMAIL,
    DEVICE_VERIFY_MINUTES,
    APP_BASE_URL,
)
from email_sender import send_device_verification_email, smtp_configured
from load_secrets import redact_secrets

PUBLIC_API_PATHS = frozenset({
    '/api/health',
    '/api/auth/login',
    '/api/auth/status',
    '/api/auth/confirm-device',
    '/api/auth/send-device-code',
})


def _start_session(user: dict) -> None:
    session.clear()
    session.permanent = True
    session['username'] = user['username']
    session['role'] = user['role']


def register_auth(app):
    app.config.setdefault('PERMANENT_SESSION_LIFETIME', timedelta(hours=8))
    app.config.setdefault('SESSION_COOKIE_HTTPONLY', True)
    app.config.setdefault('SESSION_COOKIE_SAMESITE', 'Lax')

    @app.before_request
    def require_auth():
        path = request.path
        if not path.startswith('/api/'):
            return None
        if path in PUBLIC_API_PATHS:
            return None
        if not session.get('username'):
            return jsonify({'success': False, 'error': 'Não autenticado', 'code': 'AUTH_REQUIRED'}), 401
        return None

    @app.route('/api/auth/status', methods=['GET'])
    def auth_status():
        return jsonify({
            'success': True,
            'master_configured': master_configured(),
            'master_username': MASTER_USERNAME,
            'device_verify_enabled': device_verify_enabled(),
            'smtp_configured': smtp_configured(),
            'verify_email_masked': _mask_email(MASTER_VERIFY_EMAIL),
        })

    @app.route('/api/auth/login', methods=['POST'])
    def auth_login():
        if not master_configured():
            return jsonify({
                'success': False,
                'error': 'Autenticação não configurada. Defina MASTER_PASSWORD_HASH no .env.',
                'code': 'AUTH_NOT_CONFIGURED',
            }), 503

        data = request.get_json(silent=True) or {}
        username = (data.get('username') or '').strip()
        password = data.get('password') or ''
        device_id = (data.get('device_id') or '').strip()

        user = authenticate(username, password)
        if not user:
            return jsonify({'success': False, 'error': 'Usuário ou senha inválidos.'}), 401

        # Usuários secundários: login direto (sem verificação de dispositivo)
        if user['role'] != 'master' or not device_verify_enabled():
            _start_session(user)
            return jsonify({'success': True, 'user': user})

        if is_device_trusted(user['username'], device_id):
            _start_session(user)
            return jsonify({'success': True, 'user': user})

        pending, err = create_device_verification(
            username=user['username'],
            device_id=device_id,
            user_agent=request.headers.get('User-Agent', ''),
            ip_hint=request.remote_addr or '',
        )
        if err or not pending:
            return jsonify({'success': False, 'error': err or 'Erro ao iniciar verificação.'}), 400

        return jsonify({
            'success': True,
            'verification_required': True,
            'verification_token': pending['token'],
            'email_masked': _mask_email(MASTER_VERIFY_EMAIL),
            'expires_minutes': DEVICE_VERIFY_MINUTES,
            'smtp_configured': smtp_configured(),
        })

    @app.route('/api/auth/send-device-code', methods=['POST'])
    def auth_send_device_code():
        data = request.get_json(silent=True) or {}
        token = (data.get('verification_token') or data.get('token') or '').strip()
        email = (data.get('email') or '').strip()
        device_id = (data.get('device_id') or '').strip()

        pending, err = get_pending_verification(token, device_id)
        if err or not pending:
            return jsonify({'success': False, 'error': err or 'Verificação inválida.'}), 400

        if not _emails_match(email, MASTER_VERIFY_EMAIL):
            return jsonify({'success': False, 'error': 'E-mail não confere com o cadastrado.'}), 400

        if not smtp_configured():
            if _dev_show_verification_code():
                return jsonify({
                    'success': True,
                    'email_masked': _mask_email(pending['email_to']),
                    'expires_minutes': DEVICE_VERIFY_MINUTES,
                    'dev_mode': True,
                    'dev_code': pending['code'],
                })
            return jsonify({
                'success': False,
                'error': 'Configure SMTP_PASSWORD no backend/.env (senha de app do Gmail).',
                'code': 'SMTP_NOT_CONFIGURED',
            }), 503

        sent, mail_err = send_device_verification_email(
            to=pending['email_to'],
            username=pending['username'],
            code=pending['code'],
            confirm_url=pending['confirm_url'],
            user_agent=request.headers.get('User-Agent', ''),
            ip_hint=request.remote_addr or '',
            expires_minutes=DEVICE_VERIFY_MINUTES,
        )
        if not sent:
            return jsonify({
                'success': False,
                'error': f'Não foi possível enviar o e-mail: {redact_secrets(mail_err or "erro desconhecido")}',
                'code': 'EMAIL_SEND_FAILED',
            }), 503

        return jsonify({
            'success': True,
            'email_masked': _mask_email(pending['email_to']),
            'expires_minutes': DEVICE_VERIFY_MINUTES,
        })

    @app.route('/api/auth/confirm-device', methods=['POST'])
    def auth_confirm_device():
        data = request.get_json(silent=True) or {}
        token = (data.get('token') or request.args.get('token') or '').strip()
        device_id = (data.get('device_id') or '').strip()
        code = data.get('code')

        user, err = confirm_device_verification(token=token, device_id=device_id, code=code)
        if err or not user:
            return jsonify({'success': False, 'error': err or 'Verificação inválida.'}), 400

        _start_session(user)
        return jsonify({'success': True, 'user': user})

    @app.route('/api/auth/logout', methods=['POST'])
    def auth_logout():
        session.clear()
        return jsonify({'success': True})

    @app.route('/api/auth/me', methods=['GET'])
    def auth_me():
        username = session.get('username')
        if not username:
            return jsonify({'success': False, 'authenticated': False}), 401
        return jsonify({
            'success': True,
            'authenticated': True,
            'user': {'username': username, 'role': session.get('role', 'user')},
        })

    @app.route('/api/auth/users', methods=['GET'])
    def auth_list_users():
        if session.get('role') != 'master':
            return jsonify({'success': False, 'error': 'Acesso negado.'}), 403
        return jsonify({'success': True, 'users': list_secondary_users()})

    @app.route('/api/auth/users', methods=['POST'])
    def auth_create_user():
        if session.get('role') != 'master':
            return jsonify({'success': False, 'error': 'Acesso negado.'}), 403

        data = request.get_json(silent=True) or {}
        username = data.get('username') or ''
        password = data.get('password') or ''

        user, err = create_secondary_user(
            username,
            password,
            created_by=session.get('username', 'master'),
        )
        if err:
            return jsonify({'success': False, 'error': err}), 400
        return jsonify({'success': True, 'user': user}), 201

    @app.route('/api/auth/users/<username>', methods=['DELETE'])
    def auth_delete_user(username):
        if session.get('role') != 'master':
            return jsonify({'success': False, 'error': 'Acesso negado.'}), 403
        if is_master_username(username):
            return jsonify({'success': False, 'error': 'Não é possível excluir o master.'}), 400
        ok, err = delete_secondary_user(username)
        if not ok:
            return jsonify({'success': False, 'error': err}), 400
        return jsonify({'success': True})

    @app.route('/api/auth/users/<username>/password', methods=['PUT'])
    def auth_reset_password(username):
        if session.get('role') != 'master':
            return jsonify({'success': False, 'error': 'Acesso negado.'}), 403

        data = request.get_json(silent=True) or {}
        password = data.get('password') or ''
        ok, err = reset_secondary_password(username, password)
        if not ok:
            return jsonify({'success': False, 'error': err}), 400
        return jsonify({'success': True})

    @app.route('/api/auth/users/<username>/active', methods=['PUT'])
    def auth_set_active(username):
        if session.get('role') != 'master':
            return jsonify({'success': False, 'error': 'Acesso negado.'}), 403

        data = request.get_json(silent=True) or {}
        active = bool(data.get('active', True))
        ok, err = set_secondary_user_active(username, active)
        if not ok:
            return jsonify({'success': False, 'error': err}), 400
        return jsonify({'success': True, 'active': active})


def _mask_email(email: str) -> str:
    email = (email or '').strip()
    if '@' not in email:
        return '***'
    local, domain = email.split('@', 1)
    if len(local) <= 2:
        masked_local = local[0] + '***'
    else:
        masked_local = local[0] + '***' + local[-1]
    return f'{masked_local}@{domain}'


def _emails_match(provided: str, expected: str) -> bool:
    return (provided or '').strip().lower() == (expected or '').strip().lower()


def _dev_show_verification_code() -> bool:
    """Em localhost sem SMTP, exibe o código na tela (somente desenvolvimento)."""
    if os.environ.get('AUTH_DEV_SHOW_CODE', '').strip().lower() in ('0', 'false', 'no'):
        return False
    if os.environ.get('AUTH_DEV_SHOW_CODE', '').strip().lower() in ('1', 'true', 'yes'):
        return True
    base = (APP_BASE_URL or '').lower()
    return 'localhost' in base or '127.0.0.1' in base
