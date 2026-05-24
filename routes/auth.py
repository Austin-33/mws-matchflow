from datetime import datetime

from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user

from extensions import db
from models.user import User, PasswordHistory

auth_bp = Blueprint('auth', __name__)


# ─── Login ────────────────────────────────────────────────────

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        identifier = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = 'remember' in request.form

        # Aceita username OU email
        user = (
            User.query.filter_by(username=identifier).first() or
            User.query.filter_by(email=identifier).first()
        )

        # Tratar is_active=None (utilizadores migrados sem o campo)
        user_active = user and (user.is_active is True or user.is_active is None)

        if user and user_active and user.check_password(password):
            user.record_login()
            db.session.commit()
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))

        if user and user.is_active is False:
            flash('Esta conta está desativada. Contacta o administrador.', 'error')
        else:
            flash('Credenciais inválidas. Verifica o username/email e a password.', 'error')

    return render_template('auth/login.html')


# ─── Register ─────────────────────────────────────────────────

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        full_name = request.form.get('full_name', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        role = request.form.get('role', 'manager')
        sport_role = request.form.get('sport_role', 'player')
        preferred_position = request.form.get('preferred_position', '').strip()
        nationality = request.form.get('nationality', '').strip()
        age = request.form.get('age', type=int)

        # ─── Validações ───────────────────────────────────────
        errors = []

        if len(username) < 3:
            errors.append('O username deve ter pelo menos 3 caracteres.')
        if not username.replace('_', '').replace('-', '').isalnum():
            errors.append('O username só pode ter letras, números, _ e -.')
        if len(password) < 6:
            errors.append('A password deve ter pelo menos 6 caracteres.')
        if password != confirm:
            errors.append('As passwords não coincidem.')
        if User.query.filter_by(username=username).first():
            errors.append(f'O username "{username}" já está em uso.')
        if email and User.query.filter_by(email=email).first():
            errors.append(f'O email "{email}" já está registado.')

        if errors:
            for e in errors:
                flash(e, 'error')
            return render_template('auth/register.html',
                                   form_data={'username': username, 'email': email,
                                              'full_name': full_name, 'role': role,
                                              'sport_role': sport_role,
                                              'preferred_position': preferred_position})

        # ─── Criar utilizador ─────────────────────────────────
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            role=role,
            sport_role=sport_role,
            preferred_position=preferred_position,
            is_active=True,
        )
        db.session.add(user)
        db.session.commit()

        user.set_password(password)
        db.session.commit()
        user.save_password_history()

        # ─── Se é jogador/treinador/CEO → criar perfil Player ─
        if sport_role in ('player', 'coach', 'ceo'):
            from models.team import Player
            # Criar uma equipa "Mercado Livre" virtual se não existir
            from models.team import Team
            free_team = Team.query.filter_by(name='__FREE_AGENTS__').first()
            if not free_team:
                free_team = Team(
                    name='__FREE_AGENTS__',
                    short_name='FREE',
                    sport='futsal',
                    notes='Equipa virtual — jogadores livres sem clube',
                )
                db.session.add(free_team)
                db.session.commit()

            player = Player(
                name=full_name or username,
                position=preferred_position,
                nationality=nationality,
                age=age,
                email=email,
                status='ativo',
                team_id=free_team.id,
            )
            db.session.add(player)
            db.session.commit()

            user.player_id = player.id
            db.session.commit()

        flash('✅ Conta criada com sucesso!', 'success')
        flash(f'O teu ID único: {user.public_id}', 'info')
        if sport_role in ('player', 'coach', 'ceo'):
            flash('Estás no Mercado Livre. Pede contrato a uma equipa! ⚽', 'info')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html', form_data={})


# ─── Logout ───────────────────────────────────────────────────

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sessão terminada.', 'info')
    return redirect(url_for('auth.login'))


