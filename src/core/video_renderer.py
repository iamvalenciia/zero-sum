from __future__ import annotations
import av
import numpy as np
from PIL import Image, ImageEnhance, ImageDraw, ImageFilter, ImageOps
import os
from pathlib import Path
from typing import Dict, List, Optional
import math
import bisect
import traceback
from src.utils.captionGenerator import CaptionGenerator
from collections import OrderedDict

class LRUCache:
    def __init__(self, max_size=20):
        self.cache = OrderedDict()
        self.max_size = max_size
    
    def get(self, key):
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return None
    
    def set(self, key, value):
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)
    
    def __contains__(self, key):
        return key in self.cache
        
    def __getitem__(self, key):
        return self.get(key)
        
    def __setitem__(self, key, value):
        self.set(key, value)

try:
    # We still use MoviePy for convenient audio mixing
    from moviepy import AudioFileClip, CompositeAudioClip
    from moviepy.audio.fx import AudioLoop
except ImportError as e:
    print(f"Error importing moviepy: {e}")
    print("Install with: pip install moviepy>=2.0.0.dev2")



class VideoConfig:
    """Configuration class for video assembly parameters"""
    
    def __init__(self, mode: str = "long", title_text: str = ""):
        self.mode = mode # "long" or "shorts"
        
        # Video dimensions
        if self.mode == "shorts":
            self.video_width = 1080
            self.video_height = 1920
            self.ctx_img_size = 800 # Smaller for shorts
        else:
            self.video_width = 3840
            self.video_height = 2160
            self.ctx_img_size = 1000

        self.fps = 30
        
        # Background
        self.background_color = (0, 0, 0)

        # Image positioning
        self.image_width = self.video_width    # Full width
        
        # --- AUDIO CONFIGURATION ---
        self.narration_volume = 1    # Narration volume (0.0-2.0)
        self.music_volume = 0.3       # Soft piano background
        
        # Title Overlay (Shorts)
        self.title_text = title_text
        self.title_font_size = 80 if self.mode == "shorts" else 100
        self.title_color = (255, 255, 255, 255)
        self.title_y_pos = 150 # From top
        
        # Encoding settings
        self.video_codec = 'hevc_nvenc' # or 'h264_nvenc'
        self.audio_codec = 'aac'
        self.video_bitrate = 20000000 if self.mode == "long" else 12000000
        self.audio_bitrate = 192000

        # --- CONTEXTUAL IMAGE CONFIG ---
        # self.ctx_img_size is set above based on mode
        self.ctx_corner_radius = 30   # Radius for rounded corners
        self.ctx_border_width = 15     # Width of white border
        self.ctx_border_color = (255, 255, 255, 255)
        self.ctx_slide_duration = 0.8  # Seconds to slide in
        self.ctx_levitation_amp = 10.0 # Pixels (amplitude of sine wave)
        self.ctx_levitation_freq = 2.0 # Speed of bobbing
        self.ctx_shadow_offset = (15, 15)
        self.ctx_shadow_blur = 10
        self.ctx_shadow_color = (0, 0, 0, 150) # Semi-transparent black


