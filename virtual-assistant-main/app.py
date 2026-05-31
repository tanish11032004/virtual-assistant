# Standard library imports
import os
import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Tuple, Any, Dict

# Third-party imports
from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, jsonify, session, g
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from flask_cors import CORS
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from flask_login import (
    LoginManager, UserMixin, login_user,
    login_required, logout_user, current_user
)
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
import structlog
from celery import Celery
from flasgger import Swagger
import bleach
import sympy as sp
from googletrans import Translator, LANGUAGES

# Local imports
from config import config_by_name
from utils.decorators import log_execution_time
from services.bot import chatbot_response
from forms.auth import LoginForm, RegistrationForm
from utils.algorithms import LRUCache, SearchOptimizer, PriorityQueue
from utils.optimizers import QueryOptimizer

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Custom error classes (defined early so handlers/factory can reference them)
# ---------------------------------------------------------------------------
class APIError(Exception):
    """Application-level API error with an HTTP status code."""
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code

# ---------------------------------------------------------------------------
# In-memory data structures
# ---------------------------------------------------------------------------
user_cache = LRUCache(capacity=1000)
query_cache = LRUCache(capacity=500)
task_queue = PriorityQueue()

# ---------------------------------------------------------------------------
# Extensions (created unbound, initialised inside create_app)
# ---------------------------------------------------------------------------
mysql = MySQL()
bcrypt = Bcrypt()
cache = Cache()
login_manager = LoginManager()
csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per day", "50 per hour"])
translator = Translator()
celery = Celery(
    __name__,
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
)


def create_app(config_name: str = None) -> Flask:
    """
    Application factory.

    Args:
        config_name: One of 'development', 'production', 'testing'.

    Returns:
        A fully configured Flask application.
    """
    config_name = config_name or os.getenv('FLASK_ENV', 'development')

    app = Flask(__name__, template_folder='templates')
    app.config.from_object(config_by_name[config_name])

    # Environment overrides
    app.secret_key = os.getenv('SECRET_KEY', app.config.get('SECRET_KEY', 'your_default_secret_key'))
    app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', app.config.get('MYSQL_HOST', 'localhost'))
    app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', app.config.get('MYSQL_USER', 'root'))
    app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', app.config.get('MYSQL_PASSWORD', ''))
    app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', app.config.get('MYSQL_DB', 'virtual_assistant_users'))

    app.config.setdefault('CACHE_TYPE', 'SimpleCache')
    app.config.setdefault('CACHE_DEFAULT_TIMEOUT', 300)

    # Initialise extensions against this app
    mysql.init_app(app)
    bcrypt.init_app(app)
    cache.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    csrf.init_app(app)
    limiter.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    Swagger(app)

    # Performance-related config
    app.config['SQLALCHEMY_ECHO'] = False
    app.config['SQLALCHEMY_POOL_SIZE'] = 10
    app.config['SQLALCHEMY_POOL_TIMEOUT'] = 30

    # Celery picks up the (possibly overridden) broker URL
    celery.conf.update(broker_url=app.config.get('CELERY_BROKER_URL', celery.conf.broker_url))

    _register_error_handlers(app)
    return app


def _register_error_handlers(app: Flask) -> None:
    """Register application error handlers."""

    @app.errorhandler(APIError)
    def handle_api_error(error: APIError) -> Tuple[Any, int]:
        return jsonify({'error': error.message}), error.status_code

    @app.errorhandler(Exception)
    def handle_exception(error: Exception) -> Tuple[Any, int]:
        logging.error(f"Exception occurred: {str(error)}", exc_info=True)
        return jsonify({'error': f'An internal error occurred: {str(error)}'}), 500


# Create the application instance
app = create_app()


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
@app.before_request
def log_request_info():
    if not request.path.startswith('/static'):
        logging.info(f'Request: {request.method} {request.path} from {request.remote_addr}')


@app.before_request
def check_session_lifetime():
    if 'user_id' in session:
        session.permanent = True
        app.permanent_session_lifetime = timedelta(minutes=30)