# ─── Perfil ───────────────────────────────────────────────────

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_profile':
            full_name = request.form.get('full_name', '').strip()
            email = request.form.get('email', '').strip().lower()

            existing = User.query.filter_by(email=email).first()
            if existing and existing.id != current_user.id:
                flash('Este email já está em uso por outra conta.', 'error')
            else:
                current_user.full_name = full_name
                current_user.email = email
                db.session.commit()
                flash('✅ Perfil atualizado!', 'success')

        elif action == 'change_password':
            current_pw = request.form.get('current_password', '')
            new_pw = request.form.get('new_password', '')
            confirm_pw = request.form.get('confirm_password', '')

            if not current_user.check_password(current_pw):
                flash('❌ Password atual incorreta.', 'error')
            elif len(new_pw) < 6:
                flash('❌ A nova password deve ter pelo menos 6 caracteres.', 'error')
            elif new_pw != confirm_pw:
                flash('❌ As novas passwords não coincidem.', 'error')
            elif current_user.was_password_used(new_pw):
                flash('❌ Não podes reutilizar uma das últimas 5 passwords.', 'error')
            else:
                current_user.set_password(new_pw)
                db.session.commit()
                current_user.save_password_history()
                flash('✅ Password alterada com sucesso!', 'success')

        return redirect(url_for('auth.profile'))

    history = PasswordHistory.query.filter_by(user_id=current_user.id)\
        .order_by(PasswordHistory.changed_at.desc()).limit(10).all()

    return render_template('auth/profile.html', history=history)


# ─── Recuperar password ───────────────────────────────────────

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    token_generated = None

    if request.method == 'POST':
        identifier = request.form.get('identifier', '').strip()
        user = (
            User.query.filter_by(email=identifier).first() or
            User.query.filter_by(username=identifier).first()
        )

        if user:
            token = user.generate_reset_token()
            db.session.commit()
            token_generated = token
        else:
            flash('Nenhuma conta encontrada com esse email ou username.', 'error')

    return render_template('auth/forgot_password.html', token=token_generated)


# ─── Reset password ───────────────────────────────────────────

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    user = User.query.filter_by(reset_token=token).first()

    if not user or not user.verify_reset_token(token):
        flash('Link inválido ou expirado. Solicita um novo.', 'error')
        return redirect(url_for('auth.forgot_password'))

    if request.method == 'POST':
        new_pw = request.form.get('new_password', '')
        confirm_pw = request.form.get('confirm_password', '')

        if len(new_pw) < 6:
            flash('A password deve ter pelo menos 6 caracteres.', 'error')
        elif new_pw != confirm_pw:
            flash('As passwords não coincidem.', 'error')
        elif user.was_password_used(new_pw):
            flash('Não podes reutilizar uma das últimas 5 passwords.', 'error')
        else:
            user.set_password(new_pw)
            user.clear_reset_token()
            db.session.commit()
            user.save_password_history()
            flash('✅ Password redefinida! Faz login.', 'success')
            return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', token=token, user=user)


# ─── Admin: lista de utilizadores ────────────────────────────

@auth_bp.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'admin':
        flash('Acesso restrito a administradores.', 'error')
        return redirect(url_for('index'))

    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('auth/admin_users.html', users=users)


@auth_bp.route('/admin/users/<int:user_id>/toggle', methods=['POST'])
@login_required
def toggle_user(user_id):
    if current_user.role != 'admin':
        flash('Acesso restrito.', 'error')
        return redirect(url_for('index'))

    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('Não podes desativar a tua própria conta.', 'error')
    else:
        user.is_active = not bool(user.is_active)
        db.session.commit()
        state = 'ativada' if user.is_active else 'desativada'
        flash(f'Conta de {user.username} {state}.', 'success')

    return redirect(url_for('auth.admin_users'))


@auth_bp.route('/admin/users/<int:user_id>/role', methods=['POST'])
@login_required
def change_role(user_id):
    if current_user.role != 'admin':
        flash('Acesso restrito.', 'error')
        return redirect(url_for('index'))

    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role', 'manager')
    if new_role in ('admin', 'manager', 'player'):
        user.role = new_role
        db.session.commit()
        flash(f'Role de {user.username} alterado para {new_role}.', 'success')

    return redirect(url_for('auth.admin_users'))
