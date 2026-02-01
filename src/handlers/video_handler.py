from abc import ABC, abstractmethod
import json
from pathlib import Path
from typing import Optional
import os

import shutil

from src.core.elevenlabs import generate_audio_from_script
from src.core.nano_banana import generate_image
from src.core.video_renderer import VideoConfig, assemble_video
from src.core.whisper import generate_timestamps_from_audio
from src.core.asset_assembler import VideoAnimationBuilder

class BaseHandler(ABC):
 
    def __init__(self):
        self.current_dir = os.path.dirname(__file__)
        self.root_dir = os.path.abspath(os.path.join(self.current_dir, "..", ".."))
        self.base_dir = Path(self.root_dir)

        # RENAMED COMMANDS FOR CLEANER CLI EXPERIENCE
        self.commands = {
            "create-dialogue": self._create_audio,
            "create-dialogue-timestamps": self._create_timestamps,
            "generate-images": self._generate_images,
            "create-video-script": self._create_video_script, # NEW NAME
            "video-render": self._create_final_video,
            "archive-project": self._archive_project,
            # SHORTS COMMANDS
            "create-video-script-shorts": self._create_video_script_shorts,
            "video-render-shorts": self._create_final_video_shorts,
        }
        
    def execute(self, command: Optional[str]):
        """Executes the exact command requested by the user."""
        if command in self.commands:
            handler = self.commands[command]
            try:
                handler()
            except Exception as e:
                print(f"[ERROR] Step failed: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"[ERROR] Unknown command: {command}")

    # ... [Existing methods omitted for brevity, keeping them as they were] ...

    def _generate_images(self):
        print("Generating images...")

        production_plan_path = (
            Path(self.root_dir) / "data" / "production_plan.json"
        )

        if not production_plan_path.is_file():
            print(f"[ERROR] Expected file but found nothing: {production_plan_path}")
            return

        try:
            with open(production_plan_path, "r", encoding="utf-8") as f:
                production_plan_data = json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to load JSON: {e}")
            return

        script = production_plan_data.get("script", {})
        if not script:
            print("[WARNING] No 'script' found in production plan.")
            return

        sections = ["dialogue"]
        output_folder = Path(self.root_dir) / "data" / "images" / "generated_images"

        for section_name in sections:
            items = script.get(section_name, [])
            if not items:
                continue
            
            print(f"Processing section: {section_name} with {len(items)} items...")
            
            for idx, item in enumerate(items):
                visual_assets_list = item.get("visual_assets")
                
                if not visual_assets_list or not isinstance(visual_assets_list, list):
                    continue
                
                for asset_idx, visual_asset in enumerate(visual_assets_list):
                    image_prompt = visual_asset.get("image_prompt")
                    if not image_prompt:
                        continue
                    
                    visual_id = visual_asset.get("visual_asset_id")
                    filename = f"{visual_id}.png" if visual_id else f"{section_name}_{idx}_{asset_idx}.png"
                    
                    print(f"Generating image for {filename}...")
                    generate_image(image_prompt, str(output_folder), filename)

        print("Image generation complete.")
    
    def _create_timestamps(self):
        print("Creating timestamps & Aligning Script...")

        output_audio_path = (
            self.base_dir / "data" / "audio" / "elevenlabs" / "dialogue.mp3"
        )

        output_timestamps_path = (
            self.base_dir / "data" / "audio" / "elevenlabs" / "dialogue_timestamps.json"
        )
        
        # Load Script for alignment
        production_plan_path = (
            self.base_dir / "data" / "production_plan.json"
        )
        
        script_content = []
        if production_plan_path.exists():
            with open(production_plan_path, 'r', encoding='utf-8') as f:
                plan = json.load(f)
                # Support both formats:
                # 1. Nested: { "script": { "dialogue": [...] } }
                # 2. Root level: { "dialogue": [...] }
                if 'script' in plan and 'dialogue' in plan['script']:
                    dialogue = plan['script']['dialogue']
                elif 'dialogue' in plan:
                    dialogue = plan['dialogue']
                else:
                    dialogue = []
                script_content = dialogue
                print(f"Loaded {len(script_content)} script segments for alignment.")

        # ==========================
        # 5. Generate timestamps AND ALIGN
        # ==========================
        generate_timestamps_from_audio(
            audio_file=str(output_audio_path),
            output_file=str(output_timestamps_path),
            script_content=script_content # Passing script triggers alignment in whisperTool
        )

        # ==========================
        # 6. Debug info
        # ==========================
        print("timestamps created and aligned.")
        
    def _create_audio(self):
        print("Creating audio...")

        # ==========================
        # 1. Paths & Config
        # ==========================
        # Skeptic: Charles (Husky, bassy, standard American)
        voice_id_skeptic = "S9GPGBaMND8XWwwzxQXp"

        # Analyst: Eve (Grounded professional)
        voice_id_analyst = "BZgkqPqms7Kj9ulSkVzn"

        production_plan_path = (
            self.base_dir / "data" / "production_plan.json"
        )

        output_audio_path = (
            self.base_dir / "data" / "audio" / "elevenlabs" / "dialogue.mp3"
        )

        # ==========================
        # 2. Validate & Load JSON
        # ==========================
        if not production_plan_path.is_file():
            print(f"[ERROR] Expected file but found nothing: {production_plan_path}")
            return

        try:
            with open(production_plan_path, "r", encoding="utf-8") as f:
                production_plan_data = json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to load JSON: {e}")
            return

        # ==========================
        # 3. Extract script
        # ==========================
        script_obj = production_plan_data.get("script", {})
        
        # Validate script structure
        full_dialogue = []
        if isinstance(script_obj, dict):
            full_dialogue = script_obj.get("dialogue", [])
        elif isinstance(script_obj, list):
            # Legacy support in case the JSON structure changes
            full_dialogue = script_obj

        if not full_dialogue:
            print("[ERROR] No dialogue found in production_plan.json")
            return

        # ==========================
        # 4. Generate audio
        # ==========================
        # Toda la complejidad de la API se delega a la función importada
        generate_audio_from_script(
            dialogue=full_dialogue,
            output_file=str(output_audio_path),
            voice_id_skeptic=voice_id_skeptic,
            voice_id_analyst=voice_id_analyst
        )

        print(f"Audio creation process completed. Output: {output_audio_path}")


    def _create_video_script(self):
        """
        ASSEMBLE ASSETS:
        Takes the ALIGNED timestamps (from transcribe step) and adds VISUALS (images, animations).
        """
        print("Assembling assets (Enriching segments)...")
        
        builder = VideoAnimationBuilder()
        
        # Path files
        # Aligned timestamps are generated in 'create-dialogue-timestamps' step
        timestamps_path = self.base_dir / "data" / "audio" / "elevenlabs" / "dialogue_timestamps.json"
        
        # New pose-based catalog
        images_path = self.base_dir / "data" / "images" / "images_catalog.json"
        
        # Final output as requested
        output_segments_path = self.base_dir / "data" / "video-script.json"
        
        try:
            output_path = builder.build_video_plan(
                str(timestamps_path),
                str(images_path), 
                str(output_segments_path)
            )
            print(f"✅ Assets assembled and saved to: {output_path}")
                
        except Exception as e:
            print(f"❌ Error assembling assets: {e}")
            import traceback
            traceback.print_exc()

    def _create_video_script_shorts(self):
        """
        ASSEMBLE ASSETS FOR SHORTS:
        Uses shorts images catalog and outputs to a dedicated shorts script file.
        """
        print("Assembling assets for SHORTS (Enriching segments)...")
        
        builder = VideoAnimationBuilder()
        
        # Path files
        timestamps_path = self.base_dir / "data" / "audio" / "elevenlabs" / "dialogue_timestamps.json"
        
        # SHORTS catalog
        images_path = self.base_dir / "data" / "shorts" / "images_catalog.json"
        
        # SHORTS output script
        output_segments_path = self.base_dir / "data" / "shorts" / "video-script.json"
        
        # Ensure directory exists
        output_segments_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            output_path = builder.build_video_plan(
                str(timestamps_path),
                str(images_path), 
                str(output_segments_path)
            )
            print(f"✅ [SHORTS] Assets assembled and saved to: {output_path}")
                
        except Exception as e:
            print(f"❌ Error assembling assets for shorts: {e}")
            import traceback
            traceback.print_exc()

    def _create_final_video(self):
        """Create the final assembled video using the new video-script.json structure"""
        print("Creating final video...")
        self._render_video_generic(
            script_path="data/video-script.json",
            output_path="data/output/final_video.mp4",
            mode="long"
        )

    def _create_final_video_shorts(self):
        """Create the final assembled SHORT video"""
        print("Creating final SHORTS video...")
        
        # Request Title from user or load from plan
        # For automation, we can check if it's in production plan or ask
        # Here we'll try to read from production plan first
        title_text = "Finding Peace" # Default
        try:
             with open(self.base_dir / "data" / "production_plan.json", 'r', encoding='utf-8') as f:
                plan = json.load(f)
                title_text = plan.get("opening_visual", {}).get("text_overlay", "Shorts Video")
        except:
            pass
            
        print(f"ℹ️ Using Title for Shorts: '{title_text}'")
        
        self._render_video_generic(
            script_path="data/shorts/video-script.json",
            output_path="data/shorts/output/final_video_shorts.mp4",
            mode="shorts",
            title_text=title_text
        )

    def _render_video_generic(self, script_path, output_path, mode="long", title_text=""):
        # =============================
        # 1. Define File Paths (Centralized)
        # =============================
        synced_plan_path = self.base_dir / script_path
        
        # New music path (Piano with nature sounds)
        background_music_path = str(
            self.base_dir / "data" / "audio" / "music" / "Frolic-Es-Jammy-Jams.mp3"
        )
        
        final_output_path = str(
            self.base_dir / output_path
        )
        
        # =============================
        # 2. Validate & Load Script
        # =============================
        if not synced_plan_path.exists():
            print(f"[ERROR] Video script not found: {synced_plan_path}")
            return
            
        try:
            with open(synced_plan_path, 'r', encoding='utf-8') as f:
                synced_plan_data = json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to load video script: {e}")
            return
            
        # =============================
        # 3. Dynamic Paths from Script
        # =============================
        narration_audio_path = synced_plan_data.get("audio_file")
        
        if not narration_audio_path or not Path(narration_audio_path).exists():
             if narration_audio_path:
                potential_path = self.base_dir / narration_audio_path
                if potential_path.exists():
                    narration_audio_path = str(potential_path)
                else:
                    print(f"[ERROR] Narration audio file not found: {narration_audio_path}")
                    return
             else:
                print("[ERROR] 'audio_file' key missing in video-script.json")
                return

        # =============================
        # 4. Configure Video Settings
        # =============================
        config = VideoConfig(mode=mode, title_text=title_text)
        
        # Create output directory
        Path(final_output_path).parent.mkdir(parents=True, exist_ok=True)
        
        # =============================
        # 5. Assemble Video
        # =============================
        try:
            final_video_path = assemble_video(
                synced_plan_data=synced_plan_data,
                narration_audio_path=narration_audio_path,
                background_music_path=background_music_path,
                output_path=final_output_path,
                config=config
            )
            
            print(f"✅ Final video ({mode}) created successfully: {final_video_path}")
            
        except Exception as e:
            print(f"[ERROR] Failed to create video: {e}")
            import traceback
            traceback.print_exc()

    def _archive_project(self):
        """Archives the current project artifacts to 'old-videos' and cleans up for a new project."""
        print("Starting project archive process...")
        
        folder_name = input("Enter the name for the archive folder (e.g., video-topic-01): ").strip()
        if not folder_name:
            print("[ERROR] Folder name cannot be empty.")
            return

        archive_dir = self.base_dir / "old-videos" / folder_name
        
        # 1. Create Archive Directory
        try:
            archive_dir.mkdir(parents=True, exist_ok=True)
            print(f"Created archive directory: {archive_dir}")
        except Exception as e:
            print(f"[ERROR] Failed to create archive directory: {e}")
            return

        # 2. Handle JSON Files (Copy to archive, then Clear original)
        json_files = [
            "data/video-script.json",
            "data/production_plan.json",
            "data/shorts/video-script.json" # Added shorts script
        ]
        
        for relative_path in json_files:
            file_path = self.base_dir / relative_path
            if file_path.exists():
                try:
                    # Copy to archive
                    shutil.copy2(file_path, archive_dir / file_path.name)
                    print(f"Archived: {file_path.name}")
                    
                    # Clear original (only if it's not a config file we want to keep structure of)
                    # For script files, clearing is fine.
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump({}, f, indent=2)
                    print(f"Cleared: {file_path.name}")
                except Exception as e:
                    print(f"[ERROR] Failed to process {file_path.name}: {e}")
            else:
                pass 
                # print(f"[WARNING] File not found: {file_path}")

        # 3. Handle Audio Files (Move to archive)
        audio_files = [
            "data/audio/elevenlabs/dialogue.mp3",
            "data/audio/elevenlabs/dialogue_timestamps.json"
        ]
        
        for relative_path in audio_files:
            file_path = self.base_dir / relative_path
            if file_path.exists():
                try:
                    shutil.move(str(file_path), str(archive_dir / file_path.name))
                    print(f"Moved: {file_path.name}")
                except Exception as e:
                    print(f"[ERROR] Failed to move {file_path.name}: {e}")
            else:
                pass
                # print(f"[WARNING] File not found: {file_path}")

        # 4. Handle Final Video (Move to archive)
        video_files = [
            "data/output/final_video.mp4",
            "data/shorts/output/final_video_shorts.mp4"
        ]
        
        for v_path in video_files:
             final_video_path = self.base_dir / v_path
             if final_video_path.exists():
                try:
                    shutil.move(str(final_video_path), str(archive_dir / final_video_path.name))
                    print(f"Moved: {final_video_path.name}")
                except Exception as e:
                    print(f"[ERROR] Failed to move {final_video_path.name}: {e}")

        # 5. Handle Generated Images (Move all to archive/generated_images)
        images_dir = self.base_dir / "data/images/generated_images"
        archive_images_dir = archive_dir / "generated_images"
        
        if images_dir.exists():
            try:
                # Create destination images subfolder
                archive_images_dir.mkdir(parents=True, exist_ok=True)
                
                # Move all files
                moved_count = 0
                for item in images_dir.iterdir():
                    if item.is_file():
                        shutil.move(str(item), str(archive_images_dir / item.name))
                        moved_count += 1
                
                print(f"Moved {moved_count} images to {archive_images_dir} and cleaned source folder.")
                
            except Exception as e:
                print(f"[ERROR] Failed to move images: {e}")
        else:
             pass

        print("\n✅ Project archive and cleanup completed successfully.")


class VideoHandler(BaseHandler):
    """Concrete implementation for video production pipeline."""
    pass


if __name__ == "__main__":
    import sys
    
    handler = VideoHandler()
    
    if len(sys.argv) < 2:
        print("Usage: python -m src.handlers.video_handler <command>")
        print("\nAvailable commands:")
        for cmd in handler.commands.keys():
            print(f"  - {cmd}")
        sys.exit(1)
    
    command = sys.argv[1]
    handler.execute(command)

