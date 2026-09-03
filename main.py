# Import
from flask import Flask, render_template, request, redirect, session, jsonify
# Importowanie biblioteki bazy danych
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text, and_, or_
from datetime import datetime, timedelta, timezone
import os
import secrets
import string
import time


app = Flask(__name__)
# Podłączanie SQLite

app.secret_key = 'jabfjbveou45201'

# Upewnij się, że folder instance istnieje i użyj jednej, jawnej ścieżki do bazy.
os.makedirs(app.instance_path, exist_ok=True)
db_path = os.path.join(app.instance_path, 'diary.db')

app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {'timeout': 30}
}
# Creating a DB
db = SQLAlchemy(app)

ACTION_TYPES = ['Pomysł', 'Marsz', 'Strajk', 'Pomoc', 'Sprzątanie', 'Edukacja', 'Petycja', 'Kampania', 'Pracownia', 'Spotkanie', 'Wolontariat', 'Zbiórka', 'Inne']
PRIVATE_CODE_CHARS = string.ascii_uppercase + string.digits
PRIVATE_CODE_LENGTH = 8
SECURITY_CODE_CHARS = string.digits
SECURITY_CODE_LENGTH = 5

#Zadanie nr 1. Utwórz tabelę DB

class Card(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    subtitle = db.Column(db.String(300), nullable=False)
    text = db.Column(db.Text, nullable=False)
    user_name = db.Column(db.String(120), nullable=False)
    user_email = db.Column(db.String(120), nullable=False)
    action_type = db.Column(db.String(80), nullable=False, default='Pomysł')
    city = db.Column(db.String(120), nullable=False, default='')
    is_draft = db.Column(db.Boolean, nullable=False, default=False)

    def __repr__(self):
        return f'<Card {self.id}>'
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    private_code = db.Column(db.String(20), unique=True, nullable=False)
    security_code = db.Column(db.String(5), unique=True, nullable=False)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)
    session_token = db.Column(db.String(64), nullable=False, default='')
    session_expires_at = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f'<User {self.email}>'


class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.Integer, db.ForeignKey('card.id'), nullable=False)
    user_name = db.Column(db.String(120), nullable=False)
    user_email = db.Column(db.String(120), nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Participation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.Integer, db.ForeignKey('card.id'), nullable=False)
    user_name = db.Column(db.String(120), nullable=False)
    user_email = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (db.UniqueConstraint('card_id', 'user_email', name='unique_participation_per_user_card'),)


class PrivateMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender_email = db.Column(db.String(120), nullable=False)
    sender_name = db.Column(db.String(120), nullable=False)
    receiver_email = db.Column(db.String(120), nullable=False)
    text = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


with app.app_context():
    db.create_all()
    inspector = inspect(db.engine)
    existing_tables = set(inspector.get_table_names())

    def ensure_column(table_name, column_name, ddl):
        if table_name not in existing_tables:
            return
        current_inspector = inspect(db.engine)
        columns = {column['name'] for column in current_inspector.get_columns(table_name)}
        if column_name not in columns:
            db.session.execute(text(ddl))

    ensure_column('user', 'name', "ALTER TABLE user ADD COLUMN name VARCHAR(120) NOT NULL DEFAULT ''")
    ensure_column('user', 'private_code', "ALTER TABLE user ADD COLUMN private_code VARCHAR(20) NOT NULL DEFAULT ''")
    ensure_column('user', 'security_code', "ALTER TABLE user ADD COLUMN security_code VARCHAR(5) NOT NULL DEFAULT ''")
    ensure_column('user', 'is_admin', "ALTER TABLE user ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0")
    ensure_column('user', 'session_token', "ALTER TABLE user ADD COLUMN session_token VARCHAR(64) NOT NULL DEFAULT ''")
    ensure_column('user', 'session_expires_at', "ALTER TABLE user ADD COLUMN session_expires_at DATETIME")
    ensure_column('card', 'user_name', "ALTER TABLE card ADD COLUMN user_name VARCHAR(120) NOT NULL DEFAULT ''")
    ensure_column('card', 'action_type', "ALTER TABLE card ADD COLUMN action_type VARCHAR(80) NOT NULL DEFAULT 'Pomysł'")
    ensure_column('card', 'city', "ALTER TABLE card ADD COLUMN city VARCHAR(120) NOT NULL DEFAULT ''")
    ensure_column('card', 'is_draft', "ALTER TABLE card ADD COLUMN is_draft BOOLEAN NOT NULL DEFAULT 0")
    ensure_column('comment', 'user_name', "ALTER TABLE comment ADD COLUMN user_name VARCHAR(120) NOT NULL DEFAULT ''")
    ensure_column('participation', 'user_name', "ALTER TABLE participation ADD COLUMN user_name VARCHAR(120) NOT NULL DEFAULT ''")
    ensure_column('private_message', 'is_read', "ALTER TABLE private_message ADD COLUMN is_read BOOLEAN NOT NULL DEFAULT 1")

    users_with_codes = User.query.order_by(User.id.asc()).all()
    assigned_codes = set()
    assigned_security_codes = set()
    for existing_user in users_with_codes:
        normalized_code = (existing_user.private_code or '').strip().upper()
        if not normalized_code or normalized_code in assigned_codes:
            while True:
                generated_code = ''.join(secrets.choice(PRIVATE_CODE_CHARS) for _ in range(PRIVATE_CODE_LENGTH))
                if generated_code not in assigned_codes:
                    normalized_code = generated_code
                    break
        existing_user.private_code = normalized_code
        assigned_codes.add(normalized_code)

        normalized_security_code = (existing_user.security_code or '').strip()
        if (
            len(normalized_security_code) != SECURITY_CODE_LENGTH
            or not normalized_security_code.isdigit()
            or normalized_security_code in assigned_security_codes
        ):
            while True:
                generated_security_code = ''.join(
                    secrets.choice(SECURITY_CODE_CHARS) for _ in range(SECURITY_CODE_LENGTH)
                )
                if generated_security_code not in assigned_security_codes:
                    normalized_security_code = generated_security_code
                    break

        existing_user.security_code = normalized_security_code
        assigned_security_codes.add(normalized_security_code)

    db.session.commit()
    db.session.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_user_private_code ON user(private_code)"))
    db.session.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_user_security_code ON user(security_code)"))
    db.session.commit()


