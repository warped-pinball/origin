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
    <html>
        <head>
            <title>Origin</title>
            <script>
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
                    alert(res.ok ? 'Logged in' : 'Login failed');
                }}
            </script>
        </head>
        <body>
            <h1>Welcome to Origin</h1>
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
            <p style='margin-top:20px;font-size:small;'>Version {__version__}</p>
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

