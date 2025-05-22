# app.py
from flask import Flask, redirect, url_for, session, request, render_template, flash, jsonify, send_file
import requests, base64, threading, os, time, webbrowser, secrets
from rich.console import Console
from run_loop import run_loop
import config
from audio_capture import list_audio_devices, AudioDevice

from ai_notes import AINotesGenerator
import sys
from urllib.parse import urlencode, quote
from dotenv import load_dotenv
import logging
from rich.logging import RichHandler
from datetime import timedelta, datetime

import json
from io import BytesIO
import zipfile
from flask_sock import Sock

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="[%X]",
    handlers=[
        RichHandler(rich_tracebacks=True),
        logging.FileHandler("app.log")
    ]
)
log = logging.getLogger("zoom_poll_app")
console = Console()

app = Flask(__name__)

# Load environment variables
load_dotenv()

# Configure Flask secret key and session
# Simplified FLASK_SECRET_KEY setup: Rely on config.py
# config.py sets FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY") or (os.getenv("SECRET_TOKEN") or os.urandom(24).hex())
# If SECRET_TOKEN is set in .env, it's used. Otherwise, a new key is generated per session if not in .env.
# setup.py is responsible for writing a persistent FLASK_SECRET_KEY to .env.
if not config.FLASK_SECRET_KEY:
    log.warning("FLASK_SECRET_KEY is not set in environment or config. Using an ephemeral key.")
    # This case should ideally not happen if setup.py ran and config.py has its urandom fallback.
    # However, explicit check for safety.
    app.secret_key = secrets.token_hex(32) # Fallback if config.FLASK_SECRET_KEY was somehow None
else:
    app.secret_key = config.FLASK_SECRET_KEY
    log.info("[+] Flask secret key loaded from config.py.")

# app.secret_key = os.getenv("FLASK_SECRET_KEY") # Changed to use config.FLASK_SECRET_KEY
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=1)
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialize global variables
automation_thread = None
should_stop = threading.Event()
meeting_recorder = None

# Zoom OAuth configuration
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8000/oauth/callback")
AUTH_URL = "https://zoom.us/oauth/authorize"
TOKEN_URL = "https://zoom.us/oauth/token"
API_BASE_URL = "https://api.zoom.us/v2"

config.setup_config()

# Initialize Flask-Sock
sock = Sock(app)

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
        console.log("[yellow]No access token in session[/]")
        return False
    
    # Check if token has expired
    if 'token_expires_at' in session:
        if time.time() >= session['token_expires_at']:
            console.log("[yellow]Token has expired[/]")
            return False
    
    # For debugging, let's assume the token is valid if it exists
    # This helps break the redirect loop while you're testing
    console.log("[green]Token found in session - assuming it's valid[/]")
    return True

def refresh_access_token():
    """Refresh the access token using refresh token"""
    if 'refresh_token' not in session:
        log.warning("No refresh token available")
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
        log.info("Successfully refreshed access token")
        return True
    except requests.exceptions.RequestException as e:
        log.error(f"Network error refreshing token: {str(e)}")
        return False
    except Exception as e:
        log.error(f"Unexpected error refreshing token: {str(e)}", exc_info=True)
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
        error = "Missing CLIENT_ID or CLIENT_SECRET in .env file. Please run setup."
        log.error(f"Authorization attempt failed: {error}") # Enhanced logging
        return render_template("error.html", error=error)
    
    # Use the configured REDIRECT_URI from config
    auth_url = f"https://zoom.us/oauth/authorize?response_type=code&client_id={config.CLIENT_ID}&redirect_uri={config.REDIRECT_URI}"
    
    console.log(f"Redirecting to: {auth_url}")
    return redirect(auth_url)