def generate_private_code():
    while True:
        code = ''.join(secrets.choice(PRIVATE_CODE_CHARS) for _ in range(PRIVATE_CODE_LENGTH))
        if not User.query.filter_by(private_code=code).first():
            return code


def generate_security_code():
    while True:
        code = ''.join(secrets.choice(SECURITY_CODE_CHARS) for _ in range(SECURITY_CODE_LENGTH))
        if not User.query.filter_by(security_code=code).first():
            return code


def reset_security_code(user):
    user.security_code = generate_security_code()
    db.session.commit()


def delete_user_messages(target_email):
    deleted_count = PrivateMessage.query.filter(
        or_(
            PrivateMessage.sender_email == target_email,
            PrivateMessage.receiver_email == target_email,
        )
    ).delete(synchronize_session=False)
    db.session.commit()
    return deleted_count


def delete_user_and_related_data(target_email):
    user = User.query.filter_by(email=target_email).first()
    if user is None:
        return False

    Comment.query.filter_by(user_email=target_email).delete()
    Participation.query.filter_by(user_email=target_email).delete()
    Card.query.filter_by(user_email=target_email).delete()
    PrivateMessage.query.filter(
        or_(
            PrivateMessage.sender_email == target_email,
            PrivateMessage.receiver_email == target_email,
        )
    ).delete()
    db.session.delete(user)
    db.session.commit()
    return True


def start_user_session(user):
    token = secrets.token_hex(32)
    user.session_token = token
    user.session_expires_at = datetime.utcnow() + timedelta(days=2)
    db.session.commit()

    session.clear()
    session['user_email'] = user.email
    session['user_name'] = user.name or user.email.split('@')[0]
    session['is_admin'] = bool(user.is_admin)
    session['auth_token'] = token
    session.permanent = False


def clear_user_session(user):
    if user is not None:
        user.session_token = ''
        user.session_expires_at = None
        db.session.commit()
    session.clear()


def get_current_user():
    user_email = session.get('user_email')
    if not user_email:
        return None

    auth_token = session.get('auth_token', '')
    user = User.query.filter_by(email=user_email).first()
    if user is None:
        session.clear()
        return None

    if not auth_token or user.session_token != auth_token:
        session.clear()
        return None

    if user.session_expires_at and user.session_expires_at < datetime.utcnow():
        user.session_token = ''
        user.session_expires_at = None
        db.session.commit()
        session.clear()
        return None

    return user


def is_current_user_admin():
    user = get_current_user()
    return bool(user and user.is_admin)


def can_manage_card(card, user=None):
    if user is None:
        user = get_current_user()
    return bool(user and (user.is_admin or card.user_email == user.email))


def get_chat_partner_by_code(code, current_user_email):
    normalized_code = (code or '').strip().upper()
    if not normalized_code:
        return None, 'Podaj kod użytkownika.'

    partner = User.query.filter_by(private_code=normalized_code).first()
    if partner is None:
        return None, 'Nie znaleziono użytkownika z takim kodem.'
    # if partner.email == current_user_email:
    #     return None, 'Nie możesz pisać wiadomości do samego siebie.'
    return partner, None