class VideoAssembler:
    """Main class for assembling the final video using PyAV + Pillow + NumPy"""
    
    def __init__(self, config: Optional[VideoConfig] = None):
        self.config = config or VideoConfig()
        self.root_dir = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    
    def create_video(
        self,
        synced_plan_data: Dict,
        narration_audio_path: str,
        output_path: str,
        background_music_path: Optional[str] = None
    ) -> str:
        """Main function to create the video"""
        print("🎬 Starting video assembly (GPU Accelerated)...")
        
        # 1. Load Data & Prepare Audio
        video_plan = synced_plan_data.get("video_plan", [])
        
        if not Path(narration_audio_path).exists():
             raise FileNotFoundError(f"Audio file not found: {narration_audio_path}")

        # Prepare temporary mixed audio file
        temp_audio_path = str(Path(output_path).with_suffix('.temp_audio.m4a'))
        duration, narration_duration = self._prepare_audio(
            narration_audio_path, 
            background_music_path, 
            temp_audio_path,
            video_plan # Pass video plan for SFX
        )
        
        print(f"📊 Video duration: {duration:.2f} seconds (Narration: {narration_duration:.2f}s)")
        
        # 2. Prepare Timeline (Images)
        timeline = self._prepare_timeline(video_plan)
        
        # 3. Render Video
        try:
            # Initialize Caption Generator
            # Initialize Caption Generator
            caption_generator = CaptionGenerator(
                video_plan=video_plan,
                width=self.config.video_width,
                height=self.config.video_height
            )
            
            self._render_video(output_path, temp_audio_path, timeline, duration, video_plan, caption_generator, narration_limit=narration_duration)
            print("✅ Video assembly complete!")
        except Exception as e:
            print(f"Error during video rendering: {e}")
            traceback.print_exc()
            raise e
        finally:
            # Cleanup
            if os.path.exists(temp_audio_path):
                try:
                    os.remove(temp_audio_path)
                except Exception as e:
                    print(f"Warning: Could not remove temp audio file: {e}")
                
        return output_path


    def _prepare_audio(
        self, 
        narration_path: str, 
        music_path: Optional[str], 
        output_temp_path: str,
        video_plan: List[Dict] = None
    ) -> tuple[float, float]:
        """Mixes audio. Returns (total_duration, narration_duration)."""
        print("🔊 Processing audio...")
        
        # Initialize all audio clip variables for proper cleanup
        narration = None
        music = None
        long_music = None
        bg_part1 = None
        bg_part2 = None
        final_bg_music = None
        sfx_base = None
        sfx_clips = []
        final_audio = None
        
        try:
            # 1. NARATION
            narration = AudioFileClip(narration_path).with_volume_scaled(self.config.narration_volume)
            narration_duration = narration.duration
            print(f"Narration duration: {narration_duration}")
            
            final_audio_clips = [narration]
            total_video_duration = narration_duration 

            # 2. BACKGROUND MUSIC
            # Default path if not provided by handler
            target_music_path = music_path if music_path else str(self.root_dir / "data/audio/music/Frolic-Es-Jammy-Jams.mp3")
            
            # Check if file exists
            if Path(target_music_path).exists():
                print(f"🎵 Loading background music: {target_music_path}")
                try:
                    music = AudioFileClip(target_music_path)
                    
                    # Logic: Music loops naturally. Video length is narration + 19s (fixed tail).
                    # We want to loop the music enough times to cover narration + 19s.
                    # Then we will process it to double volume in the last 19s part.
                    
                    tail_duration = 0.0 if self.config.mode == "shorts" else 6.0
                    total_required_duration = narration_duration + tail_duration
                    
                    # Create a long enough music track by looping
                    # loops_needed = ceil(total_required / music_dur)
                    import math
                    loops_needed = math.ceil(total_required_duration / music.duration)
                    
                    # Concatenate manually to create the base chain or use composite
                    # For precise control, we can create list of clips
                    music_clips = [music] * loops_needed
                    from moviepy import concatenate_audioclips
                    long_music = concatenate_audioclips(music_clips)
                    
                    # Now we have a long music track. We need to process volume.
                    # Part 1: 0 to narration_duration (Normal Volume)
                    # Part 2: narration_duration to narration_duration + 19 (Double Volume)
                    
                    # Subclip exact ranges
                    bg_part1 = long_music.subclipped(0, narration_duration)
                    bg_part1 = bg_part1.with_volume_scaled(self.config.music_volume)
                    
                    bg_part2 = long_music.subclipped(narration_duration, total_required_duration)
                    # Double volume for the final part
                    bg_part2 = bg_part2.with_volume_scaled(self.config.music_volume * 2.0) 
                    
                    # Combine parts
                    final_bg_music = concatenate_audioclips([bg_part1, bg_part2])
                    
                    final_audio_clips.append(final_bg_music)
                    print(f"  + Added Scene Background Music (Part1 Vol: {self.config.music_volume}, Part2 Vol: {self.config.music_volume*2})")
                    
                    # Update total duration
                    total_video_duration = total_required_duration
                    
                except Exception as e:
                    print(f"  ❌ Failed to load Background Music: {e}")
            else:
                 print(f"  ⚠️ Background music file not found: {target_music_path}")


            # 3. SOUND EFFECTS (Transition SFX)
            # User Request: "poner el trnasition sound en todos los cambios no solo en coold_hook"
            # User Request: "make sure to lower volume by 10%" => 0.9
            
            sfx_path = self.root_dir / "data/audio/sound_effect/shutter-click.mp3"
            
            if sfx_path.exists() and video_plan:
                print("🎵 Applying shutter sound to FULLSCREEN images...")
                
                # Load sfx once
                sfx_base = AudioFileClip(str(sfx_path))
                # Reduce volume by 10% (0.9 factor) - keeping 0.7 as per existing code
                sfx_vol = 0.7 
                sfx_base = sfx_base.with_volume_scaled(sfx_vol)
                sfx_duration = sfx_base.duration
                
                for seg in video_plan:
                    # Get all contextual images (support both single object and list)
                    ctx_list = seg.get("contextual_images", [])
                    if not isinstance(ctx_list, list):
                        ctx_list = [ctx_list]
                    
                    # Also check legacy single object
                    legacy_ctx = seg.get("contextual_image")
                    if legacy_ctx and legacy_ctx not in ctx_list:
                        ctx_list.append(legacy_ctx)

                    for ctx in ctx_list:
                        if ctx and ctx.get("is_fullscreen"):
                            start_time = ctx.get("start_time", 0.0)
                            
                            # Calculate centered start time: subtract half duration from transition point
                            offset = sfx_duration / 2
                            centered_start = max(0.0, start_time - offset)
                            
                            # Add SFX at centered start time
                            clip = sfx_base.with_start(centered_start)
                            sfx_clips.append(clip)
                
                if sfx_clips:
                    final_audio_clips.extend(sfx_clips)
                    print(f"  + Added {len(sfx_clips)} transition SFX clips")
            else:
                 if not sfx_path.exists():
                     print(f"  ⚠️ SFX file not found: {sfx_path}")

            # Combine All
            final_audio = CompositeAudioClip(final_audio_clips)
                
            # Write temp audio file
            print(f"Writing audio to {output_temp_path}")
            # Ensure duration is set to match our total calculation
            final_audio.duration = total_video_duration
            # FIXED: Use logger='bar' instead of None to prevent blocking
            final_audio.write_audiofile(
                output_temp_path, 
                fps=44100, 
                codec='aac', 
                logger='bar'
            )
            
            return total_video_duration, narration_duration
        except Exception as e:
            print(f"Error in _prepare_audio: {e}")
            traceback.print_exc()
            raise e
        finally:
            # Cleanup - close ALL clips to prevent resource leaks and blocking
            # Use finally block to ensure cleanup happens even on error
            clips_to_close = [
                narration, music, long_music, bg_part1, bg_part2, 
                final_bg_music, sfx_base, final_audio
            ]
            for clip in clips_to_close:
                if clip is not None:
                    try:
                        clip.close()
                    except:
                        pass
            
            # Close SFX clips list
            for sfx in sfx_clips:
                if sfx is not None:
                    try:
                        sfx.close()
                    except:
                        pass

    def _prepare_timeline(self, video_plan: List[Dict]) -> List[Dict]:
        """Flattens the video plan into a sorted list of time-keyed image events."""
        events = []
        for segment in video_plan:
            for word in segment.get("words", []):
                # Check for animation frames first
                frames = word.get("animation_frames", [])
                if frames:
                    for frame in frames:
                        events.append({
                            "time": frame.get("time", 0),
                            "image": frame.get("image")
                        })
                # Fallback to static image
                elif word.get("image"):
                    img_path = word.get("image")
                    # Ensure path is string and exists
                    if img_path:
                        events.append({
                            "time": word.get("start", 0),
                            "image": img_path
                        })
        
        # Sort by time
        events.sort(key=lambda x: x["time"])
        return events

    def _get_image_for_time(self, time: float, timeline: List[Dict], current_idx: int) -> int:
        """Finds the index of the active image in the timeline for a given time."""
        # Optimization: Start searching from current_idx
        idx = current_idx
        
        # If we are before the current event (shouldn't happen in linear render), reset
        if idx < len(timeline) and time < timeline[idx]["time"]:
            idx = 0
            
        # Advance idx while the NEXT event is still in the past or present
        while idx + 1 < len(timeline) and timeline[idx + 1]["time"] <= time:
            idx += 1
            
        return idx

    # 4. HELPER PARA RESOLVER RUTAS (agregar como método de clase)
    def _resolve_path(self, path_str: str) -> Optional[Path]:
        """Resuelve rutas de manera consistente, manejando prefijos redundantes"""
        if not path_str:
            return None
            
        # Limpiar ruta de prefijos duplicados si el usuario pasó 'data/data/...'
        path_p = Path(path_str)
        
        candidates = [
            path_p,
            self.root_dir / path_p,
            # If path_str starts with 'data/', don't double it
            self.root_dir / path_str if not path_str.startswith('data') else self.root_dir / path_str.replace('data/', '', 1),
            self.root_dir / "data" / path_str,
        ]
        
        for candidate in candidates:
            if candidate.exists():
                return candidate.resolve()
        
        return None

    def _find_active_segment(self, time: float, video_plan: List[Dict], 
                         start_idx: int = 0) -> tuple[Optional[Dict], int]:
        """
        Finds the active segment for a given time.
        Uses binary search for cold starts, linear scan for sequential access.
        Returns: (segment, index) or (None, last_checked_index)
        """
        n = len(video_plan)
        if n == 0:
            return None, 0
        
        # If start_idx is valid and time is close, use linear scan (faster for sequential)
        if start_idx < n:
            seg = video_plan[start_idx]
            seg_start = seg.get("start", 0)
            seg_end = seg.get("end", 0)
            
            # Check current segment first
            if seg_start <= time <= seg_end:
                return seg, start_idx
            
            # Check next segment (common case in sequential rendering)
            if start_idx + 1 < n:
                next_seg = video_plan[start_idx + 1]
                if next_seg.get("start", 0) <= time <= next_seg.get("end", 0):
                    return next_seg, start_idx + 1
        
        # Binary search for segment containing time
        segment_starts = [s.get("start", 0) for s in video_plan]
        idx = bisect.bisect_right(segment_starts, time) - 1
        
        if idx < 0:
            return None, 0
        
        if idx < n:
            seg = video_plan[idx]
            if seg.get("start", 0) <= time <= seg.get("end", 0):
                return seg, idx
        
        return None, max(0, idx)

    def _render_video(self, output_path: str, audio_path: str, timeline: List[Dict], duration: float, video_plan: List[Dict], caption_generator: Optional[CaptionGenerator] = None, narration_limit: float = 0.0):
        """Renders the video frame by frame using PyAV and Pillow."""
        
        container = av.open(output_path, mode='w')
        input_audio = av.open(audio_path)

        # Cache para versiones blurred
        blurred_cache = {}  
        # Cache de PIL Images para evitar conversiones
        pil_image_cache = {}

        def get_pil_image(image_path: str, apply_blur: bool = False, force_cover: bool = False, copy: bool = True) -> Image.Image:
            """Get PIL image from cache or load from disk.
            
            Args:
                copy: If True, return a copy (safe for modification). If False, return cached version directly (faster, read-only).
            """
            cache_key = (image_path, apply_blur, force_cover)
            
            if cache_key in pil_image_cache:
                return pil_image_cache[cache_key].copy() if copy else pil_image_cache[cache_key]
            
            # Get numpy array
            arr = get_image_array(image_path, force_cover=force_cover)
            pil_img = Image.fromarray(arr)
            
            if apply_blur:
                pil_img = pil_img.filter(ImageFilter.GaussianBlur(15))
            
            # Cache con límite (ej: últimas 10 imágenes)
            if len(pil_image_cache) > 10:
                # Eliminar entrada más antigua (FIFO simple)
                pil_image_cache.pop(next(iter(pil_image_cache)))
            
            pil_image_cache[cache_key] = pil_img
            return pil_img.copy() if copy else pil_img
        
        try:
            # Setup Video Stream
            stream = container.add_stream(self.config.video_codec, rate=self.config.fps)
            stream.width = self.config.video_width
            stream.height = self.config.video_height
            stream.pix_fmt = 'yuv420p'
            stream.bit_rate = self.config.video_bitrate
            # NVENC specific options for quality/speed
            stream.options = {'preset': 'p4', 'tune': 'hq'} 
            
            # Setup Audio Stream (Copy from temp file)
            input_audio_stream = input_audio.streams.audio[0]
            # Manually add stream without template to avoid attribute errors
            output_audio_stream = container.add_stream('aac', rate=44100)
            
            # Pre-load images cache to avoid disk I/O lag
            image_cache = LRUCache(max_size=30)



            # --- PREPARE CONTEXTUAL IMAGES CACHE ---
            # We cache them to avoid reloading in loop
            # Key: (path_str, target_width_pixels)
            ctx_image_cache = {}

            def get_contextual_image(path_str: str, target_width_px: Optional[int] = None) -> Optional[Image.Image]:
                # Default to config size if not specified
                width_key = target_width_px if target_width_px else self.config.ctx_img_size
                cache_key = (path_str, width_key)
                
                if cache_key in ctx_image_cache:
                    return ctx_image_cache[cache_key]
                
                full_path = self._resolve_path(path_str)
                
                if full_path and full_path.exists():
                    try:
                        with Image.open(full_path) as img:
                            if img.mode != 'RGBA':
                                img = img.convert('RGBA')
                            
                            # START PROCESSING
                            # 1. Resize
                            # Determine dimensions
                            req_width = width_key
                            w_percent = (req_width / float(img.size[0]))
                            h_size = int((float(img.size[1]) * float(w_percent)))
                            
                            img = img.resize((req_width, h_size), Image.Resampling.BILINEAR)
                            
                            # 2. Create Rounded Mask for Image
                            mask = Image.new('L', (req_width, h_size), 0)
                            draw = ImageDraw.Draw(mask)
                            draw.rounded_rectangle(
                                [(0, 0), (req_width, h_size)], 
                                radius=self.config.ctx_corner_radius, 
                                fill=255
                            )
                            # Apply mask
                            img.putalpha(mask)

                            # 3. Create Border
                            bw = self.config.ctx_border_width
                            bordered_size = (req_width + 2*bw, h_size + 2*bw)
                            
                            # Border layer (White rounded rectangle)
                            # The border radius should be slightly larger to look concentric: radius + bw
                            outer_radius = self.config.ctx_corner_radius + bw
                            
                            bordered_img = Image.new('RGBA', bordered_size, (0,0,0,0))
                            draw_border = ImageDraw.Draw(bordered_img)
                            draw_border.rounded_rectangle(
                                [(0,0), bordered_size],
                                radius=outer_radius,
                                fill=self.config.ctx_border_color
                            )
                            
                            # Paste image onto border
                            bordered_img.paste(img, (bw, bw), img)
                            
                            # 4. Add Drop Shadow
                            # Create canvas for shadow + image
                            shadow_off = self.config.ctx_shadow_offset
                            blur = self.config.ctx_shadow_blur
                            # Total size needs to fit shadow
                            total_w = bordered_size[0] + abs(shadow_off[0]) + 2*blur
                            total_h = bordered_size[1] + abs(shadow_off[1]) + 2*blur
                            
                            final_comp = Image.new('RGBA', (total_w, total_h), (0,0,0,0))
                            
                            # Draw shadow (black rounded rect)
                            shadow_layer = Image.new('RGBA', bordered_size, self.config.ctx_shadow_color)
                            
                            shadow_shape = Image.new('RGBA', bordered_size, (0,0,0,0))
                            draw_shadow = ImageDraw.Draw(shadow_shape)
                            draw_shadow.rounded_rectangle(
                                [(0,0), bordered_size],
                                radius=outer_radius,
                                fill=self.config.ctx_shadow_color
                            )
                            
                            # Paste shadow shape onto a larger canvas to handle blur expansion
                            shadow_canvas = Image.new('RGBA', (total_w, total_h), (0,0,0,0))
                            
                            # Position: slightly offset
                            sh_x = blur + max(0, shadow_off[0])
                            sh_y = blur + max(0, shadow_off[1])
                            
                            shadow_canvas.paste(shadow_shape, (sh_x, sh_y), shadow_shape)
                            shadow_blurred = shadow_canvas.filter(ImageFilter.GaussianBlur(blur))
                            
                            # Paste shadow onto final comp
                            final_comp.paste(shadow_blurred, (0,0), shadow_blurred)
                            
                            # Paste image (bordered)
                            img_x = blur + max(0, -shadow_off[0])
                            img_y = blur + max(0, -shadow_off[1])
                            final_comp.paste(bordered_img, (img_x, img_y), bordered_img)
                            
                            ctx_image_cache[cache_key] = final_comp
                            return final_comp
                    except Exception as e:
                        print(f"Error loading ctx image {full_path}: {e}")
                else:
                    # print(f"Warning: Contextual image not found at {full_path}")
                    pass
                
                return None
            
            def get_image_array(path_str: str, force_cover: bool = False) -> np.ndarray:
                cache_key = path_str if not force_cover else f"{path_str}_COVER"
                if cache_key in image_cache:
                    return image_cache[cache_key]
                
                full_path = self._resolve_path(path_str)
                
                if not full_path or not full_path.exists():
                     # Return blank or placeholder if not found
                     return np.zeros((self.config.video_height, self.config.video_width, 3), dtype=np.uint8)

                try:
                    with Image.open(full_path) as img:
                        if img.mode != 'RGBA':
                            img = img.convert('RGBA')
                        
                        if force_cover:
                            # Cover logic (Full Screen)
                            img_resized = ImageOps.fit(
                                img, 
                                (self.config.video_width, self.config.video_height), 
                                method=Image.Resampling.BILINEAR
                            )
                        else:
                            # Resize logic (Fit Width)
                            target_width = self.config.video_width
                            w_percent = (target_width / float(img.size[0]))
                            h_size = int((float(img.size[1]) * float(w_percent)))
                            img_resized = img.resize((target_width, h_size), Image.Resampling.BILINEAR)
                        

                        
                        # Create background
                        bg = Image.new('RGB', (self.config.video_width, self.config.video_height), self.config.background_color)
                        
                        if force_cover:
                            bg.paste(img_resized, (0, 0), img_resized)
                        else:
                            # Center vertically
                            y_pos = (self.config.video_height - h_size) // 2
                            bg.paste(img_resized, (0, y_pos), img_resized)
                        
                        arr = np.array(bg)
                        image_cache[cache_key] = arr
                        return arr
                except Exception as e:
                    print(f"Error loading image {full_path}: {e}")
                    return np.zeros((self.config.video_height, self.config.video_width, 3), dtype=np.uint8)

            # --- VIDEO RENDERING LOOP ---
            total_frames = int(duration * self.config.fps)
            print(f"🎞️ Rendering {total_frames} frames...")
            
            timeline_idx = 0
            current_image_path = None
            current_frame_arr = None
            
            # Create a blank black frame for start
            blank_frame = np.zeros((self.config.video_height, self.config.video_width, 3), dtype=np.uint8)
            current_frame_arr = blank_frame

            # Pre-allocate frame buffer to avoid per-frame memory allocation
            frame_buffer = np.zeros((self.config.video_height, self.config.video_width, 3), dtype=np.uint8)
            
            # Pre-load final screen image (used for last 40s)
            final_screen_path = "images/final_screen/final_screen_image.jpeg"
            final_screen_arr = get_image_array(final_screen_path, force_cover=True)
            
            # Index for optimized search
            current_seg_idx = 0

            for i in range(total_frames):
                t = i / self.config.fps
                
                is_final_screen = False
                if narration_limit > 0 and t > narration_limit:
                    is_final_screen = True
                
                # Update current image if needed
                if not is_final_screen and timeline:
                    # Check if we need to advance
                    # We want the event that is <= t and closest to t
                    new_idx = self._get_image_for_time(t, timeline, timeline_idx)
                    
                    if new_idx < len(timeline):
                        evt = timeline[new_idx]
                        if evt["time"] <= t:
                            path = evt["image"]
                            if path != current_image_path:
                                current_image_path = path
                                current_frame_arr = get_image_array(path)
                            timeline_idx = new_idx
                elif is_final_screen:
                     # FINAL SCREEN OVERRIDE - Use pre-loaded image
                     if current_image_path != final_screen_path:
                        current_image_path = final_screen_path
                        current_frame_arr = final_screen_arr

                            
                # --- CONTEXTUAL VISUALS OVERLAY ---
                active_ctx_images = [] # Now a list to support multiple overlays if needed
                is_fullscreen_active = False 

                if not is_final_screen:
                    target_seg, current_seg_idx = self._find_active_segment(
                        t, video_plan, current_seg_idx
                    )
                    
                    if target_seg:
                        # Get all contextual images (support both single object and list)
                        ctx_list = target_seg.get("contextual_images", [])
                        if not isinstance(ctx_list, list):
                            ctx_list = [ctx_list]
                        
                        # Also check legacy single object
                        legacy_ctx = target_seg.get("contextual_image")
                        if legacy_ctx and legacy_ctx not in ctx_list:
                            ctx_list.append(legacy_ctx)

                        for ctx_data in ctx_list:
                            ctx_start = ctx_data.get("start_time", 0.0)
                            ctx_end = ctx_data.get("end_time", 0.0)
                            
                            if ctx_start <= t <= ctx_end:
                                is_fullscreen = ctx_data.get("is_fullscreen", False)
                                
                                # Determine target size and load image
                                if is_fullscreen:
                                    # Conditional Sizing: 90% for Shorts, 40% for Long
                                    if self.config.mode == "shorts":
                                        target_w = int(self.config.video_width * 0.90)
                                    else:
                                        target_w = int(self.config.video_width * 0.40)

                                    c_img = get_contextual_image(ctx_data.get("path"), target_width_px=target_w)
                                    is_fullscreen_active = True
                                else:
                                    c_img = get_contextual_image(ctx_data.get("path")) # Default size
                                    
                                if c_img:
                                    mid_y = (self.config.video_height - c_img.height) // 2
                                    
                                    if is_fullscreen:
                                        # FULLSCREEN CENTERED
                                        target_x = (self.config.video_width - c_img.width) // 2
                                        current_x = target_x 
                                    else:
                                        # SIDE POSITIONING (Classic)
                                        char = target_seg.get("character", "").lower()
                                        is_analyst = "analyst" in char
                                        
                                        if is_analyst:
                                            # Analyst (Right) - Center of Right Side (75%)
                                            target_x = int(self.config.video_width * 0.75 - c_img.width/2)
                                            start_x_off = self.config.video_width 
                                        else:
                                            # Skeptic (Left) - Center of Left Side (25%)
                                            target_x = int(self.config.video_width * 0.25 - c_img.width/2)
                                            start_x_off = -c_img.width
                                        
                                        # Animation: Slide In (Only for non-fullscreen side images)
                                        dt = t - ctx_start
                                        slide_dur = self.config.ctx_slide_duration
                                        current_x = target_x
                                        
                                        if dt < slide_dur:
                                            progress = dt / slide_dur
                                            # Ease out cubic
                                            p = 1 - math.pow(1 - progress, 3)
                                            current_x = start_x_off + (target_x - start_x_off) * p
                                    
                                    # Animation: Floating / Levitation (Sine Wave)
                                    # "Floating smoothly"
                                    lev_offset = math.sin(t * self.config.ctx_levitation_freq) * self.config.ctx_levitation_amp
                                    
                                    active_ctx_images.append({
                                        "image": c_img,
                                        "x": int(current_x),
                                        "y": int(mid_y + lev_offset)
                                    })

                # Compose Frame
                try:
                    # Get base image (with or without blur) using cache
                    # If final screen, we might not want blur? Or treat as fullscreen?
                    # "it's just an image at the end... 40 seconds"
                    # It acts as the main background image. 
                    # If we use get_image_array logic, it places it on background.
                    base_img = get_pil_image(current_image_path, apply_blur=(is_fullscreen_active and not is_final_screen), force_cover=is_final_screen)
                    
                    # Overlay de imágenes contextuales
                    if active_ctx_images and not is_final_screen:
                        for ctx_item in active_ctx_images:
                            base_img.paste(ctx_item["image"], (ctx_item["x"], ctx_item["y"]), ctx_item["image"])
                    
                    # Captions
                    if caption_generator and not is_fullscreen_active and not is_final_screen:
                        cap_img = caption_generator.get_caption_image(t)
                        if cap_img:
                            base_img.paste(cap_img, (0, 0), cap_img)
                    
                    # --- TITLE OVERLAY (FOR SHORTS) ---
                    if self.config.title_text:
                        from PIL import ImageFont
                        draw = ImageDraw.Draw(base_img)
                        # Attempt to load a nice font, fallback to default
                        try:
                            # Try to find a system font or use a bundled one
                            font = ImageFont.truetype("arial.ttf", self.config.title_font_size)
                        except:
                            font = ImageFont.load_default()
                        
                        # Calculate text size for centering
                        # Pillow 10+ uses getbbox or textbbox, older uses textsize
                        try:
                             left, top, right, bottom = draw.textbbox((0, 0), self.config.title_text, font=font)
                             text_w = right - left
                             text_h = bottom - top
                        except:
                             # Legacy fallback
                             text_w, text_h = draw.textsize(self.config.title_text, font=font)
                        
                        text_x = (self.config.video_width - text_w) // 2
                        text_y = self.config.title_y_pos
                        
                        # Draw Text Shadow/Outline for readability
                        outline_color = (0, 0, 0, 255)
                        stroke_width = 3
                        draw.text((text_x, text_y), self.config.title_text, font=font, fill=self.config.title_color, 
                                  stroke_width=stroke_width, stroke_fill=outline_color)

                    
                    # Conversión final - reuse buffer when no modifications
                    np.copyto(frame_buffer, np.asarray(base_img))
                    final_frame_arr = frame_buffer
                    
                except Exception as e:
                    print(f"Error compositing frame at {t:.2f}s: {e}")
                    final_frame_arr = current_frame_arr

                # Create VideoFrame
                frame = av.VideoFrame.from_ndarray(final_frame_arr, format='rgb24')
                for packet in stream.encode(frame):
                    container.mux(packet)
                    
                if i % 100 == 0:
                    print(f"Progress: {i}/{total_frames} ({(i/total_frames)*100:.1f}%)", end='\r')

            # Flush video stream
            for packet in stream.encode():
                container.mux(packet)
                
            print("\n🎵 Muxing audio...")
            # --- AUDIO MUXING LOOP ---
            for packet in input_audio.demux(input_audio_stream):
                if packet.dts is None:
                    continue
                
                # We need to rescale timestamps to the output stream's time base
                # packet.rescale_to(input_audio_stream.time_base, output_audio_stream.time_base) -> Deprecated/Removed in av 16.0.1
                if packet.pts is not None:
                    packet.pts = int(round(packet.pts * input_audio_stream.time_base / output_audio_stream.time_base))
                if packet.dts is not None:
                    packet.dts = int(round(packet.dts * input_audio_stream.time_base / output_audio_stream.time_base))
                packet.stream = output_audio_stream
                container.mux(packet)
                
        finally:
            input_audio.close()
            container.close()
        
def assemble_video(
    synced_plan_data: Dict,
    narration_audio_path: str,
    output_path: str,
    background_music_path: Optional[str] = None,
    config: Optional[VideoConfig] = None
) -> str:
    assembler = VideoAssembler(config)
    return assembler.create_video(
        synced_plan_data=synced_plan_data,
        narration_audio_path=narration_audio_path,
        output_path=output_path,
        background_music_path=background_music_path
    )