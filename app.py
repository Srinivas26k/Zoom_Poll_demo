# app.py
<<<<<<< HEAD
from flask import Flask, redirect, url_for, session, request, render_template, flash
import requests, base64, threading, os, time
=======
from flask import Flask, redirect, url_for, session, request, render_template, flash, jsonify
import requests, base64, threading, os, time, webbrowser, secrets
>>>>>>> bcc4988 (Initial commit of Zoom Poll Automator project, including core functionality for audio capture, transcription, poll generation, and integration with Zoom API. Added CLI interface, web interface, and setup scripts. Configured logging and environment management. Included necessary dependencies and documentation.)
from rich.console import Console
from run_loop import run_loop
import config
from audio_capture import list_audio_devices
<<<<<<< HEAD
=======
import sys
from urllib.parse import urlencode, quote
import os
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
>>>>>>> bcc4988 (Initial commit of Zoom Poll Automator project, including core functionality for audio capture, transcription, poll generation, and integration with Zoom API. Added CLI interface, web interface, and setup scripts. Configured logging and environment management. Included necessary dependencies and documentation.)

console = Console()

app = Flask(__name__)
<<<<<<< HEAD
app.secret_key = config.SECRET_TOKEN or os.urandom(24)  # Fallback for secret key
=======

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
>>>>>>> bcc4988 (Initial commit of Zoom Poll Automator project, including core functionality for audio capture, transcription, poll generation, and integration with Zoom API. Added CLI interface, web interface, and setup scripts. Configured logging and environment management. Included necessary dependencies and documentation.)

# Initialize global variables
automation_thread = None
should_stop = threading.Event()

<<<<<<< HEAD
# ─── 1) Home: OAuth or Setup ────────────────────────────────────────────────────
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
    
    if "zoom_token" in session:
        return redirect(url_for("setup"))
    return render_template("index.html")

# ─── 2) Start OAuth ─────────────────────────────────────────────────────────────
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

# ─── 3) OAuth callback ──────────────────────────────────────────────────────────
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
            token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)  # Default to 1 hour
            session["zoom_token"] = token
            session["token_expiry"] = time.time() + expires_in
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

# ─── 4) Setup page ──────────────────────────────────────────────────────────────
@app.route("/setup", methods=["GET","POST"])
def setup():
    global automation_thread
    
    if "zoom_token" not in session:
        return redirect(url_for("index"))
    
    # Check if token is still valid
    if "token_expiry" in session and time.time() > session["token_expiry"]:
        console.log("[yellow]⚠️ Zoom token expired, redirecting to login[/]")
        session.pop("zoom_token", None)
        session.pop("token_expiry", None)
        return redirect(url_for("index"))

=======
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
    if not is_token_valid():
        if 'refresh_token' in session:
            if not refresh_access_token():
                clear_oauth_session()
                return render_template("index.html", authorized=False)
        else:
            return render_template("index.html", authorized=False)
    
    return render_template("index.html", authorized=True)

@app.route("/authorize")
def authorize():
    try:
        # Clear any existing OAuth session data
        clear_oauth_session()
        
        # Generate a secure state token
        state = secrets.token_urlsafe(32)
        session['oauth_state'] = state
        
        # Construct the authorization URL with proper encoding
        params = {
            'response_type': 'code',
            'client_id': CLIENT_ID,
            'redirect_uri': REDIRECT_URI,
            'state': state
        }
        
        # Properly encode the parameters
        auth_url = f"{AUTH_URL}?{urlencode(params)}"
        log.info(f"Starting OAuth flow with state: {state}")
        return redirect(auth_url)
    except Exception as e:
        log.error(f"Authorization error: {str(e)}")
        flash("Failed to start authorization process")
        return redirect(url_for('index'))

