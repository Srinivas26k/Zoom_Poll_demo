# audio_capture.py
"""
Utility functions for listing and identifying audio devices.
This module relies on the `sounddevice` library.
"""

import sounddevice as sd
import logging
from typing import Optional, List, Dict, Union, Any # Union and Dict might be removed if get_device_by_name only returns AudioDevice
from rich.console import Console
from rich.logging import RichHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("audio_capture")
console = Console()

class AudioDevice:
    """Data class representing an audio device."""
    def __init__(self, index: int, name: str, channels: int):
        self.index = index
        self.name = name
        self.channels = channels
    
    def __str__(self) -> str:
        return f"Index: {self.index}, Name: {self.name} (Input Channels: {self.channels})"

def list_audio_devices() -> List[AudioDevice]:
    """
    List all available audio input devices.
    
    Returns:
        List[AudioDevice]: A list of available audio input devices.
    """
    try:
        devices = sd.query_devices()
        input_devices = []
        
        for i, dev_info in enumerate(devices):
            if dev_info['max_input_channels'] > 0:  # Only show input devices
                device = AudioDevice(
                    index=i,
                    name=str(dev_info['name']),
                    channels=int(dev_info['max_input_channels'])
                )
                input_devices.append(device)
                # logger.debug(f"Found input device: {device}") # Use debug for less verbose logging
        
        if not input_devices:
            logger.warning("No audio input devices found.")
        
        return input_devices
        
    except Exception as e:
        logger.error(f"Error listing audio devices: {str(e)}", exc_info=True)
        return []

def get_device_by_name(name_substring: str) -> Optional[AudioDevice]:
    """
    Find an audio input device by a substring of its name (case-insensitive).
    
    Args:
        name_substring (str): A substring of the desired device's name.
        
    Returns:
        Optional[AudioDevice]: The first matching AudioDevice, or None if not found.
    """
    if not name_substring:
        logger.warning("Cannot search for device with an empty name substring.")
        return None
        
    devices = list_audio_devices()
    for device in devices:
        if name_substring.lower() in device.name.lower():
            logger.info(f"Found device matching '{name_substring}': {device}")
            return device
    logger.warning(f"No device found matching substring: '{name_substring}'")
    return None

if __name__ == "__main__":
    console.print("[bold blue]Listing all available audio input devices:[/bold blue]")
    all_devices = list_audio_devices()
    if all_devices:
        for device in all_devices:
            console.print(f"  - {device}")
    else:
        console.print("[yellow]No audio input devices found.[/yellow]")

    console.print("\n[bold blue]Attempting to find a device by name substring (e.g., 'microphone', 'stereo mix', 'default'):[/bold blue]")
    # Example: Try to find a common microphone name part. User might need to change this.
    test_substrings = ["microphone", "default", "stereo mix", "line in", "webcam"] 
    found_specific_device = False
    for sub in test_substrings:
        console.print(f"Searching for device containing: '{sub}'")
        specific_device = get_device_by_name(sub)
        if specific_device:
            console.print(f"  [green]Found:[/green] {specific_device}")
            found_specific_device = True
            break # Stop after finding one for the example
    
    if not found_specific_device:
        console.print("[yellow]Could not find a device with common substrings. Your device names might be different.[/yellow]")