def private_chat_query(current_user_email, partner_email):
    return PrivateMessage.query.filter(
        or_(
            and_(
                PrivateMessage.sender_email == current_user_email,
                PrivateMessage.receiver_email == partner_email,
            ),
            and_(
                PrivateMessage.sender_email == partner_email,
                PrivateMessage.receiver_email == current_user_email,
            ),
        )
    )


def serialize_private_message(message, current_user_email):
    return {
        'id': message.id,
        'text': message.text,
        'sender_email': message.sender_email,
        'sender_name': message.sender_name,
        'is_mine': message.sender_email == current_user_email,
        'is_read': bool(message.is_read),
        'created_at': format_local_datetime(message.created_at),
    }


def build_message_preview(text, max_length=72):
    normalized = ' '.join((text or '').split())
    if len(normalized) <= max_length:
        return normalized
    return f"{normalized[:max_length - 1]}…"


def format_local_datetime(value):
    if value is None:
        return ''
    utc_value = value.replace(tzinfo=timezone.utc)
    return utc_value.astimezone().strftime('%Y-%m-%d %H:%M:%S')


def mark_private_messages_as_read(current_user_email, partner_email):
    updated_rows = PrivateMessage.query.filter_by(
        sender_email=partner_email,
        receiver_email=current_user_email,
        is_read=False,
    ).update({'is_read': True}, synchronize_session=False)

    if updated_rows:
        db.session.commit()


def get_private_chat_summaries(current_user_email):
    raw_messages = PrivateMessage.query.filter(
        or_(
            PrivateMessage.sender_email == current_user_email,
            PrivateMessage.receiver_email == current_user_email,
        )
    ).order_by(PrivateMessage.id.desc()).all()

    if not raw_messages:
        return []

    partner_emails = []
    summaries_by_partner = {}
    for message in raw_messages:
        partner_email = message.receiver_email if message.sender_email == current_user_email else message.sender_email
        if partner_email not in summaries_by_partner:
            partner_emails.append(partner_email)
            summaries_by_partner[partner_email] = {
                'partner_email': partner_email,
                'last_message_id': message.id,
                'last_message_preview': build_message_preview(message.text),
                'last_message_at': format_local_datetime(message.created_at),
                'last_message_is_mine': message.sender_email == current_user_email,
                'last_message_is_read': bool(message.is_read),
                'unread_count': 0,
            }

        if message.receiver_email == current_user_email and not message.is_read:
            summaries_by_partner[partner_email]['unread_count'] += 1

    users = User.query.filter(User.email.in_(partner_emails)).all()
    users_by_email = {user.email: user for user in users}

    summaries = []
    for partner_email in partner_emails:
        summary = summaries_by_partner[partner_email]
        partner = users_by_email.get(partner_email)

        partner_name = partner.name if partner and partner.name else partner_email.split('@')[0]
        partner_code = partner.private_code if partner else ''

        if summary['unread_count'] > 0:
            status_label = 'Nieodczytane'
        elif summary['last_message_is_mine'] and summary['last_message_is_read']:
            status_label = 'Odczytana'
        elif summary['last_message_is_mine']:
            status_label = 'Wysłana'
        else:
            status_label = 'Odczytane'

        summaries.append({
            'partner_name': partner_name,
            'partner_email': partner_email,
            'partner_code': partner_code,
            'last_message_preview': summary['last_message_preview'],
            'last_message_at': summary['last_message_at'],
            'status_label': status_label,
            'unread_count': summary['unread_count'],
        })

    return summaries


@app.before_request
def validate_session_on_every_request():
    if request.endpoint == 'static':
        return None

    if not session.get('user_email'):
        return None

    user = get_current_user()
    if user is not None:
        session['user_name'] = user.name or user.email.split('@')[0]
        session['is_admin'] = bool(user.is_admin)
        return None

    if request.path.startswith('/api/'):
        return jsonify({'ok': False, 'error': 'Sesja wygasla. Zaloguj sie ponownie.'}), 401

    return redirect('/login')

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        form_login = request.form['email']
        form_password = request.form['password']
        user = User.query.filter_by(email=form_login, password=form_password).first()
        if user:
            start_user_session(user)
            return redirect('/index')

        error = "Nieprawidłowy login lub hasło"
        return render_template('login.html', error=error)
    else:
        return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email']
        password = request.form['password']

        if not name:
            error = 'Podaj nick'
            return render_template('register.html', error=error)

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            error = 'Konto z takim adresem e-mail już istnieje'
            return render_template('register.html', error=error)

        # Dodanie nowego użytkownika do bazy danych
        new_user = User(
            name=name,
            email=email,
            password=password,
            private_code=generate_private_code(),
            security_code=generate_security_code(),
        )
        db.session.add(new_user)
        db.session.commit()
        start_user_session(new_user)
        return redirect('/index')
    else:
        return render_template('register.html')


