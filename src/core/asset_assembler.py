import json
import re
from pathlib import Path
from typing import Dict, List, Optional

# Mapping of legacy pose ID prefixes to standard ones
# Standard: skeptic_*, analyst_* (matches images_catalog.json)
POSE_ID_ALIASES = {
    "brother_marcus": "skeptic",
    "sister_faith": "analyst",
}

class VideoAnimationBuilder:
    def __init__(self):
        self.pose_registry = {}
        self.missing_log = set()

    def load_data(self, timestamps_path: str, images_path: str) -> tuple:
        with open(timestamps_path, 'r', encoding='utf-8') as f:
            timestamps_data = json.load(f)
        with open(images_path, 'r', encoding='utf-8') as f:
            images_data = json.load(f)
        return timestamps_data, images_data

    def _index_images(self, images_data: List[Dict]):
        """
        Indices poses from images_catalog.json.
        Structure: { "pose_id": {"open": path, "closed": path} }
        """
        self.pose_registry = {}
        for entry in images_data:
            pose_id = entry.get('id')
            if not pose_id:
                continue
            
            self.pose_registry[pose_id] = {
                "closed": entry.get('closed', {}).get('path'),
                "open": entry.get('open', {}).get('path')
            }

    def _normalize_pose_id(self, pose_id: str) -> str:
        """
        Normalize legacy pose IDs to standard catalog IDs.
        E.g., 'brother_marcus_side' -> 'skeptic_side'
        """
        if not pose_id:
            return pose_id
        for old_prefix, new_prefix in POSE_ID_ALIASES.items():
            if pose_id.startswith(old_prefix):
                return pose_id.replace(old_prefix, new_prefix, 1)
        return pose_id

    def _find_contextual_image_path(self, visual_id: str) -> str:
        """
        Find the actual path of a contextual image with any supported extension.
        Searches for .png, .jpeg, .jpg in generated_images folder.
        """
        base_path = Path("data/images/generated_images")
        extensions = [".png", ".jpeg", ".jpg", ".webp"]
        
        for ext in extensions:
            candidate = base_path / f"{visual_id}{ext}"
            if candidate.exists():
                return str(candidate).replace("\\", "/")
        
        # Fallback - return .png path even if not exists (will log error later)
        self.missing_log.add(f"MISSING_CONTEXTUAL_IMAGE: {visual_id}")
        return f"data/images/generated_images/{visual_id}.png"


    def _count_syllables(self, word: str) -> int:
        """
        Professional heuristic for syllable counting in English.
        """
        word = word.lower().strip()
        if not word:
            return 0
        if len(word) <= 3:
            return 1
        
        # Remove non-alphabetic chars
        word = re.sub(r'[^a-z]', '', word)
        
        # Simple vowel-group counting
        count = 0
        vowels = "aeiouy"
        if word[0] in vowels:
            count += 1
        for index in range(1, len(word)):
            if word[index] in vowels and word[index - 1] not in vowels:
                count += 1
        if word.endswith("e"):
            count -= 1
        if word.endswith("le") and len(word) > 2 and word[-3] not in vowels:
            count += 1
        if count == 0:
            count = 1
        return count

    def _create_animation_frames(self, word: str, start: float, end: float, pose_id: str) -> List[Dict]:
        """
        Creates frames alternating between open and closed mouth for each syllable.
        
        Uses intelligent speed control to prevent unnatural rapid mouth movements:
        - Minimum syllable duration threshold prevents "rapper" effect
        - Fast words get reduced effective syllable count for smoother animation
        """
        if not word:
            return []
        
        pose_data = self.pose_registry.get(pose_id)
        if not pose_data:
            self.missing_log.add(f"MISSING_POSE: {pose_id}")
            return []

        duration = end - start
        if duration <= 0:
            return []

        # === SPEED CONTROL LOGIC ===
        # Minimum time per syllable cycle to look natural (in seconds)
        # 100ms = 10 open/close cycles per second max
        MIN_SYLLABLE_DURATION = 0.10
        
        raw_syllables = self._count_syllables(word)
        
        # Calculate effective syllables based on word duration
        # If speaking too fast, reduce syllable count to prevent rapid animation
        max_syllables_for_duration = max(1, int(duration / MIN_SYLLABLE_DURATION))
        effective_syllables = min(raw_syllables, max_syllables_for_duration)
        
        # For very short words (< 80ms), just hold mouth open
        if duration < 0.08:
            effective_syllables = 1
        
        FPS = 30
        num_frames = max(1, int(duration * FPS))
        
        frames = []
        frames_per_syllable = num_frames / effective_syllables
        
        for i in range(num_frames):
            frame_time = start + (i / FPS)
            progress_in_syllable = (i % frames_per_syllable) / frames_per_syllable
            # Open mouth for first 50% of each syllable cycle
            is_open = progress_in_syllable < 0.5
            
            img_path = pose_data["open"] if is_open else pose_data["closed"]
            
            frames.append({
                "time": round(frame_time, 3),
                "image": img_path
            })
            
        return frames

    def _validate_segment_words(self, segment):
        """Validates that words are within the segment time range"""
        start_time = segment.get('start', 0)
        end_time = segment.get('end', 0)
        words = segment.get('words', [])
        
        filtered_words = []
        for word in words:
            word_start = word.get('start', 0)
            word_end = word.get('end', 0)
            
            if word_start >= start_time - 0.1 and word_end <= end_time + 0.1:
                filtered_words.append(word)
        
        return filtered_words

    def build_video_plan(self, timestamps_path: str, images_path: str, output_path: str):
        print("📂 Loading data files for enrichment...")
        timestamps_data, images_data = self.load_data(timestamps_path, images_path)
        
        self._index_images(images_data)
        
        if "segments" not in timestamps_data:
             raise ValueError("Input JSON does not contain 'segments'.")

        raw_segments = timestamps_data["segments"]
        final_segments = []
        
        print(f"\n🎬 Enriching {len(raw_segments)} segments with syllable-based animation...")
        
        previous_character = None
        
        # GLOBAL TRACKING: Find and track the opening visual asset ID BEFORE processing segments
        # This ensures we filter this image from ALL segments, not just the first one
        used_opening_id = None
        for seg in raw_segments:
            vas = seg.get('visual_assets', [])
            if vas and isinstance(vas, list) and vas:
                first_va = vas[0]
                if first_va.get('visual_asset_id'):
                    used_opening_id = first_va.get('visual_asset_id')
                    break
        
        for idx, segment in enumerate(raw_segments):
            text = segment.get('text', '')
            character = segment.get('character', 'Unknown')
            words = self._validate_segment_words(segment)
            
            char_poses = segment.get('character_poses', [])
            visual_assets = segment.get('visual_assets', [])
            
            contextual_images = []
            
            # OPENING VISUAL: For first segment, inject a pre-segment opening image
            # This makes each video start with an illustration instead of always the same character
            if idx == 0 and used_opening_id:
                opening_duration = 2.5  # Show opening image for 2.5 seconds
                contextual_images.append({
                    "id": f"opening_{used_opening_id}",
                    "path": self._find_contextual_image_path(used_opening_id),
                    "start_time": 0,
                    "end_time": opening_duration,
                    "is_fullscreen": True
                })
            
            if visual_assets and isinstance(visual_assets, list) and visual_assets:
                filtered_assets = [va for va in visual_assets if va.get('visual_asset_id') != used_opening_id]
                
                for va in filtered_assets:
                    visual_id = va.get('visual_asset_id')
                    if not visual_id:
                        continue
                    
                    # Use word indices for precise timing
                    start_idx = va.get('start_word_index')
                    end_idx = va.get('end_word_index')
                    
                    if start_idx is not None and words:
                        start_idx = max(0, min(start_idx, len(words) - 1))
                        end_idx = max(start_idx, min(end_idx or start_idx, len(words) - 1))
                        start_t = words[start_idx]['start']
                        end_t = words[end_idx]['end']
                    else:
                        seg_start = words[0]['start'] if words else segment.get('start', 0)
                        seg_end = words[-1]['end'] if words else segment.get('end', 0)
                        start_t, end_t = seg_start, seg_end
            
                    contextual_images.append({
                        "id": visual_id,
                        "path": self._find_contextual_image_path(visual_id),
                        "start_time": round(start_t, 3),
                        "end_time": round(end_t, 3),
                        "is_fullscreen": va.get('is_fullscreen', True)
                    })

            transition_sound = None
            if previous_character and character != previous_character:
                transition_sound = "data/audio/sound_effect/shutter-click.mp3"
            if idx == 0:
                 transition_sound = "data/audio/sound_effect/shutter-click.mp3"

            previous_character = character

            words_with_animation = []
            for w_idx, word_obj in enumerate(words):
                w_text = word_obj['word']
                w_start = word_obj['start']
                w_end = word_obj['end']
                
                current_pose_id = None
                for pose in char_poses:
                    if pose['start_word_index'] <= w_idx <= pose['end_word_index']:
                        current_pose_id = self._normalize_pose_id(pose['pose_id'])
                        break
                
                if not current_pose_id and char_poses:
                    current_pose_id = self._normalize_pose_id(char_poses[0]['pose_id'])
                
                animation_frames = self._create_animation_frames(w_text, w_start, w_end, current_pose_id)
                
                words_with_animation.append({
                    "character": character,
                    "text": w_text,
                    "start": w_start,
                    "end": w_end,
                    "animation_frames": animation_frames,
                    "pose_id": current_pose_id
                })
            
            final_segments.append({
                "character": character,
                "start": segment.get('start', 0),
                "end": segment.get('end', 0),
                "text": text,
                "words": words_with_animation,
                "contextual_images": contextual_images,
                "transition_sound": transition_sound
            })
            
        if self.missing_log:
            print("\n🛑 MISSING ASSETS DETECTED:", self.missing_log)

        output_data = {
            "audio_file": timestamps_data.get('audio_file'),
            "video_plan": final_segments
        }
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ Video plan created: {output_path}")
        return output_path

if __name__ == "__main__":
    pass