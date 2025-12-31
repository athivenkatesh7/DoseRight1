from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from functools import wraps

# Create Blueprint for authentication
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Database helper functions
def get_db_connection():
    conn = sqlite3.connect('doseright.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_auth_db():
    """Initialize authentication database tables"""
    conn = get_db_connection()
    c = conn.cursor()
    
    # Create users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  email TEXT UNIQUE,
                  password_hash TEXT NOT NULL,
                  full_name TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Create default admin user
    try:
        admin_hash = generate_password_hash('admin123')
        c.execute("INSERT OR IGNORE INTO users (username, email, password_hash, full_name) VALUES (?, ?, ?, ?)",
                  ('admin', 'admin@doseright.com', admin_hash, 'Administrator'))
    except:
        pass
    
    conn.commit()
    conn.close()

# Decorator for login required
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Context processor to make user info available in templates
def auth_context_processor():
    user_info = {}
    if 'user_id' in session:
        conn = get_db_connection()
        user = conn.execute('SELECT id, username, email, full_name FROM users WHERE id = ?', 
                           (session['user_id'],)).fetchone()
        conn.close()
        if user:
            user_info = {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'full_name': user['full_name'],
                'is_authenticated': True
            }
    return dict(current_user=user_info)

# Routes
@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        full_name = request.form.get('full_name', '').strip()
        
        # Validation
        errors = []
        if not username:
            errors.append('Username is required')
        if not email:
            errors.append('Email is required')
        if not password:
            errors.append('Password is required')
        if password != confirm_password:
            errors.append('Passwords do not match')
        if len(password) < 6:
            errors.append('Password must be at least 6 characters')
        
        if errors:
            return render_template('signup.html', errors=errors)
        
        try:
            conn = get_db_connection()
            # Check if username or email already exists
            existing_user = conn.execute('SELECT id FROM users WHERE username = ? OR email = ?',
                                        (username, email)).fetchone()
            if existing_user:
                conn.close()
                return render_template('signup.html', errors=['Username or email already exists'])
            
            # Create new user
            password_hash = generate_password_hash(password)
            conn.execute('''INSERT INTO users (username, email, password_hash, full_name)
                          VALUES (?, ?, ?, ?)''',
                        (username, email, password_hash, full_name))
            conn.commit()
            
            # Get the new user's ID
            user = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
            conn.close()
            
            # Set session
            session['user_id'] = user['id']
            session['username'] = username
            session['logged_in'] = True
            
            return redirect(url_for('index'))
            
        except Exception as e:
            print(f"Signup error: {e}")
            return render_template('signup.html', errors=['An error occurred during signup'])
    
    return render_template('signup.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        if not username or not password:
            return render_template('login.html', error='Username and password are required')
        
        try:
            conn = get_db_connection()
            user = conn.execute('SELECT id, username, password_hash FROM users WHERE username = ?',
                               (username,)).fetchone()
            conn.close()
            
            if user and check_password_hash(user['password_hash'], password):
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['logged_in'] = True
                
                if remember:
                    session.permanent = True
                else:
                    session.permanent = False
                
                next_page = request.args.get('next')
                return redirect(next_page or url_for('index'))
            else:
                return render_template('login.html', error='Invalid username or password')
                
        except Exception as e:
            print(f"Login error: {e}")
            return render_template('login.html', error='An error occurred during login')
    
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@auth_bp.route('/profile')
@login_required
def profile():
    conn = get_db_connection()
    user = conn.execute('SELECT username, email, full_name, created_at FROM users WHERE id = ?',
                       (session['user_id'],)).fetchone()
    
    # Get scan statistics
    stats = conn.execute('''SELECT COUNT(*) as total_scans, 
                           MAX(timestamp) as last_scan 
                           FROM scan_history WHERE user_id = ?''',
                        (session['user_id'],)).fetchone()
    
    conn.close()
    
    # Prepare stats for template
    stats_dict = {
        'total_scans': stats['total_scans'] if stats and stats['total_scans'] else 0,
        'last_scan': stats['last_scan'][:10] if stats and stats['last_scan'] else 'Never'
    }
    
    return render_template('profile.html', user=user, stats=stats_dict)

# Initialize database when module is imported
init_auth_db()