@app.route('/account', methods=['GET', 'POST'])
def account():
    user_email = session.get('user_email')
    if not user_email:
        return redirect('/login')

    user = User.query.filter_by(email=user_email).first()
    if user is None:
        session.clear()
        return redirect('/login')

    session['is_admin'] = bool(user.is_admin)
    message = None

    if request.method == 'POST':
        action = request.form.get('action', 'update_name')

        if action == 'change_password':
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')

            if current_password != user.password:
                drafts = Card.query.filter_by(user_email=user_email, is_draft=True).order_by(Card.id.desc()).all()
                return render_template('account.html', user=user, drafts=drafts, error='Aktualne hasło jest nieprawidłowe', draft_error=False, message=None)

            if len(new_password) < 6:
                drafts = Card.query.filter_by(user_email=user_email, is_draft=True).order_by(Card.id.desc()).all()
                return render_template('account.html', user=user, drafts=drafts, error='Nowe hasło musi mieć co najmniej 6 znaków', draft_error=False, message=None)

            if new_password != confirm_password:
                drafts = Card.query.filter_by(user_email=user_email, is_draft=True).order_by(Card.id.desc()).all()
                return render_template('account.html', user=user, drafts=drafts, error='Nowe hasła nie są takie same', draft_error=False, message=None)

            user.password = new_password
            db.session.commit()
            return redirect('/account?message=password_changed')

        new_name = request.form.get('name', '').strip()
        if not new_name:
            drafts = Card.query.filter_by(user_email=user_email, is_draft=True).order_by(Card.id.desc()).all()
            return render_template('account.html', user=user, drafts=drafts, error='Podaj nick', draft_error=False, message=None)

        user.name = new_name
        session['user_name'] = new_name
        db.session.commit()
        return redirect('/account?message=name_saved')

    drafts = Card.query.filter_by(user_email=user_email, is_draft=True).order_by(Card.id.desc()).all()
    draft_error = request.args.get('draft_error') == '1'
    message_key = request.args.get('message', '').strip()
    if message_key == 'password_changed':
        message = 'Hasło zostało zmienione'
    elif message_key == 'name_saved':
        message = 'Nick został zapisany'

    return render_template('account.html', user=user, drafts=drafts, draft_error=draft_error, message=message)


@app.route('/private_chat')
def private_chat():
    current_user = get_current_user()
    if current_user is None:
        return redirect('/login')

    partner_code = request.args.get('code', '').strip().upper()
    partner_user = None
    chat_error = None
    messages = []
    conversations = get_private_chat_summaries(current_user.email)

    if partner_code:
        partner_user, chat_error = get_chat_partner_by_code(partner_code, current_user.email)
        if partner_user is not None:
            raw_messages = private_chat_query(current_user.email, partner_user.email).order_by(PrivateMessage.id.asc()).all()
            messages = [serialize_private_message(message, current_user.email) for message in raw_messages]
            conversations = get_private_chat_summaries(current_user.email)

    return render_template(
        'private_chat.html',
        current_user=current_user,
        partner_code=partner_code,
        partner_user=partner_user,
        chat_error=chat_error,
        messages=messages,
        conversations=conversations,
    )


@app.route('/api/private_chat/messages')
def api_private_chat_messages():
    current_user = get_current_user()
    if current_user is None:
        return jsonify({'ok': False, 'error': 'Musisz się zalogować.'}), 401

    partner_code = request.args.get('code', '').strip().upper()
    partner_user, chat_error = get_chat_partner_by_code(partner_code, current_user.email)
    if partner_user is None:
        return jsonify({'ok': False, 'error': chat_error}), 400

    after_id_raw = request.args.get('after_id', '0').strip()
    after_id = int(after_id_raw) if after_id_raw.isdigit() else 0

    raw_messages = private_chat_query(current_user.email, partner_user.email)
    if after_id > 0:
        raw_messages = raw_messages.filter(PrivateMessage.id > after_id)

    raw_messages = raw_messages.order_by(PrivateMessage.id.asc()).limit(200).all()
    serialized_messages = [serialize_private_message(message, current_user.email) for message in raw_messages]

    return jsonify({
        'ok': True,
        'messages': serialized_messages,
        'partner': {
            'name': partner_user.name,
            'code': partner_user.private_code,
        },
    })


