# app.py

from flask import Flask, redirect, url_for, session, request, render_template, flash, jsonify
import requests, base64, threading, os, time, webbrowser, secrets
from rich.console import Console
from run_loop import run_loop
import config
from audio_capture import list_audio_devices
import sys
from urllib.parse import urlencode, quote
from dotenv import load_dotenv
import logging
from rich.logging import RichHandler
from datetime import timedelta

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
log = logging.getLogger("rich")
console = Console()

app = Flask(__name__)

# Load environment variables
load_dotenv()

# Configure Flask secret key and session
if not os.getenv("FLASK_SECRET_KEY"):
    secret_key = secrets.token_hex(32)
    with open(".env", "a") as f:
        f.write(f"\nFLASK_SECRET_KEY={secret_key}")
    log.info("[+] Flask secret key configured")
else:
    log.info("[+] Flask secret key loaded from configuration.")

app.secret_key = os.getenv("FLASK_SECRET_KEY")
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialize global variables
automation_thread = None
should_stop = threading.Event()

# Zoom OAuth configuration
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/oauth/callback")
AUTH_URL = "https://zoom.us/oauth/authorize"
TOKEN_URL = "https://zoom.us/oauth/token"
API_BASE_URL = "https://api.zoom.us/v2"

def get_device_by_name(device_name):
    """Get the full device object by name"""
    try:
        devices = list_audio_devices()
        for device in devices:
            if isinstance(device, dict) and device.get('name') == device_name:
                return device
            elif str(device) == device_name:
                return device
        return None
    except Exception as e:
        log.error(f"Error getting device by name: {str(e)}")
        return None

def clear_oauth_session():
    """Clear OAuth related session data"""
    session.pop('oauth_state', None)
    session.pop('access_token', None)
    session.pop('refresh_token', None)
    session.pop('token_expires_at', None)

def is_token_valid():
    """Check if the current access token is valid"""
    if 'access_token' not in session:
        return False
    
    # Check if token has expired
    if 'token_expires_at' in session:
        if time.time() >= session['token_expires_at']:
            return False
    
    # Verify token with Zoom API
    try:
        response = requests.get(
            f"{API_BASE_URL}/users/me",
            headers={"Authorization": f"Bearer {session['access_token']}"}
        )
        return response.status_code == 200
    except Exception as e:
        log.error(f"Error verifying token: {str(e)}")
        return False

def refresh_access_token():
    """Refresh the access token using refresh token"""
    if 'refresh_token' not in session:
        return False
    
    try:
        response = requests.post(
            TOKEN_URL,
            auth=(CLIENT_ID, CLIENT_SECRET),
            data={
                'grant_type': 'refresh_token',
                'refresh_token': session['refresh_token']
            }
        )
        response.raise_for_status()
        
        token_info = response.json()
        session['access_token'] = token_info['access_token']
        session['refresh_token'] = token_info.get('refresh_token')
        session['token_expires_at'] = time.time() + token_info.get('expires_in', 3600)
        return True
    except Exception as e:
        log.error(f"Error refreshing token: {str(e)}")
        return False

@app.before_request
def make_session_permanent():
    session.permanent = True

@app.route("/")
def index():
    # Check if configuration is valid
    missing_config = []
    if not config.CLIENT_ID:
        missing_config.append("CLIENT_ID")
    if not config.CLIENT_SECRET:
        missing_config.append("CLIENT_SECRET")
    
    if missing_config:
        error_message = f"Missing required configuration: {', '.join(missing_config)}. Please update your .env file."
        console.log(f"[red]❌ {error_message}[/]")
        return render_template("error.html", error=error_message)
    
    if not is_token_valid():
        if 'refresh_token' in session:
            if not refresh_access_token():
                clear_oauth_session()
                return render_template("index.html", authorized=False)
        else:
            return render_template("index.html", authorized=False)
    
    return redirect(url_for("setup"))

