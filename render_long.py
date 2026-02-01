
import sys
import os
import argparse
import json
from pathlib import Path

# Add src to python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.core.video_renderer import assemble_video, VideoConfig

def main():
    parser = argparse.ArgumentParser(description="Render a script into a long-form video")
    parser.add_argument("script_id", help="The ID of the script (or path to json)")
    parser.add_argument("--hook", dest="hook_text", help="Title/Hook text", default="")
    parser.add_argument("--output", dest="output_filename", help="Output filename", default="")
    
    args = parser.parse_args()

    base_dir = Path(__file__).parent
    
    # Resolve script path
    if args.script_id.endswith(".json"):
        script_path = Path(args.script_id)
        script_id = script_path.stem
    else:
        script_path = base_dir / "data" / "shorts" / "scripts" / f"{args.script_id}.json"
        script_id = args.script_id

    if not script_path.exists():
        print(f"Error: Script file not found: {script_path}")
        sys.exit(1)

    # Load script to find assets
    with open(script_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        script_data = data.get("script", data)

    # Paths
    audio_path = base_dir / "data" / "shorts" / "audio" / f"{script_id}.mp3"
    timestamps_path = base_dir / "data" / "shorts" / "audio" / f"{script_id}_timestamps.json"
    
    output_name = args.output_filename if args.output_filename else f"{script_id}_long.mp4"
    output_path = base_dir / "data" / "shorts" / "output" / output_name

    if not audio_path.exists():
        print(f"Error: Audio file not found: {audio_path}")
        sys.exit(1)
        
    if not timestamps_path.exists():
        print("Timestamps not found. Please run render_short first (it generates timestamps) or implement auto-gen here.")
        # In a real scenario we might want to call the whisper part here too.
        sys.exit(1)
        
    # Load timestamps
    with open(timestamps_path, 'r', encoding='utf-8') as f:
        timestamps_data = json.load(f)

    # Prepare synced plan (the renderer expects a specific format, we might need to adapt it)
    # The 'video_renderer.py' seems to expect 'synced_plan_data' which is usually the output of alignment.
    # If we have timestamps.json validation, we can use that.
    
    # NOTE: video_renderer.py's assemble_video takes 'synced_plan_data'. 
    # This usually looks like the aligned JSON.
    # For now, we will pass the timestamps_data as it's likely the aligned format.
    
    print(f"Starting long render for: {script_id}")
    
    config = VideoConfig(mode="long", title_text=args.hook_text)
    
    try:
        assemble_video(
            synced_plan_data=timestamps_data,
            narration_audio_path=str(audio_path),
            output_path=str(output_path),
            config=config
        )
        print(f"Long-form render finished. Output: {output_path}")
    except Exception as e:
        print(f"Render failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