@app.route('/api/private_chat/messages/wait')
def api_private_chat_messages_wait():
    current_user = get_current_user()
    if current_user is None:
        return jsonify({'ok': False, 'error': 'Musisz sie zalogowac.'}), 401

    partner_code = request.args.get('code', '').strip().upper()
    partner_user, chat_error = get_chat_partner_by_code(partner_code, current_user.email)
    if partner_user is None:
        return jsonify({'ok': False, 'error': chat_error}), 400

    after_id_raw = request.args.get('after_id', '0').strip()
    after_id = int(after_id_raw) if after_id_raw.isdigit() else 0

    timeout_raw = request.args.get('timeout', '20').strip()
    timeout_seconds = int(timeout_raw) if timeout_raw.isdigit() else 20
    timeout_seconds = max(1, min(timeout_seconds, 30))

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        raw_messages = private_chat_query(current_user.email, partner_user.email)
        if after_id > 0:
            raw_messages = raw_messages.filter(PrivateMessage.id > after_id)

        raw_messages = raw_messages.order_by(PrivateMessage.id.asc()).limit(200).all()
        if raw_messages:
            serialized_messages = [serialize_private_message(message, current_user.email) for message in raw_messages]
            return jsonify({'ok': True, 'messages': serialized_messages})

        time.sleep(0.6)

    return jsonify({'ok': True, 'messages': []})


@app.route('/api/private_chat/send', methods=['POST'])
def api_private_chat_send():
    current_user = get_current_user()
    if current_user is None:
        return jsonify({'ok': False, 'error': 'Musisz się zalogować.'}), 401

    payload = request.get_json(silent=True) or request.form
    partner_code = str(payload.get('code', '')).strip().upper()
    message_text = str(payload.get('text', '')).strip()

    partner_user, chat_error = get_chat_partner_by_code(partner_code, current_user.email)
    if partner_user is None:
        return jsonify({'ok': False, 'error': chat_error}), 400
    if not message_text:
        return jsonify({'ok': False, 'error': 'Wiadomość nie może być pusta.'}), 400
    if len(message_text) > 1000:
        return jsonify({'ok': False, 'error': 'Wiadomość jest za długa (max 1000 znaków).'}), 400

    message = PrivateMessage(
        sender_email=current_user.email,
        sender_name=current_user.name or current_user.email.split('@')[0],
        receiver_email=partner_user.email,
        text=message_text,
        is_read=False,
    )
    db.session.add(message)
    db.session.commit()

    return jsonify({'ok': True, 'message': serialize_private_message(message, current_user.email)})


@app.route('/api/private_chat/conversations')
def api_private_chat_conversations():
    current_user = get_current_user()
    if current_user is None:
        return jsonify({'ok': False, 'error': 'Musisz się zalogować.'}), 401

    return jsonify({
        'ok': True,
        'conversations': get_private_chat_summaries(current_user.email),
    })


@app.route('/api/private_chat/mark_read', methods=['POST'])
def api_private_chat_mark_read():
    current_user = get_current_user()
    if current_user is None:
        return jsonify({'ok': False, 'error': 'Musisz się zalogować.'}), 401

    payload = request.get_json(silent=True) or request.form
    partner_code = str(payload.get('code', '')).strip().upper()
    partner_user, chat_error = get_chat_partner_by_code(partner_code, current_user.email)
    if partner_user is None:
        return jsonify({'ok': False, 'error': chat_error}), 400

    mark_private_messages_as_read(current_user.email, partner_user.email)
    return jsonify({'ok': True, 'conversations': get_private_chat_summaries(current_user.email)})


@app.route('/publish_draft/<int:id>', methods=['POST'])
def publish_draft(id):
    user_email = session.get('user_email')
    if not user_email:
        return redirect('/login')

    draft = Card.query.filter_by(id=id, is_draft=True).first()
    if draft is None:
        return redirect('/account')

    if draft.user_email != user_email and not is_current_user_admin():
        return redirect('/account')

    # Publikacja wymaga pełnych danych karty.
    if not draft.title.strip() or not draft.subtitle.strip() or not draft.text.strip() or not draft.city.strip():
        return redirect('/account?draft_error=1')

    draft.is_draft = False
    draft.user_name = session.get('user_name') or user_email.split('@')[0]
    db.session.commit()
    return redirect('/index')


@app.route('/delete_draft/<int:id>', methods=['POST'])
def delete_draft(id):
    user_email = session.get('user_email')
    if not user_email:
        return redirect('/login')

    draft = Card.query.filter_by(id=id, is_draft=True).first()
    if draft is None:
        return redirect('/account')

    if draft.user_email != user_email and not is_current_user_admin():
        return redirect('/account')

    db.session.delete(draft)
    db.session.commit()
    return redirect('/account')


@app.route('/logout')
def logout():
    clear_user_session(get_current_user())
    return redirect('/login')


