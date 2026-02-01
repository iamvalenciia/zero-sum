
import json
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.elevenlabs import generate_audio_from_script

def main():
    if len(sys.argv) < 2:
        print("Usage: python generate_audio.py <script_json_path>")
        sys.exit(1)

    script_path = Path(sys.argv[1])
    if not script_path.exists():
        print(f"Error: Script file not found at {script_path}")
        sys.exit(1)

    with open(script_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle different json structures (sometimes it's wrapped in 'script' key, sometimes not)
    script_content = data.get("script", data)
    
    script_id = script_content.get("id", script_path.stem)
    
    # Setup output paths
    base_dir = Path(__file__).parent / "data" / "shorts"
    audio_output = base_dir / "audio" / f"{script_id}.mp3"
    
    dialogue = script_content.get("dialogue", [])
    
    # You might need to adjust these voice IDs or load them from env/config
    # Using defaults or env vars if available, else placeholders
    # In the actual code these seem to be passed or hardcoded? 
    # Let's check how they are usually passed. 
    # For now I will use placeholders that the user must fill or env vars.
    voice_id_skeptic = os.getenv("VOICE_ID_SKEPTIC", "iP95p4xoSX5wMGTk13qQ") # Charles
    voice_id_analyst = os.getenv("VOICE_ID_ANALYST", "9BWtsMINqrJLrRacOk9x") # Aria/Eve equivalent
    
    print(f"Generating audio for script: {script_id}")
    try:
        generate_audio_from_script(
            dialogue=dialogue,
            output_file=str(audio_output),
            voice_id_skeptic=voice_id_skeptic,
            voice_id_analyst=voice_id_analyst
        )
        print(f"Done! Audio saved to {audio_output}")
    except Exception as e:
        print(f"Error generating audio: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