@app.route("/authorize")
def authorize():
    # Verify configuration
    if not config.CLIENT_ID or not config.CLIENT_SECRET:
        error = "Missing CLIENT_ID or CLIENT_SECRET in .env file"
        console.log(f"[red]❌ {error}[/]")
        return render_template("error.html", error=error)
        
    scopes = "meeting:read:meeting_transcript meeting:read:list_meetings " \
             "meeting:read:poll meeting:read:token meeting:write:poll " \
             "meeting:update:poll user:read:zak zoomapp:inmeeting"
    params = {
        "response_type": "code",
        "client_id":     config.CLIENT_ID,
        "redirect_uri":  config.REDIRECT_URI,
        "scope":         scopes
    }
    url = "https://zoom.us/oauth/authorize"
    auth_url = f"{url}?{'&'.join(f'{k}={v}' for k,v in params.items())}"
    console.log(f"Redirecting to: {auth_url}")
    return redirect(auth_url)

@app.route("/oauth/callback")
def oauth_callback():
    code = request.args.get("code")
    error = request.args.get("error")
    
    if error:
        error_description = request.args.get("error_description", "Unknown error")
        console.log(f"[red]OAuth error: {error} - {error_description}[/]")
        return render_template("error.html", error=f"OAuth error: {error_description}")
        
    if not code:
        return render_template("error.html", error="No authorization code returned")

    # swap code for token
    token_url = "https://zoom.us/oauth/token"
    creds = f"{config.CLIENT_ID}:{config.CLIENT_SECRET}".encode()
    auth_header = base64.b64encode(creds).decode()
    headers = {
        "Authorization": f"Basic {auth_header}",
        "Content-Type":  "application/x-www-form-urlencoded"
    }
    data = {
        "grant_type":   "authorization_code",
        "code":         code,
        "redirect_uri": config.REDIRECT_URI
    }
    
    try:
        r = requests.post(token_url, headers=headers, data=data)
        if r.ok:
            token_data = r.json()
            session["access_token"] = token_data["access_token"]
            session["refresh_token"] = token_data.get("refresh_token")
            session["token_expires_at"] = time.time() + token_data.get("expires_in", 3600)
            console.log("[green]✅ Obtained Zoom access token[/]")
            return redirect(url_for("setup"))
        else:
            error_msg = f"Token error: {r.status_code} - {r.text}"
            console.log(f"[red]{error_msg}[/]")
            return render_template("error.html", error=error_msg)
    except Exception as e:
        error_msg = f"Error during token exchange: {str(e)}"
        console.log(f"[red]{error_msg}[/]")
        return render_template("error.html", error=error_msg)

@app.route("/logout")
def logout():
    clear_oauth_session()
    return redirect(url_for("index"))

@app.route("/setup", methods=["GET", "POST"])
def setup():
    global automation_thread
    
    if not is_token_valid():
        return redirect(url_for("index"))
    
    if request.method == "POST":
        device_name = request.form.get("device")
        if not device_name:
            flash("Please select an audio device", "error")
            return render_template("setup.html")
        
        device = get_device_by_name(device_name)
        if not device:
            flash("Invalid audio device selected", "error")
            return render_template("setup.html")
        
        # Start automation in a separate thread
        should_stop.clear()
        automation_thread = threading.Thread(
            target=run_loop,
            args=(device, should_stop),
            daemon=True
        )
        automation_thread.start()
        return redirect(url_for("started"))
    
    return render_template("setup.html")

@app.route("/stop", methods=["POST"])
def stop():
    global automation_thread
    if automation_thread and automation_thread.is_alive():
        should_stop.set()
        automation_thread.join(timeout=5)
        flash("Automation stopped successfully", "success")
    return redirect(url_for("setup"))

@app.route("/health")
def health_check():
    return jsonify({"status": "healthy"})

@app.route("/meetings")
def list_meetings():
    if not is_token_valid():
        return jsonify({"error": "Invalid or expired token"}), 401
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/users/me/meetings",
            headers={"Authorization": f"Bearer {session['access_token']}"}
        )
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def open_browser():
    """Open the default web browser to the application URL"""
    webbrowser.open('http://localhost:8000')

if __name__ == "__main__":
    # Open browser in a separate thread
    threading.Thread(target=open_browser).start()
    app.run(host="0.0.0.0", port=8000, debug=True)
