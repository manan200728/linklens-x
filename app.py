from flask import Flask, request, redirect, render_template, jsonify, session
import sqlite3, string, random
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ---------- DATABASE ----------
def get_db():
    return sqlite3.connect("database.db")

def init_db():
    con = get_db()
    c = con.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS urls(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        original TEXT,
        short TEXT UNIQUE,
        clicks INTEGER DEFAULT 0,
        created_at TEXT,
        expiry TEXT
    )
    """)

    con.commit()
    con.close()

init_db()

# ---------- HELPERS ----------
def generate_short():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=6))

def get_insight(clicks):
    if clicks > 50:
        return "🔥 Trending"
    elif clicks > 20:
        return "🚀 Growing"
    elif clicks > 5:
        return "👍 Moderate"
    else:
        return "⚠️ Low"

# ---------- AUTH ----------
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            con = get_db()
            c = con.cursor()
            c.execute("INSERT INTO users(username,password) VALUES (?,?)",
                      (username, password))
            con.commit()
            con.close()
            return redirect('/login')
        except:
            return "User already exists"

    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        con = get_db()
        c = con.cursor()
        c.execute("SELECT id FROM users WHERE username=? AND password=?",
                  (username, password))
        user = c.fetchone()
        con.close()

        if user:
            session['user_id'] = user[0]
            return redirect('/')
        return "Invalid credentials"

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# ---------- HOME ----------
@app.route('/', methods=['GET','POST'])
def index():
    if 'user_id' not in session:
        return redirect('/login')

    short = None

    if request.method == 'POST':
        url = request.form['url']
        custom = request.form['custom']
        expiry = request.form['expiry']

        if not url.startswith("http"):
            return "Invalid URL"

        short_code = custom if custom else generate_short()

        try:
            con = get_db()
            c = con.cursor()
            c.execute("""
                INSERT INTO urls(user_id, original, short, created_at, expiry)
                VALUES (?, ?, ?, ?, ?)
            """, (session['user_id'], url, short_code, datetime.now().isoformat(), expiry))
            con.commit()
            con.close()
            short = short_code
        except:
            return "Short link already exists"

    return render_template('index.html', short=short)

# ---------- REDIRECT ----------
@app.route('/<short>')
def redirect_url(short):
    con = get_db()
    c = con.cursor()

    c.execute("SELECT original, clicks, expiry FROM urls WHERE short=?", (short,))
    data = c.fetchone()

    if not data:
        return "Link not found"

    original, clicks, expiry = data

    if expiry:
        if datetime.now() > datetime.fromisoformat(expiry):
            return "Link expired"

    c.execute("UPDATE urls SET clicks=? WHERE short=?", (clicks + 1, short))
    con.commit()
    con.close()

    return redirect(original)

# ---------- DASHBOARD ----------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    con = get_db()
    c = con.cursor()

    c.execute("""
        SELECT original, short, clicks, created_at
        FROM urls WHERE user_id=?
    """, (session['user_id'],))

    data = c.fetchall()
    con.close()

    enriched = []
    for row in data:
        insight = get_insight(row[2])
        enriched.append((*row, insight))

    return render_template('dashboard.html', data=enriched)

# ---------- API ----------
@app.route('/api')
def api():
    con = get_db()
    c = con.cursor()
    c.execute("SELECT short, clicks FROM urls")
    data = c.fetchall()
    con.close()
    return jsonify(data)

# ---------- RUN ----------
if __name__ == "__main__":
    app.run()