@app.route('/delete_account', methods=['POST'])
def delete_account():
    user_email = session.get('user_email')
    if not user_email:
        return redirect('/login')

    target_email = request.form.get('user_email', user_email)
    is_admin_action = is_current_user_admin() and target_email != user_email

    if target_email != user_email and not is_admin_action:
        return redirect('/index')

    delete_user_and_related_data(target_email)

    if target_email == user_email:
        session.clear()
        return redirect('/login')

    return redirect('/index')


@app.route('/admin/accounts', methods=['GET', 'POST'])
def admin_accounts():
    current_user = get_current_user()
    if current_user is None:
        return redirect('/login')
    if not current_user.is_admin:
        return redirect('/index')

    error = None
    message = None

    verified_email = session.get('admin_verified_email', '')
    search_query = request.args.get('search', '').strip()
    role_filter = request.args.get('role', '').strip()

    if request.method == 'POST':
        action = request.form.get('action', '').strip()
        target_email = request.form.get('target_email', '').strip().lower()
        target_user = User.query.filter_by(email=target_email).first() if target_email else None

        if action == 'verify_identity':
            security_code = request.form.get('security_code', '').strip()
            if target_user is None:
                error = 'Nie znaleziono użytkownika z podanym e-mailem'
            elif security_code != target_user.security_code:
                error = 'Kod zabezpieczający jest nieprawidłowy'
            else:
                session['admin_verified_email'] = target_email
                verified_email = target_email
                message = f'Tożsamość użytkownika {target_email} została potwierdzona'

        elif action == 'clear_verification':
            session.pop('admin_verified_email', None)
            verified_email = ''
            message = 'Weryfikacja została wyczyszczona'

        elif action == 'admin_change_password':
            if verified_email != target_email:
                error = 'Najpierw potwierdź tożsamość użytkownika przez e-mail i kod'
            elif target_user is None:
                error = 'Użytkownik nie istnieje'
            else:
                new_password = request.form.get('new_password', '')
                confirm_password = request.form.get('confirm_password', '')

                if len(new_password) < 6:
                    error = 'Nowe hasło musi mieć co najmniej 6 znaków'
                elif new_password != confirm_password:
                    error = 'Nowe hasła nie są takie same'
                else:
                    target_user.password = new_password
                    db.session.commit()
                    message = f'Hasło dla {target_email} zostało zmienione'

        elif action == 'admin_reset_codes':
            if verified_email != target_email:
                error = 'Najpierw potwierdź tożsamość użytkownika przez e-mail i kod'
            elif target_user is None:
                error = 'Użytkownik nie istnieje'
            else:
                reset_security_code(target_user)
                message = (
                    f'Kod zabezpieczający dla {target_email} został zresetowany. '
                    f'Nowy kod zabezpieczający: {target_user.security_code}'
                )

        elif action == 'admin_delete_messages_unverified':
            if target_user is None:
                error = 'Użytkownik nie istnieje'
            else:
                deleted_count = delete_user_messages(target_email)
                message = f'Usunięto wiadomości użytkownika {target_email}: {deleted_count}'

        elif action == 'admin_delete_account':
            confirm_text = request.form.get('confirm_text', '').strip()
            if verified_email != target_email:
                error = 'Najpierw potwierdź tożsamość użytkownika przez e-mail i kod'
            elif target_user is None:
                error = 'Użytkownik nie istnieje'
            elif target_email == current_user.email:
                error = 'Nie możesz usunąć swojego konta z panelu admina'
            elif confirm_text != 'USUN':
                error = 'Aby usunąć konto, wpisz dokładnie: USUN'
            else:
                delete_user_and_related_data(target_email)
                session.pop('admin_verified_email', None)
                verified_email = ''
                message = f'Konto {target_email} zostało usunięte'

        elif action == 'admin_toggle_role':
            if verified_email != target_email:
                error = 'Najpierw potwierdź tożsamość użytkownika przez e-mail i kod'
            elif target_user is None:
                error = 'Użytkownik nie istnieje'
            elif target_email == current_user.email:
                error = 'Nie możesz zmienić własnej roli z panelu admina'
            else:
                target_user.is_admin = not target_user.is_admin
                db.session.commit()
                role_name = 'administratorem' if target_user.is_admin else 'zwykłym użytkownikiem'
                message = f'{target_email} jest teraz {role_name}'

        elif action == 'admin_logout_user':
            if verified_email != target_email:
                error = 'Najpierw potwierdź tożsamość użytkownika przez e-mail i kod'
            elif target_user is None:
                error = 'Użytkownik nie istnieje'
            elif target_email == current_user.email:
                error = 'Nie możesz wylogować siebie z panelu admina'
            else:
                target_user.session_token = ''
                target_user.session_expires_at = None
                db.session.commit()
                message = f'Wszystkie sesje użytkownika {target_email} zostały zakończone'

    users_query = User.query
    if search_query:
        users_query = users_query.filter(or_(User.email.ilike(f'%{search_query}%'), User.name.ilike(f'%{search_query}%')))
    if role_filter == 'admin':
        users_query = users_query.filter_by(is_admin=True)
    elif role_filter == 'user':
        users_query = users_query.filter_by(is_admin=False)
    users = users_query.order_by(User.email.asc()).all()
    verified_user = User.query.filter_by(email=verified_email).first() if verified_email else None
    stats = {
        'users': User.query.count(),
        'admins': User.query.filter_by(is_admin=True).count(),
        'published_cards': Card.query.filter_by(is_draft=False).count(),
        'drafts': Card.query.filter_by(is_draft=True).count(),
        'comments': Comment.query.count(),
        'messages': PrivateMessage.query.count(),
    }

    return render_template(
        'admin_accounts.html',
        users=users,
        verified_email=verified_email,
        verified_user=verified_user,
        error=error,
        message=message,
        stats=stats,
        search_query=search_query,
        role_filter=role_filter,
    )
    
