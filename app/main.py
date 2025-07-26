from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from .database import Base, engine
from .routers import auth, users, machines, scores
from .version import __version__
import os

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Origin")

@app.get("/", response_class=HTMLResponse)
def read_root():
    return f"""
    <!doctype html>
    <html data-theme='dark'>
        <head>
            <meta charset='utf-8'>
            <meta name='viewport' content='width=device-width,initial-scale=1'>
            <title>Origin</title>
            <link rel='stylesheet' href='https://unpkg.com/@picocss/pico@1.*/css/pico.min.css'>
            <script>
                function toggleTheme() {{
                    const html = document.documentElement;
                    html.dataset.theme = html.dataset.theme === 'dark' ? 'light' : 'dark';
                }}

                async function signup(e) {{
                    e.preventDefault();
                    const email = document.getElementById('signup-email').value;
                    const password = document.getElementById('signup-password').value;
                    const res = await fetch('/api/v1/users/', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{email, password}})
                    }});
                    alert(res.ok ? 'Account created' : 'Signup failed');
                }}

                async function login(e) {{
                    e.preventDefault();
                    const email = document.getElementById('login-email').value;
                    const password = document.getElementById('login-password').value;
                    const body = new URLSearchParams({{username: email, password}});
                    const res = await fetch('/api/v1/auth/token', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
                        body
                    }});
                    if (res.ok) {{
                        const data = await res.json();
                        localStorage.setItem('token', data.access_token);
                        showLoggedIn();
                    }} else {{
                        alert('Login failed');
                    }}
                }}

                function logout() {{
                    localStorage.removeItem('token');
                    showLogin();
                }}

                function showLogin() {{
                    document.getElementById('login-section').style.display = 'block';
                    document.getElementById('loggedin-section').style.display = 'none';
                }}

                function showLoggedIn() {{
                    document.getElementById('login-section').style.display = 'none';
                    document.getElementById('loggedin-section').style.display = 'block';
                }}

                function checkAuth() {{
                    localStorage.getItem('token') ? showLoggedIn() : showLogin();
                }}

                document.addEventListener('DOMContentLoaded', checkAuth);
            </script>
        </head>
        <body>
            <main class='container'>
                <h1>Origin</h1>
                <button onclick='toggleTheme()' style='float:right'>Toggle Theme</button>
                <section id='login-section'>
                    <h2>Create Account</h2>
                    <form onsubmit='signup(event)'>
                        <input id='signup-email' type='email' placeholder='Email' required />
                        <input id='signup-password' type='password' placeholder='Password' required />
                        <button type='submit'>Sign Up</button>
                    </form>
                    <h2>Login</h2>
                    <form onsubmit='login(event)'>
                        <input id='login-email' type='text' placeholder='Email' required />
                        <input id='login-password' type='password' placeholder='Password' required />
                        <button type='submit'>Log In</button>
                    </form>
                </section>
                <section id='loggedin-section' style='display:none;'>
                    <h2>You are logged in</h2>
                    <button onclick='logout()'>Logout</button>
                </section>
                <p style='margin-top:20px;font-size:small;'>Version {__version__}</p>
            </main>
        </body>
    </html>
    """

# Mount static files for universal links
static_dir = os.path.join(os.path.dirname(__file__), 'static/.well-known')
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)
app.mount('/.well-known', StaticFiles(directory=static_dir), name='static')

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(machines.router, prefix="/api/v1")
app.include_router(scores.router, prefix="/api/v1")

@app.get("/api/v1/version")
def get_version():
    return {"version": __version__}