def sanitize_input(f):
    """
    Sanitise incoming form values with bleach.

    Note: request.form is immutable, so the cleaned values are stored on
    flask.g.clean_form for handlers that want them, rather than mutating
    request.form (which would raise).
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.form:
            g.clean_form = {k: bleach.clean(v) for k, v in request.form.items()}
        return f(*args, **kwargs)
    return decorated_function


def validate_json_request(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.is_json:
            try:
                request.get_json()
            except Exception:
                raise APIError("Invalid JSON payload", 400)
        return f(*args, **kwargs)
    return decorated_function


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
class User(UserMixin):
    pass


@login_manager.user_loader
def load_user(user_id):
    with mysql.connection.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        if user:
            user_obj = User()
            user_obj.id = user[0]
            return user_obj
    return None


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        password = form.password.data
        hashed_password = generate_password_hash(password)

        with mysql.connection.cursor() as cur:
            try:
                cur.execute("SELECT * FROM users WHERE username = %s OR email = %s", (username, email))
                if cur.fetchone():
                    return jsonify({'success': False, 'message': 'Username or email already exists'}), 400

                cur.execute("INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                            (username, email, hashed_password))
                mysql.connection.commit()
                return jsonify({'success': True}), 200

            except Exception as e:
                mysql.connection.rollback()
                logging.error(f"Database error: {e}")
                return jsonify({'success': False, 'message': 'Database error occurred'}), 500

    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        with mysql.connection.cursor() as cur:
            try:
                cur.execute("SELECT * FROM users WHERE username = %s", (username,))
                user = cur.fetchone()

                if user and check_password_hash(user[3], password):
                    user_obj = User()
                    user_obj.id = user[0]
                    login_user(user_obj)
                    session['user_id'] = user[0]
                    return redirect(url_for('dashboard'))
                else:
                    flash('Invalid username or password', 'danger')

            except Exception as err:
                logging.error(f"Error: {err}")
                flash('Database error occurred', 'danger')

    return render_template('login.html', form=form)


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@cache.memoize(timeout=300)
def get_dashboard_data(user_id: int) -> Dict[str, Any]:
    """Optimised dashboard data retrieval."""
    cached_data = user_cache.get(f"dashboard_{user_id}")
    if cached_data:
        return cached_data

    with mysql.connection.cursor() as cur:
        query = QueryOptimizer.optimize_select(
            fields=['username', 'email'],
            table='users',
            conditions={'id': user_id}
        )
        cur.execute(query, (user_id,))
        data = cur.fetchone()

        if data:
            user_cache.put(f"dashboard_{user_id}", data)
        return data


@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session.get('user_id')
    try:
        user_data = get_dashboard_data(user_id)
        if user_data:
            return render_template('dashboard.html', username=user_data[0], email=user_data[1])
        raise APIError("User data not found", 404)
    except APIError:
        raise
    except Exception as e:
        logger.error("dashboard_error", error=str(e), user_id=user_id)
        raise APIError("Failed to load dashboard", 500)


@app.route('/activity')
@login_required
def activity():
    return "This is the activity page."


@app.route('/forgot_password', methods=['GET'])
def forgot_password():
    return render_template('forgot_password.html')


@app.route('/calendar')
@login_required
def calendar():
    return render_template('calendar.html')


@app.route('/index')
def index():
    try:
        logging.info("Attempting to render index.html")
        return render_template('index.html', languages=LANGUAGES)
    except Exception as e:
        logging.error(f"Error in index route: {str(e)}", exc_info=True)
        return f"An error occurred: {str(e)}", 500


@app.route('/calculator', methods=['GET', 'POST'])
@login_required
def calculator():
    result = None
    if request.method == 'POST':
        expression = request.form.get('expression')
        if expression:
            try:
                result = sp.sympify(expression).evalf()
            except Exception as e:
                flash(f"Error in calculation: {e}", 'danger')
        else:
            flash('Please enter an expression.', 'danger')

    return render_template('calculator.html', result=result)


@app.route('/language', methods=['GET', 'POST'])
def translator_page():
    if request.method == 'POST':
        input_language = request.form.get('input_language')
        output_language = request.form.get('output_language')
        text_to_translate = request.form.get('text_to_translate')

        if not text_to_translate:
            return jsonify({'error': 'Please enter text to translate.'})

        if input_language not in LANGUAGES or output_language not in LANGUAGES:
            return jsonify({'error': 'Invalid language selected.'})

        try:
            translated = translator.translate(text_to_translate, src=input_language, dest=output_language)
            return jsonify({'translated_text': translated.text})
        except Exception as e:
            logging.error(f"Translation error: {str(e)}")
            return jsonify({'error': 'An error occurred during translation. Please try again.'})

    return render_template('Translator/translator.html', languages=LANGUAGES)


# ---------------------------------------------------------------------------
# Background tasks
# ---------------------------------------------------------------------------
@celery.task
def process_chat_history(user_id, chat_content):
    """Process and analyse chat history (placeholder)."""
    return None


@app.route('/chat_bot', methods=['GET', 'POST'])
@login_required
@limiter.limit("10 per minute")
@sanitize_input
@validate_json_request
def chat_bot():
    """
    Chat Bot Endpoint
    ---
    parameters:
      - name: user_input
        in: body
        required: true
        schema:
          type: object
          properties:
            message:
              type: string
    responses:
      200:
        description: Bot response
    """
    if request.method == 'POST':
        user_input = request.form.get('user_input')
        if not user_input:
            raise APIError("Empty input not allowed")

        logger.info("chat_request", user_id=current_user.id, input=user_input)

        task_queue.push(
            lambda: process_chat_history.delay(current_user.id, user_input),
            priority=1
        )

        try:
            bot_response = chatbot_response(user_input)
            return jsonify({
                'response': bot_response,
                'timestamp': datetime.now().isoformat()
            })
        except Exception as e:
            logger.error("chatbot_error", error=str(e))
            raise APIError("Failed to generate response", 500)

    return render_template('bot.html')


@app.route('/notepad', methods=['GET', 'POST'])
@login_required
def notepad():
    if request.method == 'POST':
        note_content = request.form.get('note_content')
        if note_content:
            with mysql.connection.cursor() as cur:
                try:
                    cur.execute("INSERT INTO notes (user_id, content) VALUES (%s, %s)",
                                (session['user_id'], note_content))
                    mysql.connection.commit()
                    flash('Note saved successfully!', 'success')
                except Exception as e:
                    mysql.connection.rollback()
                    logging.error(f"Error saving note: {e}")
                    flash('Error saving note. Please try again.', 'danger')
        else:
            flash('Please enter a note before saving.', 'danger')
        return redirect(url_for('notepad'))

    return render_template('notepad.html')


@app.route('/api/v1/notes', methods=['GET', 'POST'])
@login_required
@limiter.limit("60 per hour")
@sanitize_input
def api_notes():
    if request.method == 'POST':
        content = request.form.get('content')
        if not content:
            raise APIError("Note content is required")

        with mysql.connection.cursor() as cur:
            try:
                cur.execute(
                    "INSERT INTO notes (user_id, content, created_at) VALUES (%s, %s, %s)",
                    (current_user.id, content, datetime.now())
                )
                mysql.connection.commit()
                return jsonify({'status': 'success', 'message': 'Note created'})
            except Exception as e:
                mysql.connection.rollback()
                raise APIError(f"Database error: {str(e)}", 500)

    return jsonify({'error': 'Method not allowed'}), 405


@app.route('/api/v1/search', methods=['GET'])
@login_required
def search():
    """Optimised search endpoint."""
    query = request.args.get('q', '').lower()
    results = []

    with mysql.connection.cursor() as cur:
        cur.execute("SELECT id, content FROM searchable_content")
        for row in cur.fetchall():
            # row is a tuple: (id, content)
            if SearchOptimizer.fuzzy_search(row[1], query):
                results.append({'id': row[0], 'content': row[1]})

    return jsonify({'results': results[:10]})


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


@app.route('/api/v1/health')
@log_execution_time
def health_check() -> Tuple[Any, int]:
    """Health check endpoint with detailed status."""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'services': {
            'database': check_database_connection(),
            'cache': check_cache_connection(),
            'celery': check_celery_status()
        }
    }), 200


def check_database_connection() -> bool:
    try:
        mysql.connection.ping()
        return True
    except Exception as e:
        logger.error("database_connection_error", error=str(e))
        return False


def check_cache_connection() -> bool:
    try:
        cache.get('health_check')
        return True
    except Exception as e:
        logger.error("cache_connection_error", error=str(e))
        return False


def check_celery_status() -> bool:
    try:
        celery.control.ping()
        return True
    except Exception as e:
        logger.error("celery_connection_error", error=str(e))
        return False


@app.route('/')
def home():
    return redirect(url_for('index'))


@app.route('/user_guide')
def user_guide():
    return render_template('user_guide.html')


@app.route('/terms')
def terms():
    return render_template('terms.html')


@app.route('/privacy')
def privacy():
    return render_template('privacy.html')


@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')


@app.route('/activity_log')
@login_required
def activity_log():
    try:
        with mysql.connection.cursor() as cur:
            cur.execute("""
                SELECT activity, created_at, status, details
                FROM activity_logs
                WHERE user_id = %s
                ORDER BY created_at DESC
            """, (current_user.id,))
            activities = cur.fetchall()
        return render_template('activity_log.html', activities=activities)
    except Exception as e:
        logger.error("activity_log_error", error=str(e))
        raise APIError("Failed to load activity log", 500)


def log_user_activity(user_id, activity, status='complete', details=None):
    """Log user activity to database."""
    try:
        with mysql.connection.cursor() as cur:
            cur.execute("""
                INSERT INTO activity_logs (user_id, activity, status, details, created_at)
                VALUES (%s, %s, %s, %s, NOW())
            """, (user_id, activity, status, details))
            mysql.connection.commit()
    except Exception as e:
        logger.error("activity_log_error", error=str(e))
        mysql.connection.rollback()


def process_background_tasks():
    """Process queued background tasks in priority order."""
    while not task_queue.is_empty():
        task = task_queue.pop()
        try:
            task()
        except Exception as e:
            logger.error(f"Task processing error: {e}")


# Catch-all must be registered last so it doesn't shadow real routes.
@app.route('/<path:path>')
def catch_all(path):
    logging.warning(f"Attempted to access undefined route: /{path}")
    return "Page not found", 404


if __name__ == '__main__':
    app.run(
        host=os.getenv('FLASK_HOST', '0.0.0.0'),
        port=int(os.getenv('FLASK_PORT', 5000)),
        debug=app.config.get('DEBUG', False)
    )