@app.route("/oauth/callback")
def oauth_callback():
    try:
        # Check for error in callback
        if 'error' in request.args:
            error = request.args.get('error')
            log.error(f"OAuth error: {error}")
            flash(f"Authorization failed: {error}")
            return redirect(url_for('index'))

        # Verify state parameter
        state = request.args.get('state')
        stored_state = session.get('oauth_state')
        
        if not state or not stored_state:
            log.error("Missing state parameter")
            flash("Authorization failed: Missing state parameter")
            return redirect(url_for('index'))
            
        if state != stored_state:
            log.error(f"State mismatch: received={state}, stored={stored_state}")
            flash("Authorization failed: Invalid state parameter")
            return redirect(url_for('index'))

        # Get the authorization code
        code = request.args.get('code')
        if not code:
            log.error("No authorization code received")
            flash("Authorization failed: No code received")
            return redirect(url_for('index'))

        # Exchange code for token
        token_data = {
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': REDIRECT_URI
        }

        response = requests.post(
            TOKEN_URL,
            auth=(CLIENT_ID, CLIENT_SECRET),
            data=token_data
        )
        response.raise_for_status()
        
        # Store tokens in session
        token_info = response.json()
        session['access_token'] = token_info['access_token']
        session['refresh_token'] = token_info.get('refresh_token')
        session['token_expires_at'] = time.time() + token_info.get('expires_in', 3600)
        
        # Clear the state after successful token exchange
        session.pop('oauth_state', None)
        
        log.info("Successfully obtained access token")
        flash("Successfully authorized with Zoom")
        return redirect(url_for('setup'))
        
    except requests.exceptions.RequestException as e:
        log.error(f"Token exchange failed: {str(e)}")
        flash("Failed to exchange authorization code for token")
        return redirect(url_for('index'))
    except Exception as e:
        log.error(f"Unexpected error during OAuth callback: {str(e)}")
        flash("An unexpected error occurred during authorization")
        return redirect(url_for('index'))

@app.route("/logout")
def logout():
    clear_oauth_session()
    flash("Successfully logged out")
    return redirect(url_for('index'))

@app.route("/setup", methods=["GET", "POST"])
def setup():
    global automation_thread
    
    if not is_token_valid():
        if 'refresh_token' in session:
            if not refresh_access_token():
                return redirect(url_for('authorize'))
        else:
            return redirect(url_for('authorize'))
    
>>>>>>> bcc4988 (Initial commit of Zoom Poll Automator project, including core functionality for audio capture, transcription, poll generation, and integration with Zoom API. Added CLI interface, web interface, and setup scripts. Configured logging and environment management. Included necessary dependencies and documentation.)
    if request.method == "POST":
        try:
            # Validate meeting ID
            meeting_id = request.form.get("meeting_id", "").strip()
            if not meeting_id:
                flash("Meeting ID is required")
                return redirect(url_for("setup"))
            
<<<<<<< HEAD
        device = request.form["device"]
<<<<<<< HEAD
        zoom_token = session["zoom_token"]
=======
>>>>>>> bcc4988 (Initial commit of Zoom Poll Automator project, including core functionality for audio capture, transcription, poll generation, and integration with Zoom API. Added CLI interface, web interface, and setup scripts. Configured logging and environment management. Included necessary dependencies and documentation.)
=======
            # Validate duration
            try:
                duration = int(request.form.get("duration", "60"))
                if duration < 10 or duration > 300:
                    flash("Duration must be between 10 and 300 seconds")
                    return redirect(url_for("setup"))
            except ValueError:
                flash("Duration must be a valid number")
                return redirect(url_for("setup"))
            
            # Get and validate device
            device_name = request.form.get("device", "").strip()
            if not device_name:
                flash("Audio device is required")
                return redirect(url_for("setup"))
            
            device = get_device_by_name(device_name)
            if not device:
                flash(f"Selected audio device '{device_name}' not found")
                return redirect(url_for("setup"))
>>>>>>> 4fcc7f5 (Enhance setup functionality by adding device validation and error handling. Introduce a new function to retrieve audio devices by name. Refactor meeting ID and duration validation logic for improved user feedback. Maintain existing thread management for automation tasks.)

            console.log(f"🚀 Starting automation: meeting={meeting_id}, dur={duration}s, dev={device_name}")
            
            # Stop existing thread if running
            if automation_thread and automation_thread.is_alive():
                console.log("[yellow]⚠️ Stopping existing automation thread[/]")
                should_stop.set()  # Signal the thread to stop
                # Give time for thread to clean up
                time.sleep(2)
                should_stop.clear()  # Reset the flag for next thread
            
            # Test Ollama connection before starting thread
            try:
                # Direct API test to Ollama
                ollama_url = f"{config.OLLAMA_API}/api/tags"
                console.log(f"Testing Ollama connection: {ollama_url}")
                r = requests.get(ollama_url, timeout=5)
                if not r.ok:
                    error_msg = f"Failed to connect to Ollama API: {r.status_code} {r.text}"
                    console.log(f"[red]❌ {error_msg}[/]")
                    flash(error_msg)
                    return redirect(url_for("setup"))
                    
                # Verify llama3.2 model is available
                models = r.json().get("models", [])
                llama_available = any("llama3.2" in model.get("name", "") for model in models)
                if not llama_available:
                    console.log("[yellow]⚠️ llama3.2 model not found, you may need to pull it[/]")
                    flash("Warning: llama3.2 model not found in Ollama. Run 'ollama pull llama3.2' first.")
                else:
                    console.log("[green]✅ Successfully connected to Ollama and found llama3.2 model[/]")
            except Exception as e:
                error_msg = f"Failed to connect to Ollama at {config.OLLAMA_API}: {str(e)}"
                console.log(f"[red]❌ {error_msg}[/]")
                flash(error_msg)
                return redirect(url_for("setup"))
            
            # launch background loop
            automation_thread = threading.Thread(
                target=run_loop,
                args=(session["access_token"], meeting_id, duration, device, should_stop),
                daemon=True
            )
            automation_thread.start()
            return render_template("started.html")
            
        except Exception as e:
            log.error(f"Error starting automation: {str(e)}")
            flash(f"Failed to start automation: {str(e)}")
            return redirect(url_for("setup"))
