# app.py

from flask import Flask, redirect, url_for, session, request, render_template, flash, jsonify, send_file
import requests, base64, threading, os, time, webbrowser, secrets
from rich.console import Console
from run_loop import run_loop
import config
from audio_capture import list_audio_devices, AudioDevice
from virtual_audio import VirtualAudioRecorder, check_virtual_audio_setup
from meeting_recorder import MeetingRecorder, check_meeting_recorder_setup
from ai_notes import AINotesGenerator
import sys
from urllib.parse import urlencode, quote
from dotenv import load_dotenv
import logging
from rich.logging import RichHandler
from datetime import timedelta, datetime
import atexit
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
        error = "Missing CLIENT_ID or CLIENT_SECRET in .env file"
        console.log(f"[red]❌ {error}[/]")
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
            log.error(f"OAuth error: {error} - {error_description}")
            return render_template("error.html", error=f"OAuth error: {error_description}")
            
        if not code:
            log.error("No authorization code returned")
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
        log.info("Successfully obtained Zoom access token")
        return redirect(url_for("setup"))
        
    except requests.exceptions.RequestException as e:
        error_msg = f"Network error during token exchange: {str(e)}"
        log.error(error_msg)
        return render_template("error.html", error=error_msg)
    except Exception as e:
        error_msg = f"Unexpected error during token exchange: {str(e)}"
        log.error(error_msg, exc_info=True)
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
        segment_duration = request.form.get("segment_duration", "30")
        
        # Validate input
        if not device_name:
            flash("Please select an audio device", "error")
            return render_template("setup.html", devices=device_names)
            
        if not meeting_id:
            flash("Please enter a Zoom Meeting ID", "error")
            return render_template("setup.html", devices=device_names)
        
        # Set environment variables for the run_loop
        os.environ["MEETING_ID"] = meeting_id
        os.environ["ZOOM_TOKEN"] = session.get("access_token", "")
        os.environ["SEGMENT_DURATION"] = segment_duration
        
        console.log(f"[green]Set MEETING_ID={meeting_id}, SEGMENT_DURATION={segment_duration}[/]")
        
        device = get_device_by_name(device_name)
        if not device:
            # For testing, allow proceeding with any device name
            console.log(f"[yellow]Using '{device_name}' as device even though it wasn't found[/]")
            device = device_name
        
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
    """Cleanup function to run when the application is shutting down"""
    global automation_thread, meeting_recorder
    
    # Stop automation thread
    if automation_thread and automation_thread.is_alive():
        console.log("[yellow]Application shutting down, stopping automation thread...[/]")
        should_stop.set()
        try:
            automation_thread.join(timeout=1)
        except Exception:
            # Ignore exceptions during shutdown
            pass
    
    # Close meeting recorder
    if meeting_recorder is not None:
        console.log("[yellow]Cleaning up meeting recorder...[/]")
        try:
            meeting_recorder.close()
        except Exception as e:
            console.log(f"[yellow]Error closing meeting recorder: {str(e)}[/]")
    
    console.log("[green]Cleanup complete. Goodbye![/]")

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

@app.route("/started")
def started():
    if not is_token_valid():
        return redirect(url_for("index"))
    return render_template("started.html")

# New routes for meeting recording functionality
@app.route("/record/status", methods=["GET"])
def record_status():
    """Check the status of the meeting recorder"""
    global meeting_recorder
    
    if meeting_recorder is None:
        return jsonify({
            "status": "success",
            "active": False,
            "message": "Meeting recorder not initialized"
        })
    
    # Calculate duration
    duration_seconds = meeting_recorder.get_recording_duration() if hasattr(meeting_recorder, 'get_recording_duration') else 0
    hours, remainder = divmod(duration_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    formatted_duration = f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
    
    return jsonify({
        "status": "success",
        "active": meeting_recorder.recording,
        "meeting_id": meeting_recorder.meeting_id if meeting_recorder.recording else None,
        "transcript_length": len(meeting_recorder.full_transcript) if meeting_recorder.recording else 0,
        "duration_seconds": duration_seconds,        "duration_formatted": formatted_duration,
        "has_transcript": bool(meeting_recorder.full_transcript),
        "has_notes": bool(meeting_recorder.summary_notes)
    })

@app.route("/record/start", methods=["POST"])
def record_start():
    """Start recording with the selected audio source"""
    try:
        if meeting_recorder and meeting_recorder.is_recording:
            return jsonify({"error": "Recording already in progress"}), 400

        # Get audio source from session or default to 'all'
        audio_source = session.get('audio_source', 'all')
        
        # Initialize or update the recorder
        global meeting_recorder
        if not meeting_recorder:
            meeting_recorder = MeetingRecorder(
                device_name=session.get('device'),
                audio_source=audio_source
            )
        else:
            meeting_recorder.set_audio_source(audio_source)

        # Start recording
        meeting_recorder.start()
        
        return jsonify({
            "success": True,
            "message": "Recording started",
            "audio_source": audio_source
        })
    except Exception as e:
        log.error(f"Error starting recording: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/record/stop", methods=["POST"])
def record_stop():
    """Stop the current recording"""
    global meeting_recorder
    
    if meeting_recorder is None or not meeting_recorder.recording:
        return jsonify({
            "status": "error",
            "message": "No recording in progress"
        })
    
    try:
        # Stop recording
        result = meeting_recorder.stop_recording()
        
        return jsonify({
            "status": "success",
            "message": "Recording stopped successfully",
            "files": result,
            "meeting_id": meeting_recorder.meeting_id
        })
    
    except Exception as e:
        log.error(f"Error stopping recording: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Error: {str(e)}"
        }), 500