@app.route('/index')
def index():
    selected_action_type = request.args.get('action_type', '').strip()
    selected_city = request.args.get('city', '').strip()

    cards_query = Card.query.filter_by(is_draft=False)
    if selected_action_type:
        cards_query = cards_query.filter(Card.action_type == selected_action_type)
    if selected_city:
        cards_query = cards_query.filter(Card.city.ilike(f'%{selected_city}%'))

    cards = cards_query.order_by(Card.id.desc()).all()
    current_user_email = session.get('user_email')
    my_cards = [card for card in cards if card.user_email == current_user_email]
    other_cards = [card for card in cards if card.user_email != current_user_email]
    participation_counts = {
        card.id: Participation.query.filter_by(card_id=card.id).count()
        for card in cards
    }
    joined_card_ids = {
        participation.card_id
        for participation in Participation.query.filter_by(user_email=current_user_email).all()
    } if current_user_email else set()

    return render_template(
        'index.html',
        cards=cards,
        my_cards=my_cards,
        other_cards=other_cards,
        participation_counts=participation_counts,
        joined_card_ids=joined_card_ids,
        action_types=ACTION_TYPES,
        selected_action_type=selected_action_type,
        selected_city=selected_city,
    )

# Uruchomienie strony z kartą
@app.route('/card/<int:id>')
def card(id):
    #Zadanie #2. Wyświetl właściwą kartę według jej identyfikatora
    card = Card.query.get(id)
    if card is None:
        return redirect('/index')

    comments = Comment.query.filter_by(card_id=id).order_by(Comment.created_at.desc()).all()
    participation_count = Participation.query.filter_by(card_id=id).count()
    has_joined = Participation.query.filter_by(
        card_id=id,
        user_email=session.get('user_email')
    ).first() is not None
    participants = Participation.query.filter_by(card_id=id).order_by(Participation.created_at.desc()).all()

    return render_template(
        'card.html',
        card=card,
        comments=comments,
        participation_count=participation_count,
        has_joined=has_joined,
        participants=participants,
    )


@app.route('/join_card/<int:id>', methods=['POST'])
def join_card(id):
    user_email = session.get('user_email')
    if not user_email:
        return redirect('/login')

    card = Card.query.get(id)
    if card is None:
        return redirect('/index')

    user_name = session.get('user_name') or user_email.split('@')[0]

    existing_participation = Participation.query.filter_by(card_id=id, user_email=user_email).first()
    if existing_participation is not None:
        db.session.delete(existing_participation)
    else:
        participation = Participation(card_id=id, user_name=user_name, user_email=user_email)
        db.session.add(participation)
    db.session.commit()

    next_url = request.form.get('next', '').strip()
    if next_url in ('/index', f'/card/{id}'):
        return redirect(next_url)
    return redirect(f'/card/{id}')


@app.route('/remove_participant/<int:id>', methods=['POST'])
def remove_participant(id):
    participation = Participation.query.get(id)
    current_user = get_current_user()
    if participation is None or current_user is None:
        return redirect('/index')

    card = Card.query.get(participation.card_id)
    if card is None or not can_manage_card(card, current_user):
        return redirect('/index')

    db.session.delete(participation)
    db.session.commit()
    return redirect(f'/card/{card.id}')


@app.route('/comment_card/<int:id>', methods=['POST'])
def comment_card(id):
    user_email = session.get('user_email')
    if not user_email:
        return redirect('/login')

    card = Card.query.get(id)
    if card is None:
        return redirect('/index')

    user_name = session.get('user_name') or user_email.split('@')[0]

    text = request.form.get('text', '').strip()
    if text:
        comment = Comment(card_id=id, user_name=user_name, user_email=user_email, text=text)
        db.session.add(comment)
        db.session.commit()

    return redirect(f'/card/{id}')