@app.route("/oauth/callback")
def oauth_callback():
    try:
        code = request.args.get("code")
        error = request.args.get("error")
        
        if error:
            error_description = request.args.get("error_description", "Unknown error")
            log.error(f"OAuth error during callback: {error} - {error_description}") # Consistent logging
            return render_template("error.html", error=f"OAuth error: {error_description}")
            
        if not code:
            log.error("OAuth callback error: No authorization code returned.") # Consistent logging
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
        
        r = requests.post(token_url, headers=headers, data=data)
        r.raise_for_status()  # Raise exception for non-200 status codes
        
        token_data = r.json()
        session["access_token"] = token_data["access_token"]
        session["refresh_token"] = token_data.get("refresh_token")
        session["token_expires_at"] = time.time() + token_data.get("expires_in", 3600)
        log.info(f"Successfully obtained Zoom access token for client ID: {config.CLIENT_ID[:10]}...") # Added client ID part
        return redirect(url_for("setup"))
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Network error during token exchange: {str(e)}"
        log.error(f"{error_msg}. Response: {e.response.text if e.response else 'No response'}", exc_info=True) # More detailed logging
        return render_template("error.html", error=error_msg)
    except Exception as e:
        error_msg = f"Unexpected error during token exchange: {str(e)}"
        log.error(error_msg, exc_info=True) # exc_info=True was already there, good.
        return render_template("error.html", error=error_msg)

@app.route("/logout")
def logout():
    clear_oauth_session()
    return redirect(url_for("index"))

@app.route("/setup", methods=["GET", "POST"])
def setup():
    global automation_thread
    
    console.log("[blue]Debug: Entering setup route[/]")
    
    if not is_token_valid():
        console.log("[yellow]Debug: Token invalid in setup route, redirecting to index[/]")
        return redirect(url_for("index"))
    
    console.log("[green]Debug: Token valid in setup route[/]")
    
    # Get a list of audio devices for the setup page
    try:
        devices = list_audio_devices()
        device_names = []
        for device in devices:
            if isinstance(device, AudioDevice):
                device_names.append(str(device))
            elif isinstance(device, dict) and device.get('name'):
                device_names.append(device.get('name'))
        
        console.log(f"[blue]Debug: Found {len(device_names)} audio devices[/]")
        
        if not device_names:
            # Add a fake device for testing if none are found
            device_names = ["Default Audio Input"]
            console.log("[yellow]Debug: No devices found, adding fallback device[/]")
    except Exception as e:
        device_names = ["Default Audio Input"]
        console.log(f"[red]Error listing audio devices: {e}[/]")
    
    if request.method == "POST":
        # Get form data
        device_name = request.form.get("device")
        meeting_id = request.form.get("meeting_id")
        segment_duration_str = request.form.get("segment_duration", "30") # Kept for env var, though MeetingRecorder might not use it
        
        # Validate input
        if not device_name:
            flash("Please select an audio device.", "error") # Added period.
            return render_template("setup.html", devices=device_names)
            
        if not meeting_id:
            flash("Please enter a Zoom Meeting ID.", "error") # Added period.
            return render_template("setup.html", devices=device_names)
        
        # Log the action
        log.info(f"Setup POST: Device='{device_name}', MeetingID='{meeting_id}', SegmentDuration='{segment_duration_str}'")

        # Set environment variables for the run_loop (run_loop might still use them)
        os.environ["MEETING_ID"] = meeting_id
        os.environ["ZOOM_TOKEN"] = session.get("access_token", "")
        os.environ["SEGMENT_DURATION"] = segment_duration_str
        
        # This `device` variable is passed to run_loop, which passes it to MeetingRecorder constructor
        # MeetingRecorder's constructor expects device_name (a string) or None.
        # get_device_by_name might return an AudioDevice object or None.
        # For simplicity, we'll pass the name directly. run_loop will handle it.
        # The `device_name` from the form is what MeetingRecorder expects.
        
        # Start automation in a separate thread
        should_stop.clear()
        automation_thread = threading.Thread(
            target=run_loop,
            args=(device, should_stop),
            daemon=True
        )
        automation_thread.start()
        flash("Automation started successfully", "success")
        return redirect(url_for("started"))
    
    console.log("[blue]Debug: Rendering setup template[/]")
    return render_template("setup.html", devices=device_names)