<<<<<<< HEAD
        
        # launch background loop
        automation_thread = threading.Thread(
            target=run_loop,
<<<<<<< HEAD
            args=(zoom_token, meeting_id, duration, device, should_stop),
=======
            args=(session["access_token"], meeting_id, duration, device, should_stop),
>>>>>>> bcc4988 (Initial commit of Zoom Poll Automator project, including core functionality for audio capture, transcription, poll generation, and integration with Zoom API. Added CLI interface, web interface, and setup scripts. Configured logging and environment management. Included necessary dependencies and documentation.)
            daemon=True
        )
        automation_thread.start()
        return render_template("started.html")
=======
>>>>>>> 4fcc7f5 (Enhance setup functionality by adding device validation and error handling. Introduce a new function to retrieve audio devices by name. Refactor meeting ID and duration validation logic for improved user feedback. Maintain existing thread management for automation tasks.)

    # List available audio devices for the UI
    try:
        devices = list_audio_devices()
<<<<<<< HEAD
    except Exception as e:
        console.log(f"[yellow]⚠️ Could not list audio devices: {e}[/]")
        devices = []
=======
        # Format device names for display
        formatted_devices = []
        for device in devices:
            if isinstance(device, dict):
                name = device.get('name', 'Unknown Device')
            else:
                name = str(device)
            formatted_devices.append(name)
    except Exception as e:
        console.log(f"[yellow]⚠️ Could not list audio devices: {e}[/]")
        formatted_devices = []
>>>>>>> bcc4988 (Initial commit of Zoom Poll Automator project, including core functionality for audio capture, transcription, poll generation, and integration with Zoom API. Added CLI interface, web interface, and setup scripts. Configured logging and environment management. Included necessary dependencies and documentation.)
    
    # GET
    return render_template(
        "setup.html",
<<<<<<< HEAD
        token=session["zoom_token"],
        devices=devices
    )

@app.route("/stop")
def stop():
    global should_stop
    should_stop.set()  # Signal the thread to stop
    flash("Automation has been signaled to stop.")
    return redirect(url_for("setup"))

if __name__ == "__main__":
    console.log("[green]Zoom Poll Automator starting...[/]")
    console.log(f"Access the web interface at: {config.REDIRECT_URI.split('/oauth')[0]}")
    app.run(host="0.0.0.0", port=8000)
=======
        token=session["access_token"],
        devices=formatted_devices
    )

@app.route("/stop", methods=["POST"])
def stop():
    global should_stop
    should_stop.set()  # Signal the thread to stop
    flash("Automation has been stopped.")
    return redirect(url_for("setup"))

@app.route("/health")
def health_check():
    """Health check endpoint to verify the app is running"""
    return {"status": "ok", "message": "Zoom Poll Automator is running"}

@app.route("/meetings")
def list_meetings():
    if not is_token_valid():
        return redirect(url_for('authorize'))
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/users/me/meetings",
            headers={"Authorization": f"Bearer {session['access_token']}"}
        )
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        log.error(f"Failed to fetch meetings: {str(e)}")
        return jsonify({"error": "Failed to fetch meetings"}), 500

def open_browser():
    """Open the browser after a short delay"""
    time.sleep(1.5)
    webbrowser.open("http://localhost:8000")

if __name__ == "__main__":
    console.log("[green]Zoom Poll Automator starting...[/]")
    server_url = REDIRECT_URI.split('/oauth')[0]
    console.log(f"Access the web interface at: {server_url}")
    
    # Check if we should automatically open the browser
    if "--no-browser" not in sys.argv:
        threading.Thread(target=open_browser, daemon=True).start()
    
    app.run(host="0.0.0.0", port=8000, debug=False)
>>>>>>> bcc4988 (Initial commit of Zoom Poll Automator project, including core functionality for audio capture, transcription, poll generation, and integration with Zoom API. Added CLI interface, web interface, and setup scripts. Configured logging and environment management. Included necessary dependencies and documentation.)