@app.route('/delete_comment/<int:id>', methods=['POST'])
def delete_comment(id):
    comment = Comment.query.get(id)
    current_user = get_current_user()
    if comment is None or current_user is None:
        return redirect('/index')

    card = Card.query.get(comment.card_id)
    can_delete = (
        current_user.is_admin
        or comment.user_email == current_user.email
        or (card is not None and card.user_email == current_user.email)
    )
    if can_delete:
        db.session.delete(comment)
        db.session.commit()

    return redirect(f'/card/{comment.card_id}')


@app.route('/delete_card/<int:id>', methods=['POST'])
def delete_card(id):
    card = Card.query.get(id)
    if card is None:
        return redirect('/index')

    if not can_manage_card(card):
        return redirect('/index')

    # Usuń powiązane aktywności, aby po karcie nie zostały osierocone rekordy.
    Comment.query.filter_by(card_id=id).delete()
    Participation.query.filter_by(card_id=id).delete()
    db.session.delete(card)
    db.session.commit()
    return redirect('/index')

# Uruchomienie strony i utworzenie karty
@app.route('/create')
def create():
    user_email = session.get('user_email')
    if not user_email:
        return redirect('/login')

    selected_draft_id = request.args.get('draft_id', '').strip()
    draft = None

    if selected_draft_id.isdigit():
        draft = Card.query.filter_by(
            id=int(selected_draft_id),
            user_email=user_email,
            is_draft=True,
        ).first()

    return render_template(
        'create_card.html',
        action_types=ACTION_TYPES,
        draft=draft,
        draft_saved=request.args.get('draft_saved') == '1',
    )


@app.route('/edit_card/<int:id>')
def edit_card(id):
    current_user = get_current_user()
    card = Card.query.get(id)
    if current_user is None:
        return redirect('/login')
    if card is None or not can_manage_card(card, current_user):
        return redirect('/index')

    return render_template(
        'create_card.html',
        action_types=ACTION_TYPES,
        draft=card,
        editing=True,
        draft_saved=False,
    )

# Formularz karty
@app.route('/form_create', methods=['GET','POST'])
def form_create():
    if request.method == 'POST':
        if not session.get('user_email'):
            return redirect('/login')

        submit_action = request.form.get('submit_action', 'publish')

        if submit_action == 'cancel':
            return redirect('/index')

        title = request.form['title']
        subtitle = request.form['subtitle']
        text = request.form['text']
        action_type = request.form.get('action_type', 'Pomysł')
        city = request.form.get('city', '').strip()
        user_email = session.get('user_email')
        user_name = session.get('user_name') or user_email.split('@')[0]
        draft_id = request.form.get('draft_id', '').strip()
        card_id = request.form.get('card_id', '').strip()
        draft_card = None

        if card_id.isdigit():
            editable_card = Card.query.filter_by(id=int(card_id)).first()
            if editable_card is None or not can_manage_card(editable_card):
                return redirect('/index')
            editable_card.title = title
            editable_card.subtitle = subtitle
            editable_card.text = text
            editable_card.action_type = action_type
            editable_card.city = city
            db.session.commit()
            return redirect(f'/card/{editable_card.id}')

        if draft_id.isdigit():
            draft_card = Card.query.filter_by(id=int(draft_id), user_email=user_email, is_draft=True).first()

        if submit_action == 'save_draft':
            if draft_card is None:
                draft_card = Card(
                    title=title,
                    subtitle=subtitle,
                    text=text,
                    user_name=user_name,
                    user_email=user_email,
                    action_type=action_type,
                    city=city,
                    is_draft=True,
                )
                db.session.add(draft_card)
            else:
                draft_card.title = title
                draft_card.subtitle = subtitle
                draft_card.text = text
                draft_card.action_type = action_type
                draft_card.city = city

            db.session.commit()
            return redirect('/create?draft_saved=1')

        if draft_card is not None:
            draft_card.title = title
            draft_card.subtitle = subtitle
            draft_card.text = text
            draft_card.action_type = action_type
            draft_card.city = city
            draft_card.is_draft = False
            draft_card.user_name = user_name
            card = draft_card
        else:
            card = Card(
                title=title,
                subtitle=subtitle,
                text=text,
                user_name=user_name,
                user_email=user_email,
                action_type=action_type,
                city=city,
                is_draft=False,
            )
            db.session.add(card)

        db.session.commit()

        return redirect('/index')
    else:
        return redirect('/create')


@app.route('/info')
def info():
    return render_template('info.html')

 
if __name__ == "__main__":
    app.run(debug=True)