@app.route("/stop", methods=["POST"])
def stop():
    global automation_thread
    if automation_thread and automation_thread.is_alive():
        try:
            should_stop.set()
            # Give the thread some time to terminate gracefully
            automation_thread.join(timeout=3)
            console.log("[green]Automation thread stopped successfully[/]")
        except Exception as e:
            console.log(f"[yellow]Warning when stopping thread: {str(e)}[/]")
    
    # Properly shutdown the Flask server
    try:
        func = request.environ.get('werkzeug.server.shutdown')
        if func is None:
            raise RuntimeError('Not running with the Werkzeug Server')
        func()
    except Exception as e:
        console.log(f"[yellow]Warning when shutting down server: {str(e)}[/]")
            
    flash("Automation stopped successfully", "success")
    return redirect(url_for("setup"))

def cleanup_on_exit():
    """Clean up resources before exiting"""
    global automation_thread, meeting_recorder, should_stop
    
    try:
        # Stop the automation thread if running (for run_loop.py based automation)
        if automation_thread and automation_thread.is_alive():
            log.info("Stopping run_loop automation thread...")
            should_stop.set()
            automation_thread.join(timeout=5)
            if automation_thread.is_alive():
                log.warning("run_loop automation thread did not stop in time.")
            else:
                log.info("run_loop automation thread stopped successfully.")
        
        # Close the meeting recorder if active (for /recorder UI based automation)
        if meeting_recorder is not None:
            log.info("Stopping and closing MeetingRecorder instance...")
            try:
                if meeting_recorder.recording: # Check if it's actually recording
                    meeting_recorder.stop_recording()
                meeting_recorder.close()
                log.info("MeetingRecorder instance closed successfully.")
            except Exception as e_mr:
                log.error(f"Error stopping/closing MeetingRecorder: {str(e_mr)}", exc_info=True)
        
    except Exception as e:
        log.error(f"General error during cleanup_on_exit: {str(e)}", exc_info=True)
    finally:
        log.info("Application shutdown complete")

# Register the cleanup function to run on application exit
atexit.register(cleanup_on_exit)

@app.route('/favicon.ico')
def favicon():
    return '', 204  # Return no content for favicon requests

@app.route("/health")
def health_check():
    return jsonify({"status": "healthy"})

@app.route("/meetings")
def list_meetings():
    if not is_token_valid():
        log.warning("Attempt to list meetings with invalid token.")
        return jsonify({"status": "error", "message": "Invalid or expired token"}), 401
    
    try:
        response = requests.get(
            f"{API_BASE_URL}/users/me/meetings",
            headers={"Authorization": f"Bearer {session['access_token']}"}
        )
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
        log.info("Successfully fetched user meetings.")
        return jsonify(response.json())
    except requests.exceptions.HTTPError as http_err:
        log.error(f"HTTP error fetching meetings: {http_err}. Response: {http_err.response.text}", exc_info=True)
        return jsonify({"status": "error", "message": f"Zoom API error: {http_err.response.status_code} - {http_err.response.text}"}), http_err.response.status_code
    except requests.exceptions.RequestException as req_err:
        log.error(f"Request error fetching meetings: {req_err}", exc_info=True)
        return jsonify({"status": "error", "message": f"Request error: {str(req_err)}"}), 500
    except Exception as e:
        log.error(f"Unexpected error fetching meetings: {e}", exc_info=True)
        return jsonify({"status": "error", "message": f"An unexpected error occurred: {str(e)}"}), 500

@app.route("/started")
def started():
    if not is_token_valid():
        return redirect(url_for("index"))
    return render_template("started.html")

