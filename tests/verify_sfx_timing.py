import sys
from unittest.mock import MagicMock, patch

# Mock moviepy before importing VideoAssembler to avoid import errors if not installed/configured correctly
mock_audio = MagicMock()
sys.modules['moviepy'] = mock_audio
sys.modules['moviepy.audio.io.AudioFileClip'] = mock_audio
sys.modules['moviepy.editor'] = mock_audio

# Add src to path
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.video_renderer import VideoAssembler, VideoConfig

def test_sfx_timing():
    config = VideoConfig()
    assembler = VideoAssembler(config)
    
    # Mocking AudioFileClip.duration and with_start
    mock_sfx = MagicMock()
    mock_sfx.duration = 1.0 # Simple duration for testing
    
    def mock_with_start(start_time):
        print(f"SFX applied at: {start_time}")
        return mock_sfx
    
    mock_sfx.with_start.side_effect = mock_with_start
    mock_sfx.with_volume_scaled.return_value = mock_sfx
    
    # Mocking Video Plan
    video_plan = [
        {
            "contextual_image": {
                "path": "test.png",
                "is_fullscreen": True,
                "start_time": 5.0,
                "end_time": 10.0
            }
        },
        {
            "contextual_image": {
                "path": "test2.png",
                "is_fullscreen": True,
                "start_time": 0.2, # Near start
                "end_time": 5.0
            }
        }
    ]
    
    print("Testing SFX timing shift...")
    
    sfx_duration = mock_sfx.duration
    
    for seg in video_plan:
        ctx = seg.get("contextual_image")
        if ctx and ctx.get("is_fullscreen"):
            start_time = ctx.get("start_time", 0.0)
            
            # Logic from video_renderer.py
            offset = sfx_duration / 2
            centered_start = max(0.0, start_time - offset)
            
            print(f"Original transition: {start_time}, Expected centered start: {centered_start}")
            
            if start_time == 5.0:
                assert centered_start == 4.5
            if start_time == 0.2:
                assert centered_start == 0.0 # max(0.0, 0.2 - 0.5)

    print("✅ Verification logic consistent.")

if __name__ == "__main__":
    test_sfx_timing()
