# Import
from flask import Flask, render_template, request, redirect, session, jsonify
# Importowanie biblioteki bazy danych
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text, and_, or_
from datetime import datetime
import os
import secrets
import string


app = Flask(__name__)
# Podłączanie SQLite

app.secret_key = 'jabfjbveou45201'

# Upewnij się, że folder instance istnieje i użyj jednej, jawnej ścieżki do bazy.
os.makedirs(app.instance_path, exist_ok=True)
db_path = os.path.join(app.instance_path, 'diary.db')

app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{db_path}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# Creating a DB
db = SQLAlchemy(app)

ACTION_TYPES = ['Pomysł', 'Marsz', 'Strajk', 'Pomoc', 'Sprzątanie', 'Inne']
PRIVATE_CODE_CHARS = string.ascii_uppercase + string.digits
PRIVATE_CODE_LENGTH = 8

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
    is_admin = db.Column(db.Boolean, nullable=False, default=False)

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
    ensure_column('user', 'is_admin', "ALTER TABLE user ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0")
    ensure_column('card', 'user_name', "ALTER TABLE card ADD COLUMN user_name VARCHAR(120) NOT NULL DEFAULT ''")
    ensure_column('card', 'action_type', "ALTER TABLE card ADD COLUMN action_type VARCHAR(80) NOT NULL DEFAULT 'Pomysł'")
    ensure_column('card', 'city', "ALTER TABLE card ADD COLUMN city VARCHAR(120) NOT NULL DEFAULT ''")
    ensure_column('card', 'is_draft', "ALTER TABLE card ADD COLUMN is_draft BOOLEAN NOT NULL DEFAULT 0")
    ensure_column('comment', 'user_name', "ALTER TABLE comment ADD COLUMN user_name VARCHAR(120) NOT NULL DEFAULT ''")
    ensure_column('participation', 'user_name', "ALTER TABLE participation ADD COLUMN user_name VARCHAR(120) NOT NULL DEFAULT ''")

    users_with_codes = User.query.order_by(User.id.asc()).all()
    assigned_codes = set()
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

    db.session.commit()
    db.session.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_user_private_code ON user(private_code)"))
    db.session.commit()


def generate_private_code():
    while True:
        code = ''.join(secrets.choice(PRIVATE_CODE_CHARS) for _ in range(PRIVATE_CODE_LENGTH))
        if not User.query.filter_by(private_code=code).first():
            return code


def get_current_user():
    user_email = session.get('user_email')
    if not user_email:
        return None
    return User.query.filter_by(email=user_email).first()


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
    if partner.email == current_user_email:
        return None, 'Nie możesz pisać wiadomości do samego siebie.'
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
        'created_at': message.created_at.strftime('%Y-%m-%d %H:%M:%S'),
    }

@app.route('/', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        form_login = request.form['email']
        form_password = request.form['password']
        user = User.query.filter_by(email=form_login, password=form_password).first()
        if user:
            session['user_email'] = user.email
            session['user_name'] = user.name or user.email.split('@')[0]
            session['is_admin'] = bool(user.is_admin)
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
        new_user = User(name=name, email=email, password=password, private_code=generate_private_code())
        db.session.add(new_user)
        db.session.commit()
        session['user_email'] = email
        session['user_name'] = name
        session['is_admin'] = False
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

    if request.method == 'POST':
        new_name = request.form.get('name', '').strip()
        if not new_name:
            drafts = Card.query.filter_by(user_email=user_email, is_draft=True).order_by(Card.id.desc()).all()
            return render_template('account.html', user=user, drafts=drafts, error='Podaj nick')

        user.name = new_name
        session['user_name'] = new_name
        db.session.commit()
        return redirect('/account')

    drafts = Card.query.filter_by(user_email=user_email, is_draft=True).order_by(Card.id.desc()).all()
    draft_error = request.args.get('draft_error') == '1'
    return render_template('account.html', user=user, drafts=drafts, draft_error=draft_error)


@app.route('/private_chat')
def private_chat():
    current_user = get_current_user()
    if current_user is None:
        return redirect('/login')

    partner_code = request.args.get('code', '').strip().upper()
    partner_user = None
    chat_error = None
    messages = []

    if partner_code:
        partner_user, chat_error = get_chat_partner_by_code(partner_code, current_user.email)
        if partner_user is not None:
            raw_messages = private_chat_query(current_user.email, partner_user.email).order_by(PrivateMessage.id.asc()).all()
            messages = [serialize_private_message(message, current_user.email) for message in raw_messages]

    return render_template(
        'private_chat.html',
        current_user=current_user,
        partner_code=partner_code,
        partner_user=partner_user,
        chat_error=chat_error,
        messages=messages,
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
    )
    db.session.add(message)
    db.session.commit()

    return jsonify({'ok': True, 'message': serialize_private_message(message, current_user.email)})


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
    session.clear()
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

    user = User.query.filter_by(email=target_email).first()
    if user is not None:
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

    if target_email == user_email:
        session.clear()
        return redirect('/login')

    return redirect('/index')
    
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

    return render_template(
        'index.html',
        cards=cards,
        my_cards=my_cards,
        other_cards=other_cards,
        participation_counts=participation_counts,
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
    if existing_participation is None:
        participation = Participation(card_id=id, user_name=user_name, user_email=user_email)
        db.session.add(participation)
        db.session.commit()

    return redirect(f'/card/{id}')


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
        draft_card = None

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

 
if __name__ == "__main__":
    app.run(debug=True)