#!/usr/bin/env python3
"""
Background render worker for MCP.

This script is launched as a separate process to render videos without
blocking the MCP server. It can continue running even if the MCP client
disconnects.

Usage:
    python render_worker.py <script_id> <hook_text> <opening_image> <output_filename>
"""
import sys
import asyncio
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from lds_mcp.tools.short_renderer import execute_render, update_render_status, log


def main():
    if len(sys.argv) < 5:
        print(f"Usage: {sys.argv[0]} <script_id> <hook_text> <opening_image> <output_filename>")
        print(f"Got: {sys.argv}")
        sys.exit(1)

    script_id = sys.argv[1]
    hook_text = sys.argv[2]
    opening_image = sys.argv[3] if sys.argv[3] else ""
    output_filename = sys.argv[4]

    # Determine shorts directory
    shorts_dir = Path(__file__).parent.parent.parent / "data" / "shorts"

    print(f"=" * 60)
    print(f"RENDER WORKER STARTED")
    print(f"Time: {datetime.now().isoformat()}")
    print(f"script_id: {script_id}")
    print(f"hook_text: {hook_text}")
    print(f"opening_image: {opening_image}")
    print(f"output_filename: {output_filename}")
    print(f"shorts_dir: {shorts_dir}")
    print(f"=" * 60)
    sys.stdout.flush()

    try:
        # Update status to indicate worker has started
        update_render_status("worker_started", "Render worker process started", 1, {
            "script_id": script_id,
            "worker_pid": str(os.getpid()) if 'os' in dir() else "unknown"
        })

        # Run the async render function
        result = asyncio.run(execute_render(
            script_id=script_id,
            hook_text=hook_text,
            opening_image=opening_image,
            output_filename=output_filename,
            shorts_dir=shorts_dir
        ))

        print(f"\n{'=' * 60}")
        print(f"RENDER WORKER COMPLETED")
        print(f"Status: {result.get('status')}")
        if result.get('status') == 'success':
            print(f"Output: {result.get('output_path')}")
            print(f"Duration: {result.get('duration', 0):.2f}s")
            print(f"Frames: {result.get('frames', 0)}")
        else:
            print(f"Error: {result.get('message')}")
        print(f"{'=' * 60}")
        sys.stdout.flush()

        # Write final result to a JSON file
        result_file = shorts_dir / "render_result.json"
        with open(result_file, "w", encoding="utf-8") as f:
            result["completed_at"] = datetime.now().isoformat()
            json.dump(result, f, indent=2)

    except Exception as e:
        import traceback
        error_msg = str(e)
        error_tb = traceback.format_exc()

        print(f"\n{'=' * 60}")
        print(f"RENDER WORKER FAILED")
        print(f"Error: {error_msg}")
        print(f"Traceback:\n{error_tb}")
        print(f"{'=' * 60}")
        sys.stdout.flush()

        # Update status with error
        update_render_status("error", f"Worker failed: {error_msg}", 0, {
            "error": error_msg,
            "traceback": error_tb
        })

        sys.exit(1)


if __name__ == "__main__":
    import os
    main()
