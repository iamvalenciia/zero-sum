
import sys
import os
import argparse
from pathlib import Path

# Add src to python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lds_mcp.tools.short_renderer import execute_render, validate_render_prerequisites

def main():
    parser = argparse.ArgumentParser(description="Render a script into a short video (9:16)")
    parser.add_argument("script_id", help="The ID of the script (filename without .json)")
    parser.add_argument("--hook", dest="hook_text", help="Hook text overlay", default="")
    parser.add_argument("--opening", dest="opening_image", help="Path to opening image", default="")
    parser.add_argument("--output", dest="output_filename", help="Output filename", default="")
    
    args = parser.parse_args()

    # Determine paths
    # Assuming standard structure: data/shorts/scripts/{script_id}.json
    base_dir = Path(__file__).parent
    
    print(f"Starting render for script: {args.script_id}")
    
    # Try to find the script to extract hook if not provided
    if not args.hook_text:
        script_path = base_dir / "data" / "shorts" / "scripts" / f"{args.script_id}.json"
        if script_path.exists():
            import json
            with open(script_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                script = data.get("script", data)
                args.hook_text = script.get("hook_text", "")
                print(f"Auto-detected hook text: {args.hook_text}")

    # Validate
    try:
        validate_render_prerequisites(args.script_id, base_dir=base_dir)
    except Exception as e:
        print(f"Validation failed: {e}")
        # Proceeding anyway usually fails, but execute_render might handle it.
        # But looking at the tool code, it raises ValueError.
        sys.exit(1)

    try:
        result = execute_render(
            script_id=args.script_id,
            hook_text=args.hook_text,
            opening_image=args.opening_image,
            output_filename=args.output_filename if args.output_filename else args.script_id,
            shorts_dir=base_dir / "data" / "shorts"
        )
        print(f"Render finished. Output: {result.get('output_path')}")
    except Exception as e:
        print(f"Render failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