@app.route("/record/devices", methods=["GET"])
def record_devices():
    """Get available audio devices for recording"""
    try:
        # Initialize recorder temporarily to access devices
        recorder = VirtualAudioRecorder()
        devices = recorder.list_devices()
        virtual_devices = [dev for dev, is_virtual in zip(devices, recorder.is_device_virtual(devices)) if is_virtual]
        
        # Check for virtual audio setup
        va_success, va_message = check_virtual_audio_setup()
        
        return jsonify({
            "status": "success",
            "devices": devices,
            "virtual_devices": virtual_devices,
            "virtual_audio_available": va_success,
            "message": va_message
        })
    
    except Exception as e:
        log.error(f"Error listing audio devices: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Error: {str(e)}"
        }), 500

@app.route("/record/transcript", methods=["GET"])
def record_transcript():
    """Get the current transcript of the meeting"""
    global meeting_recorder
    
    if meeting_recorder is None:
        return jsonify({
            "status": "error",
            "message": "Meeting recorder not initialized"
        })
    
    try:
        # Get current transcript
        return jsonify({
            "status": "success",
            "meeting_id": meeting_recorder.meeting_id,
            "transcript": meeting_recorder.full_transcript,
            "segments": meeting_recorder.transcript_segments,
            "duration": meeting_recorder.get_recording_duration() if meeting_recorder.recording else 0
        })
    
    except Exception as e:
        log.error(f"Error getting transcript: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Error: {str(e)}"
        }), 500

@app.route("/record/notes", methods=["GET"])
def record_notes():
    """Get the AI-generated notes for the current or completed meeting"""
    global meeting_recorder
    
    if meeting_recorder is None:
        return jsonify({
            "status": "error",
            "message": "Meeting recorder not initialized"
        })
    
    try:
        # Get notes
        notes = meeting_recorder.summary_notes or {}
        
        # Enhanced response with formatted sections
        response = {
            "status": "success",
            "meeting_id": meeting_recorder.meeting_id,
            "notes": notes,
            "polls": meeting_recorder.auto_polls or []
        }
        
        # Only add these fields if they exist in the notes
        if notes:
            response.update({
                "summary": notes.get("summary", ""),
                "key_points": notes.get("key_points", []),
                "action_items": notes.get("action_items", []),
                "poll_suggestions": notes.get("poll_suggestions", [])
            })
        
        return jsonify(response)
    
    except Exception as e:
        log.error(f"Error getting notes: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Error: {str(e)}"
        }), 500

