import paramiko
import os
import logging
import json
from pathlib import Path
from typing import Dict, Any, Optional
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RemoteModelProcessor:
    def __init__(self, hostname: str, username: str, password: Optional[str] = None, key_filename: Optional[str] = None):
        """Initialize remote model processor."""
        self.hostname = hostname
        self.username = username
        self.password = password
        self.key_filename = key_filename
        self.ssh = None
        self.sftp = None
        
    def connect(self) -> bool:
        """Establish SSH connection to the server."""
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            if self.key_filename:
                self.ssh.connect(
                    self.hostname,
                    username=self.username,
                    key_filename=self.key_filename
                )
            else:
                self.ssh.connect(
                    self.hostname,
                    username=self.username,
                    password=self.password
                )
            
            self.sftp = self.ssh.open_sftp()
            logger.info(f"Successfully connected to {self.hostname}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to server: {str(e)}")
            return False
    
    def disconnect(self) -> None:
        """Close SSH connection."""
        if self.sftp:
            self.sftp.close()
        if self.ssh:
            self.ssh.close()
        logger.info("Disconnected from server")
    
    def transcribe_with_whisper_large(self, audio_path: str) -> Dict[str, Any]:
        """Transcribe audio using Whisper Large model on the server."""
        if not self.ssh:
            raise ConnectionError("Not connected to server")
            
        try:
            # Create temporary file on server
            remote_temp_dir = "/tmp/zoom_transcription"
            self._execute_command(f"mkdir -p {remote_temp_dir}")
            
            # Upload audio file
            remote_audio_path = f"{remote_temp_dir}/audio_{os.path.basename(audio_path)}"
            self.sftp.put(audio_path, remote_audio_path)
            
            # Run Whisper Large transcription
            command = f"whisper {remote_audio_path} --model large --language en --output_dir {remote_temp_dir}"
            stdout, stderr = self._execute_command(command)
            
            # Get transcription results
            result_path = f"{remote_temp_dir}/{os.path.basename(audio_path)}.json"
            with self.sftp.open(result_path) as f:
                result = json.load(f)
            
            # Cleanup
            self._execute_command(f"rm -f {remote_audio_path} {result_path}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error during remote transcription: {str(e)}")
            raise
    
    def process_with_deepseek(self, text: str) -> Dict[str, Any]:
        """Process text using DeepSeek 32B model on the server."""
        if not self.ssh:
            raise ConnectionError("Not connected to server")
            
        try:
            # Create temporary file with input text
            with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                f.write(text)
                local_temp_path = f.name
            
            # Upload to server
            remote_temp_dir = "/tmp/zoom_deepseek"
            self._execute_command(f"mkdir -p {remote_temp_dir}")
            remote_input_path = f"{remote_temp_dir}/input.txt"
            self.sftp.put(local_temp_path, remote_input_path)
            
            # Run DeepSeek processing
            command = f"deepseek-32b process {remote_input_path} --output {remote_temp_dir}/output.json"
            stdout, stderr = self._execute_command(command)
            
            # Get results
            with self.sftp.open(f"{remote_temp_dir}/output.json") as f:
                result = json.load(f)
            
            # Cleanup
            os.unlink(local_temp_path)
            self._execute_command(f"rm -rf {remote_temp_dir}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error during DeepSeek processing: {str(e)}")
            raise
    
    def _execute_command(self, command: str) -> tuple:
        """Execute command on remote server."""
        stdin, stdout, stderr = self.ssh.exec_command(command)
        return stdout.read().decode(), stderr.read().decode()
