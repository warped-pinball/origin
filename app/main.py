from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from .database import Base, engine, run_migrations
from .routers import auth, users, machines, scores
from .version import __version__
import os

# Run migrations before ensuring all tables exist
run_migrations()
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
            <link rel='stylesheet' href='https://fonts.googleapis.com/icon?family=Material+Icons'>
            <style>
                .error {{ color: red; font-size: small; }}
            </style>
            <script>
                function toggleTheme() {{
                    const html = document.documentElement;
                    const newTheme = html.dataset.theme === 'dark' ? 'light' : 'dark';
                    html.dataset.theme = newTheme;
                    const icon = document.getElementById('theme-icon');
                    if (icon) {{
                        icon.textContent = newTheme === 'dark' ? 'light_mode' : 'dark_mode';
                    }}
                }}

                function showToast(msg, type = 'info') {{
                    const toast = document.getElementById('toast');
                    const icon = type === 'error' ? '❌' : type === 'success' ? '✅' : 'ℹ️';
                    toast.textContent = `${{icon}} ${{msg}}`;
                    toast.style.background = type === 'error' ? '#b91c1c' : type === 'success' ? '#15803d' : '#333';
                    toast.style.display = 'block';
                    setTimeout(() => toast.style.display = 'none', 3000);
                }}

                async function signup(e) {{
                    e.preventDefault();
                    const email = document.getElementById('signup-email').value;
                    const password = document.getElementById('signup-password').value;
                    const screen_name = document.getElementById('signup-screen').value;
                    const first_name = document.getElementById('signup-first').value;
                    const last_name = document.getElementById('signup-last').value;
                    const res = await fetch('/api/v1/users/', {{
                        method: 'POST',
                        headers: {{'Content-Type': 'application/json'}},
                        body: JSON.stringify({{email, password, screen_name, first_name, last_name}})
                    }});
                    if (res.ok) {{
                        const loginRes = await fetch('/api/v1/auth/token', {{
                            method: 'POST',
                            headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
                            body: new URLSearchParams({{username: email, password}})
                        }});
                        closeSignup();
                        if (loginRes.ok) {{
                            const data = await loginRes.json();
                            localStorage.setItem('token', data.access_token);
                            showLoggedIn();
                            showToast('Account created', 'success');
                        }} else {{
                            showToast('Account created but login failed', 'error');
                            showLogin();
                        }}
                    }} else if (res.status === 422) {{
                        const emailInput = document.getElementById('signup-email');
                        emailInput.setCustomValidity('Please enter a valid email address.');
                        emailInput.reportValidity();
                    }} else {{
                        showToast('Signup failed', 'error');
                    }}
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
                        document.getElementById('login-error').textContent = '';
                        showLoggedIn();
                    }} else if (res.status >= 500) {{
                        showToast('Server error', 'error');
                    }} else {{
                        document.getElementById('login-error').textContent = 'Login failed';
                    }}
                }}

                function logout() {{
                    localStorage.removeItem('token');
                    showLogin();
                }}

                function openSignup(e) {{
                    e.preventDefault();
                    document.getElementById('signup-dialog').showModal();
                }}

                function closeSignup() {{
                    document.getElementById('signup-dialog').close();
                    const emailInput = document.getElementById('signup-email');
                    if (emailInput) {{
                        emailInput.setCustomValidity('');
                    }}
                    document.getElementById('signup-email-error').textContent = '';
                }}

                function showLogin() {{
                    document.getElementById('login-section').style.display = 'block';
                    document.getElementById('loggedin-section').style.display = 'none';
                    document.getElementById('login-error').textContent = '';
                }}

                function showLoggedIn() {{
                    document.getElementById('login-section').style.display = 'none';
                    document.getElementById('loggedin-section').style.display = 'block';
                }}

                function checkAuth() {{
                    localStorage.getItem('token') ? showLoggedIn() : showLogin();
                }}

                document.addEventListener('DOMContentLoaded', () => {{
                    checkAuth();
                    const emailInput = document.getElementById('signup-email');
                    if (emailInput) {{
                        emailInput.addEventListener('input', () => emailInput.setCustomValidity(''));
                    }}
                }});
            </script>
        </head>
        <body>
            <main class='container'>
                <h1>Origin</h1>
                <button onclick='toggleTheme()' aria-label='Toggle theme' style='position:fixed;top:1rem;right:1rem;width:2rem;height:2rem;display:flex;align-items:center;justify-content:center;'>
                    <span id='theme-icon' class='material-icons'>light_mode</span>
                </button>
                <section id='login-section'>
                    <article>
                        <h2>Login</h2>
                        <form onsubmit='login(event)'>
                            <input id='login-email' type='text' placeholder='Email' required />
                            <input id='login-password' type='password' placeholder='Password' required />
                            <button type='submit'>Log In</button>
                            <span id='login-error' class='error'></span>
                        </form>
                        <small>Don't have an account? <a href='#' onclick='openSignup(event)'>Sign Up</a></small>
                    </article>
                </section>
                <dialog id='signup-dialog'>
                    <article>
                        <h3>Create Account</h3>
                        <form onsubmit='signup(event)'>
                            <input id='signup-email' type='email' placeholder='Email' required />
                            <span id='signup-email-error' class='error'></span>
                            <input id='signup-screen' type='text' placeholder='Screen name' required />
                            <input id='signup-first' type='text' placeholder='First name' required />
                            <input id='signup-last' type='text' placeholder='Last name' required />
                            <input id='signup-password' type='password' placeholder='Password' required />
                            <footer>
                                <button type='submit'>Create Account</button>
                                <button type='button' onclick='closeSignup()' class='secondary'>Cancel</button>
                            </footer>
                        </form>
                    </article>
                </dialog>
                <section id='loggedin-section' style='display:none;'>
                    <h2>You are logged in</h2>
                    <button onclick='logout()'>Logout</button>
                </section>
                <div id='toast' class='toast' style='display:none;position:fixed;bottom:1rem;right:1rem;background:#333;color:white;padding:0.5rem 1rem;border-radius:4px;z-index:1000;'></div>
            </main>
            <footer style='margin-top:20px;text-align:center;'>Version {__version__}</footer>
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