@app.route("/record/setup", methods=["GET"])
def record_setup():
    """Check if the recording setup is properly configured"""
    try:
        # Check recording setup components
        mr_success, mr_message = check_meeting_recorder_setup()
        va_success, va_message = check_virtual_audio_setup()
        
        # Get more details about system audio configuration
        has_virtual_audio = va_success
        
        return jsonify({
            "status": "success" if (mr_success and va_success) else "warning",
            "recording_setup": {
                "success": mr_success,
                "message": mr_message
            },
            "virtual_audio_setup": {
                "success": va_success,
                "message": va_message
            },
            "virtual_audio_available": has_virtual_audio,
            "message": "All systems ready." if (mr_success and va_success) else 
                      "Ready with limited functionality. " + 
                      ('' if va_success else "No virtual audio detected. ")
        })
    
    except Exception as e:
        log.error(f"Error checking recording setup: {str(e)}", exc_info=True)
        return jsonify({
            "status": "error",
            "message": f"Error: {str(e)}"
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
    """Update the audio source (host-only or all participants)"""
    try:
        audio_source = request.form.get('audio_source')
        if audio_source not in ['host', 'all']:
            return jsonify({"error": "Invalid audio source"}), 400

        # Update the audio source in the session
        session['audio_source'] = audio_source
        
        # Update the recording configuration
        if meeting_recorder:
            meeting_recorder.set_audio_source(audio_source)
            log.info(f"Audio source updated to: {audio_source}")
        
        return jsonify({
            "success": True,
            "message": f"Audio source updated to {audio_source}",
            "audio_source": audio_source
        })
    except Exception as e:
        log.error(f"Error updating audio source: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/record/pause", methods=["POST"])
def record_pause():
    """Pause or resume recording"""
    try:
        if not meeting_recorder:
            return jsonify({"error": "No active recording session"}), 400

        is_paused = meeting_recorder.toggle_pause()
        status = "paused" if is_paused else "resumed"
        
        return jsonify({
            "success": True,
            "message": f"Recording {status}",
            "is_paused": is_paused
        })
    except Exception as e:
        log.error(f"Error toggling recording pause: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/download_transcript")
def download_transcript():
    """Download the meeting transcript"""
    try:
        if not meeting_recorder:
            return jsonify({"error": "No transcript available"}), 404

        # Get the transcript data
        transcript_data = meeting_recorder.get_transcript()
        
        # Create a text file with the transcript
        output = BytesIO()
        with zipfile.ZipFile(output, 'w') as zipf:
            # Add transcript as text file
            transcript_text = ""
            for entry in transcript_data:
                timestamp = entry.get('timestamp', '')
                text = entry.get('text', '')
                speaker = entry.get('speaker', 'Unknown')
                transcript_text += f"[{timestamp}] {speaker}: {text}\n"
            
            zipf.writestr('transcript.txt', transcript_text)
            
            # Add transcript as JSON for programmatic use
            zipf.writestr('transcript.json', json.dumps(transcript_data, indent=2))
            
            # Add meeting metadata
            metadata = {
                "meeting_id": session.get('meeting_id'),
                "start_time": meeting_recorder.start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "audio_source": session.get('audio_source', 'all'),
                "device": session.get('device')
            }
            zipf.writestr('metadata.json', json.dumps(metadata, indent=2))

        output.seek(0)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"zoom_transcript_{timestamp}.zip"
        
        return send_file(
            output,
            mimetype='application/zip',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        log.error(f"Error downloading transcript: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route("/download_polls")
def download_polls():
    """Download the generated polls"""
    try:
        if not meeting_recorder:
            return jsonify({"error": "No polls available"}), 404

        # Get the generated polls
        polls_data = meeting_recorder.get_generated_polls()
        
        # Create a zip file with the polls
        output = BytesIO()
        with zipfile.ZipFile(output, 'w') as zipf:
            # Add polls as text file
            polls_text = ""
            for poll in polls_data:
                polls_text += f"Question: {poll['question']}\n"
                polls_text += f"Options: {', '.join(poll['options'])}\n"
                polls_text += f"Generated at: {poll['timestamp']}\n"
                polls_text += f"Context: {poll.get('context', '')}\n"
                polls_text += "-" * 50 + "\n"
            
            zipf.writestr('polls.txt', polls_text)
            
            # Add polls as JSON for programmatic use
            zipf.writestr('polls.json', json.dumps(polls_data, indent=2))
            
            # Add meeting metadata
            metadata = {
                "meeting_id": session.get('meeting_id'),
                "start_time": meeting_recorder.start_time.isoformat(),
                "end_time": datetime.now().isoformat(),
                "total_polls": len(polls_data)
            }
            zipf.writestr('metadata.json', json.dumps(metadata, indent=2))

        output.seek(0)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"zoom_polls_{timestamp}.zip"
        
        return send_file(
            output,
            mimetype='application/zip',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        log.error(f"Error downloading polls: {str(e)}")
        return jsonify({"error": str(e)}), 500

@sock.route('/ws/transcript')
def transcript_ws(ws):
    """WebSocket endpoint for real-time transcript updates"""
    try:
        while True:
            if not meeting_recorder or not meeting_recorder.is_recording:
                time.sleep(1)
                continue

            # Get the latest transcript entries
            transcript_data = meeting_recorder.get_latest_transcript()
            
            if transcript_data:
                # Send each new transcript entry
                for entry in transcript_data:
                    ws.send(json.dumps({
                        'timestamp': entry.get('timestamp', datetime.now().strftime('%H:%M:%S')),
                        'speaker': entry.get('speaker', 'Unknown'),
                        'text': entry.get('text', '')
                    }))
            
            # Sleep briefly to avoid overwhelming the client
            time.sleep(0.5)
            
    except Exception as e:
        log.error(f"WebSocket error: {str(e)}")
        ws.close()

@app.route("/get_recommended_devices", methods=["GET"])
def get_recommended_devices():
    """Get recommended input devices based on the selected audio source"""
    try:
        audio_source = request.args.get('audio_source', 'all')
        if audio_source not in ['host', 'all']:
            return jsonify({"error": "Invalid audio source"}), 400

        # Initialize recorder temporarily to get recommendations
        recorder = MeetingRecorder()
        recommendations = recorder.get_recommended_devices(audio_source)
        
        return jsonify({
            "success": True,
            "recommendations": recommendations
        })
    except Exception as e:
        log.error(f"Error getting device recommendations: {str(e)}")
        return jsonify({"error": str(e)}), 500
