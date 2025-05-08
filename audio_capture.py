# audio_capture.py

import sounddevice as sd
import soundfile  as sf
import numpy     as np
import librosa
from rich.console import Console

console = Console()

def list_audio_devices():
    """List all available audio input devices"""
    devices = sd.query_devices()
    console.log("[blue]Available audio devices:[/]")
    for i, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:  # Only show input devices
            console.log(f"  {i}: {dev['name']}")
    return devices

def record_segment(duration: int,
                   samplerate: int = 44100,
                   channels:   int = 2,
                   output:     str = "segment.wav",
                   device:     str = None):
    """
    1) Record stereo @44.1 kHz from `device` (or default if device is None/empty)
    2) Mix to mono, resample to 16 kHz, normalize, save to `segment.wav`
    """
    # Device handling - find device by name if specified
    dev = None
    if device:
        try:
            devices = sd.query_devices()
            # Try to find by name (partial match)
            for i, d in enumerate(devices):
                if device.lower() in d['name'].lower() and d['max_input_channels'] > 0:
                    dev = i
                    console.log(f"[green]Found device {i}: {d['name']}[/]")
                    break
            
            if dev is None:
                console.log(f"[yellow]⚠️ Device '{device}' not found, using default[/]")
        except Exception as e:
            console.log(f"[yellow]⚠️ Error finding device: {e}[/]")
    
    tmp = "temp_stereo.wav"
    console.log(f"🔴 Recording {duration}s @44.1kHz, stereo → {tmp} (device: {dev})")
    try:
        # record int16 PCM
        audio = sd.rec(
            int(duration * samplerate),
            samplerate=samplerate,
            channels=channels,
            dtype="int16",
            device=dev
        )
        sd.wait()
        sf.write(tmp, audio, samplerate, subtype="PCM_16")
        console.log("✅ Stereo file saved")

        # load + mix + resample
        data, sr = sf.read(tmp, dtype="float32")
        mono     = data.mean(axis=1)
        mono16   = librosa.resample(mono, orig_sr=sr, target_sr=16000)
        # normalize RMS
        rms    = np.sqrt((mono16**2).mean())
        mono16 = mono16 * (0.1 / (rms + 1e-8))
        sf.write(output, mono16, 16000, subtype="PCM_16")
        console.log("✅ Final segment.wav @16kHz mono")
        return True
    except Exception as e:
        console.log(f"[red]❌ Recording error: {e}[/]")
        return False

if __name__ == "__main__":
    # For testing
    list_audio_devices()
    record_segment(5, device=None)  # 5 seconds with default device