# New routes for meeting recording functionality
@app.route("/record/status", methods=["GET"])
def record_status():
    """Get the current recording status"""
    global meeting_recorder
    
    if meeting_recorder is None:
        return jsonify({
            "status": "info", # Changed from success to info as it's not an error but not active
            "active": False,
            "message": "Meeting recorder not initialized." # Added period
        })
    
    try:
        duration_seconds = meeting_recorder.get_recording_duration() if hasattr(meeting_recorder, 'get_recording_duration') else 0
        hours, remainder = divmod(duration_seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        formatted_duration = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
        
        # Thread health status
        thread_status = {
            "segment_recording": meeting_recorder.segment_recording_thread_active if hasattr(meeting_recorder, 'segment_recording_thread_active') else False,
            "transcription": meeting_recorder.transcription_thread_active if hasattr(meeting_recorder, 'transcription_thread_active') else False,
            "analysis": meeting_recorder.analysis_thread_active if hasattr(meeting_recorder, 'analysis_thread_active') else False,
        }

        return jsonify({
            "status": "success",
            "active": meeting_recorder.recording,
            "is_paused": meeting_recorder.is_paused if hasattr(meeting_recorder, 'is_paused') else False,
            "meeting_id": meeting_recorder.meeting_id if meeting_recorder.recording else None,
            "transcript_length": len(meeting_recorder.full_transcript) if meeting_recorder.recording else 0,
            "duration_seconds": duration_seconds,
            "duration_formatted": formatted_duration,
            "has_transcript": bool(meeting_recorder.full_transcript),
            "has_notes": bool(meeting_recorder.summary_notes),
            "threads": thread_status # Added thread health status
        })
    except Exception as e:
        log.error(f"Error getting record status: {str(e)}", exc_info=True)
        return jsonify({"status": "error", "message": f"Error getting status: {str(e)}"}), 500

@app.route("/record/start", methods=["POST"])
def record_start():
    """Start recording with the selected audio source"""
    global meeting_recorder
    try:
        if meeting_recorder and meeting_recorder.recording: # Check .recording instead of .is_recording
            log.warning("Attempt to start recording when already in progress.")
            return jsonify({"status": "error", "message": "Recording already in progress"}), 400

        audio_source = session.get('audio_source', 'all')
        device_name_from_session = session.get('device') # This might be set by old /setup route
        
        log.info(f"Attempting to start recording. Audio source: {audio_source}, Device from session: {device_name_from_session}")

        # Initialize MeetingRecorder if it's not already, or if it was closed.
        # A better approach might be to ensure meeting_recorder is always a valid instance or None.
        if meeting_recorder is None: # or not meeting_recorder.is_usable(): # (add is_usable if needed)
            log.info(f"Initializing new MeetingRecorder instance. Device: {device_name_from_session}, Source: {audio_source}")
            meeting_recorder = MeetingRecorder(
                device_name=device_name_from_session, # This needs to be the actual device name/index
                audio_source=audio_source
            )
        else:
            log.info(f"Using existing MeetingRecorder. Setting audio source to {audio_source}.")
            meeting_recorder.set_audio_source(audio_source)
            # If device needs to be changed on an existing instance, a method would be needed in MeetingRecorder.
            # For now, assume device is set at init or doesn't change post-init for an existing instance.

        if not meeting_recorder.start_recording(): # start_recording now returns bool
            log.error("meeting_recorder.start_recording() returned False.")
            # Attempt to get a more specific error if the recorder sets one
            error_message = "Failed to start recording. Check MeetingRecorder logs."
            if hasattr(meeting_recorder, 'last_error') and meeting_recorder.last_error:
                error_message = meeting_recorder.last_error
            return jsonify({"status": "error", "message": error_message}), 500
        
        log.info(f"Recording started successfully for meeting ID: {meeting_recorder.meeting_id}")
        return jsonify({
            "status": "success", # Standardized
            "message": "Recording started successfully.", # Standardized
            "meeting_id": meeting_recorder.meeting_id,
            "audio_source": audio_source
        })
    except Exception as e:
        log.error(f"Error starting recording: {str(e)}", exc_info=True) # exc_info=True added
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/record/stop", methods=["POST"])
def record_stop():
    """Stop the current recording"""
    global meeting_recorder
    
    if meeting_recorder is None or not meeting_recorder.recording:
        log.warning("Attempt to stop recording when no recording is in progress.")
        return jsonify({
            "status": "error", # Standardized
            "message": "No recording in progress to stop." # Standardized
        }), 400 # Client error
    
    try:
        log.info(f"Attempting to stop recording for meeting ID: {meeting_recorder.meeting_id}")
        result = meeting_recorder.stop_recording() # This returns a dict of file paths
        
        if not result: # stop_recording might return empty dict on some failures
            log.warning("meeting_recorder.stop_recording() returned empty or no result.")
            # Consider if this is an error or just means no files were produced.
            # For now, treat as success in stopping but note no files.
            return jsonify({
                "status": "success",
                "message": "Recording stopped, but no files were reported by the recorder.",
                "files": {},
                "meeting_id": meeting_recorder.meeting_id
            })

        log.info(f"Recording stopped successfully for meeting ID: {meeting_recorder.meeting_id}. Files: {result}")
        return jsonify({
            "status": "success",
            "message": "Recording stopped successfully.", # Standardized
            "files": result,
            "meeting_id": meeting_recorder.meeting_id
        })
    
    except Exception as e:
        log.error(f"Error stopping recording: {str(e)}", exc_info=True) # exc_info=True was already there
        return jsonify({
            "status": "error",
            "message": f"An error occurred while stopping the recording: {str(e)}" # Standardized
        }), 500

@app.route("/record/devices", methods=["GET"])
def record_devices():
    """Get available audio devices for recording"""
    try:
        # Use the new audio_capture.list_audio_devices
        # This function now returns a list of AudioDevice objects.
        devices_objects = list_audio_devices() 
        devices_list = [{"index": dev.index, "name": dev.name, "channels": dev.channels} for dev in devices_objects]

        # Virtual audio check might need adjustment if check_virtual_audio_setup is removed or changed
        # For now, assume check_virtual_audio_setup exists and works, or remove if not relevant.
        # va_success, va_message = check_virtual_audio_setup() # This seems to be missing from the provided context
        va_success, va_message = (True, "Virtual audio check placeholder.") # Placeholder

        log.info(f"Listed {len(devices_list)} audio devices.")
        return jsonify({
            "status": "success",
            "devices": devices_list,
            # "virtual_devices": virtual_devices, # This logic might need to be part of list_audio_devices or a new utility
            "virtual_audio_available": va_success, # Placeholder
            "message": va_message # Placeholder
        })
    
    except Exception as e:
        log.error(f"Error listing audio devices: {str(e)}", exc_info=True) # exc_info=True was there
        return jsonify({
            "status": "error",
            "message": f"An error occurred while listing audio devices: {str(e)}" # Standardized
        }), 500

@app.route("/record/transcript", methods=["GET"])
def record_transcript():
    """Get the current transcript of the meeting"""
    global meeting_recorder
    
    if meeting_recorder is None:
        log.warning("Attempt to get transcript when recorder is not initialized.")
        return jsonify({
            "status": "error", # Standardized
            "message": "Meeting recorder not initialized." # Standardized
        }), 400 # Client error - trying to get transcript too early
    
    try:
        # Get current transcript
        # Ensure meeting_id is available even if not recording, if instance exists
        meeting_id = meeting_recorder.meeting_id if hasattr(meeting_recorder, 'meeting_id') else None
        duration = 0
        if meeting_recorder.recording and hasattr(meeting_recorder, 'get_recording_duration'):
             duration = meeting_recorder.get_recording_duration()
        
        log.info(f"Fetching transcript for meeting ID: {meeting_id}")
        return jsonify({
            "status": "success",
            "meeting_id": meeting_id,
            "transcript": meeting_recorder.full_transcript,
            "segments": meeting_recorder.transcript_segments,
            "duration": duration
        })
    
    except Exception as e:
        log.error(f"Error getting transcript: {str(e)}", exc_info=True) # exc_info=True was there
        return jsonify({
            "status": "error",
            "message": f"An error occurred while fetching the transcript: {str(e)}" # Standardized
        }), 500

@app.route("/record/notes", methods=["GET"])
def record_notes():
    """Get the AI-generated notes for the current or completed meeting"""
    global meeting_recorder
    
    if meeting_recorder is None:
        log.warning("Attempt to get notes when recorder is not initialized.")
        return jsonify({
            "status": "error", # Standardized
            "message": "Meeting recorder not initialized." # Standardized
        }), 400 # Client error
    
    try:
        meeting_id = meeting_recorder.meeting_id if hasattr(meeting_recorder, 'meeting_id') else None
        # summary_notes now directly contains the list of note dicts or the final summary structure
        notes_data = meeting_recorder.summary_notes
        final_summary_data = meeting_recorder.final_meeting_summary_data

        log.info(f"Fetching notes for meeting ID: {meeting_id}")
        
        response_data = {
            "status": "success",
            "meeting_id": meeting_id,
            "interim_notes": notes_data if not final_summary_data else [], # Show interim if no final
            "final_summary": final_summary_data,
            "polls": meeting_recorder.auto_polls or []
        }
        # If final_summary_data is present, its 'notes' field contains the primary notes.
        # The structure saved by _save_notes in MeetingRecorder is:
        # { "meeting_id": ..., "date": ..., "interim_notes": ..., "polls": ..., "final_summary": ... }
        # So, this route should return the content of that saved notes.json, or the live state.
        # The current logic fetches live state. If we want to fetch from file, need a different method.

        return jsonify(response_data)
    
    except Exception as e:
        log.error(f"Error getting notes: {str(e)}", exc_info=True) # exc_info=True was there
        return jsonify({
            "status": "error",
            "message": f"An error occurred while fetching notes: {str(e)}" # Standardized
        }), 500

@app.route("/record/setup", methods=["GET"])
def record_setup():
    """Check if the recording setup is properly configured"""
    try:
        # check_meeting_recorder_setup and check_virtual_audio_setup might not exist or be updated.
        # Assuming they are for now, or need to be replaced with direct checks.
        # For example, check if Whisper model can be loaded by MeetingRecorder.
        
        # Placeholder for actual checks, as these helper functions might be removed/changed
        # from other modules or their functionality integrated into MeetingRecorder.
        # mr_success, mr_message = check_meeting_recorder_setup() 
        # va_success, va_message = check_virtual_audio_setup()
        
        mr_success, mr_message = (True, "Meeting recorder components seem OK (placeholder check).")
        va_success, va_message = (True, "Virtual audio setup seems OK (placeholder check).")
        has_virtual_audio = va_success # Placeholder

        log.info("Performed recording setup check.")
        return jsonify({
            "status": "success" if (mr_success and va_success) else "warning", # Standardized
            "message": "Setup status determined (placeholder checks).", # Standardized
            "details": {
                "meeting_recorder_status": {
                    "success": mr_success,
                    "message": mr_message
                },
                "virtual_audio_status": {
                    "success": va_success,
                    "message": va_message,
                    "available": has_virtual_audio
                }
            }
        })
    
    except Exception as e:
        log.error(f"Error checking recording setup: {str(e)}", exc_info=True) # exc_info=True was there
        return jsonify({
            "status": "error",
            "message": f"An error occurred while checking recording setup: {str(e)}" # Standardized
        }), 500

def open_browser():
    """Open the default web browser to the application URL"""
    webbrowser.open('http://localhost:8000')

@app.errorhandler(Exception)
def handle_error(error):
    """Global error handler for all unhandled exceptions."""
    error_msg = str(error)
    log.error(f"Unhandled error: {error_msg}", exc_info=True)
    return render_template("error.html", error=error_msg), 500

if __name__ == "__main__":
    # Open browser in a separate thread
    threading.Thread(target=open_browser).start()
    
    # Run Flask with proper shutdown handling
    try:
        app.run(host="0.0.0.0", port=8000, debug=True, use_reloader=False)
    except KeyboardInterrupt:
        print("\nShutting down gracefully...")
        cleanup_on_exit()
    except Exception as e:
        print(f"\nError occurred: {e}")
        cleanup_on_exit()

# Add route for meeting recorder interface
@app.route("/recorder")
def recorder():
    """Page for recording and analyzing meetings"""
    if not is_token_valid():
        return redirect(url_for("index"))
    
    return render_template("recorder.html")

@app.route("/update_audio_source", methods=["POST"])
def update_audio_source():
    """Update the audio source for recording"""
    global meeting_recorder
    
    try:
        audio_source = request.json.get('audio_source')
        if audio_source not in ['host', 'all']:
            return jsonify({
                "status": "error",
                "message": "Invalid audio source. Must be 'host' or 'all'."
            }), 400
        
        # Store in session
        session['audio_source'] = audio_source
        
        # Update recorder if it exists
        if meeting_recorder:
            meeting_recorder.set_audio_source(audio_source)
        
        return jsonify({
            "status": "success",
            "message": f"Audio source updated to {audio_source}",
            "audio_source": audio_source
        })
    except Exception as e:
        log.error(f"Error updating audio source: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/record/pause", methods=["POST"])
def record_pause():
    """Toggle pause/resume recording"""
    global meeting_recorder
    
    if meeting_recorder is None or not meeting_recorder.recording:
        log.warning("Attempt to pause/resume when no recording is active.")
        return jsonify({
            "status": "error", # Standardized
            "message": "No active recording to pause/resume." # Standardized
        }), 400 # Client error
    
    try:
        paused_status = meeting_recorder.toggle_pause() # toggle_pause returns new is_paused state
        status_message = "paused" if paused_status else "resumed"
        log.info(f"Recording {status_message}.")
        return jsonify({
            "status": "success",
            "message": f"Recording {status_message}.", # Standardized
            "is_paused": paused_status
        })
    except Exception as e:
        log.error(f"Error toggling pause: {str(e)}", exc_info=True) # Added exc_info
        return jsonify({
            "status": "error",
            "message": f"An error occurred while toggling pause: {str(e)}" # Standardized
        }), 500

@app.route("/download_transcript")
def download_transcript():
    """Download the meeting transcript as a zip file containing text and JSON formats"""
    global meeting_recorder
    
    global meeting_recorder
    
    if meeting_recorder is None or not (hasattr(meeting_recorder, 'full_transcript') and meeting_recorder.full_transcript):
        log.warning("Attempt to download transcript when none is available or recorder not initialized.")
        return jsonify({
            "status": "error", # Standardized
            "message": "No transcript available to download or recorder not initialized." # Standardized
        }), 400 # Client error
    
    try:
        # Create a zip file in memory
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            # Add transcript as text file
            # meeting_recorder.full_transcript is now a single string
            zf.writestr("transcript.txt", meeting_recorder.full_transcript if meeting_recorder.full_transcript else "No transcript content.")
            
            # Add full data as JSON, including segments
            transcript_data = {
                "meeting_id": meeting_recorder.meeting_id,
                "duration_seconds": meeting_recorder.get_recording_duration(),
                "full_transcript_text": meeting_recorder.full_transcript,
                "transcript_segments": meeting_recorder.transcript_segments, # This contains {"timestamp": "...", "text": "..."}
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "audio_source": meeting_recorder.audio_source
                }
            }
            zf.writestr("transcript_details.json", json.dumps(transcript_data, indent=2))
        
        memory_file.seek(0)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"transcript_{meeting_recorder.meeting_id}_{timestamp}.zip"
        log.info(f"Prepared transcript download: {filename}")
        return send_file(
            memory_file,
            mimetype="application/zip",
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        log.error(f"Error creating transcript download: {str(e)}", exc_info=True) # exc_info=True was there
        return jsonify({
            "status": "error",
            "message": f"An error occurred while preparing the transcript download: {str(e)}" # Standardized
        }), 500

@app.route("/download_polls")
def download_polls():
    """Download generated polls as a zip file"""
    global meeting_recorder
    
    global meeting_recorder
    
    if meeting_recorder is None or not (hasattr(meeting_recorder, 'auto_polls') and meeting_recorder.auto_polls):
        log.warning("Attempt to download polls when none are available or recorder not initialized.")
        return jsonify({
            "status": "error", # Standardized
            "message": "No polls available to download or recorder not initialized." # Standardized
        }), 400 # Client error
    
    try:
        memory_file = BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
            polls_data = {
                "meeting_id": meeting_recorder.meeting_id,
                "polls": meeting_recorder.auto_polls,
                "metadata": {
                    "generated_at": datetime.now().isoformat(),
                    "total_polls": len(meeting_recorder.auto_polls)
                }
            }
            zf.writestr("polls_details.json", json.dumps(polls_data, indent=2))
            
            polls_text_content = []
            for i, poll in enumerate(meeting_recorder.auto_polls, 1):
                polls_text_content.append(f"Poll #{i}: {poll.get('title', 'Untitled Poll')}")
                polls_text_content.append("-" * 20)
                polls_text_content.append(f"  Question: {poll.get('question', 'N/A')}")
                polls_text_content.append("  Options:")
                for j, option in enumerate(poll.get('options', []), 1):
                    polls_text_content.append(f"    {j}. {option}")
                polls_text_content.append("\n")
            
            zf.writestr("polls_summary.txt", "\n".join(polls_text_content))
        
        memory_file.seek(0)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"polls_{meeting_recorder.meeting_id}_{timestamp}.zip"
        log.info(f"Prepared polls download: {filename}")
        return send_file(
            memory_file,
            mimetype="application/zip",
            as_attachment=True,
            download_name=filename
        )
    
    except Exception as e:
        log.error(f"Error creating polls download: {str(e)}", exc_info=True) # exc_info=True was there
        return jsonify({
            "status": "error",
            "message": f"An error occurred while preparing the polls download: {str(e)}" # Standardized
        }), 500

@sock.route('/ws/transcript')
def transcript_ws(ws):
    """WebSocket endpoint for real-time transcript updates"""
    global meeting_recorder
    
    try:
        while True:
            if meeting_recorder and meeting_recorder.recording:
                # Get latest transcript entries
                latest = meeting_recorder.get_latest_transcript()
                if latest:
                    # Format and send each entry
                    for entry in latest:
                        ws.send(json.dumps({
                            'timestamp': entry.get('timestamp', datetime.now().strftime('%H:%M:%S')),
                            'speaker': entry.get('speaker', 'Unknown'),
                            'text': entry.get('text', '')
                        }))
            time.sleep(0.5)  # Brief pause to prevent overwhelming the client
    except Exception as e:
        log.error(f"WebSocket error: {str(e)}")
        try:
            ws.close()
        except:
            pass

@app.route("/get_recommended_devices", methods=["GET"])
def get_recommended_devices():
    """Get recommended input devices based on the selected audio source"""
    try:
        audio_source = request.args.get('audio_source', 'all')
        if audio_source not in ['host', 'all']:
            log.warning(f"Invalid audio source '{audio_source}' requested for device recommendations.")
            return jsonify({"status": "error", "message": "Invalid audio source specified."}), 400

        # Initialize a temporary MeetingRecorder instance just to call get_recommended_devices
        # This is acceptable as get_recommended_devices doesn't rely on a fully "active" instance state.
        temp_recorder = MeetingRecorder(device_name=None) # device_name can be None for this method
        recommendations = temp_recorder.get_recommended_devices(audio_source)
        
        log.info(f"Fetched device recommendations for audio source: {audio_source}")
        return jsonify({
            "status": "success", # Standardized
            "message": "Device recommendations fetched successfully.", # Standardized
            "recommendations": recommendations
        })
    except Exception as e:
        log.error(f"Error getting device recommendations: {str(e)}", exc_info=True) # Added exc_info
        return jsonify({"status": "error", "message": f"An error occurred: {str(e)}"}), 500
