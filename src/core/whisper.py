"""
Improved Whisper transcription with better script alignment.
"""

import json
from pathlib import Path
import ctypes.util
import platform
import difflib
import re 
from typing import List, Dict, Optional

# Fix for Whisper on Windows
if platform.system() == "Windows":
    original_find_library = ctypes.util.find_library

    def find_library_patched(name):
        if name == "c":
            return "msvcrt"
        return original_find_library(name)

    ctypes.util.find_library = find_library_patched

import whisper
from num2words import num2words


def expand_number_to_words(text: str) -> List[str]:
    """
    Expands a string containing numbers/currency into a list of individual words.
    Examples:
        "$20,496" -> ["twenty", "thousand", "four", "hundred", "and", "ninety-six", "dollars"]
        "50%" -> ["fifty", "percent"]
        "100" -> ["one", "hundred"]
    """
    text = text.lower().strip()
    
    # Handle currency with magnitude first: $2 billion -> 2 billion dollars
    text = re.sub(
        r'\$([0-9\.\,]+)\s*(hundred|thousand|million|billion|trillion)',
        r'\1 \2 dollars',
        text,
        flags=re.IGNORECASE
    )
    
    # Handle generic currency: $200 -> 200 dollars
    text = re.sub(r'\$([0-9\.\,]+)', r'\1 dollars', text)
    
    # Handle percent
    if '%' in text:
        text = text.replace('%', ' percent')

    # Common replacements
    text = text.replace('&', ' and ')
    text = text.replace('+', ' plus ')
    
    words = []
    for part in text.split():
        # Clean punctuation from the part for number checking
        clean_part = ''.join(filter(lambda x: x.isalnum() or x == '.', part)).rstrip('.')
        
        # Check if it's a number
        if clean_part and clean_part.replace('.', '', 1).isdigit():
            try:
                val = float(clean_part) if '.' in clean_part else int(clean_part)
                # num2words gives "twenty thousand..."
                # We replace hyphens/commas with spaces to get individual words
                expanded = num2words(val).replace('-', ' ').replace(',', ' ')
                words.extend(expanded.split())
                
                # If there was a suffix (like 'dollars' attached or 'percent'), handle it? 
                # Actually, earlier replacements separate them. 
                # But if we had "$20k", clean_part might fail or we need more regex.
                # For now, rely on simple cases as requested.
            except:
                words.append(part)
        else:
            words.append(part)
            
    # Final cleanup of words (remove punctuation)
    clean_words = []
    for w in words:
        w_clean = re.sub(r'[^\w]', '', w)
        if w_clean:
            clean_words.append(w_clean)
            
    return clean_words


def normalize_text(text: str) -> str:
    """
    Standardize text for comparison between script and transcript.
    """
    text = text.lower().strip()
    
    # Handle currency with magnitude first: $2 billion -> two billion dollars
    text = re.sub(
        r'\$([0-9\.\,]+)\s*(hundred|thousand|million|billion|trillion)',
        r'\1 \2 dollars',
        text,
        flags=re.IGNORECASE
    )
    
    # Handle generic currency: $200 -> 200 dollars
    text = re.sub(r'\$([0-9\.\,]+[kKmMbBtT]?)', r'\1 dollars', text)
    
    # Handle suffixes: 200K -> 200 thousand
    text = re.sub(r'(\d+)[kK](?=\W|$)', r'\1 thousand', text)
    text = re.sub(r'(\d+)[mM](?=\W|$)', r'\1 million', text)
    text = re.sub(r'(\d+)[bB](?=\W|$)', r'\1 billion', text)
    text = re.sub(r'(\d+)[tT](?=\W|$)', r'\1 trillion', text)
    
    # Handle percent
    text = text.replace('%', ' percent')
    
    # Common symbols
    replacements = {
        '&': ' and ',
        '+': ' plus ',
        '=': ' equals ',
        '½': ' half ',
        '-': ' ',
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    
    # Convert numbers to words
    parts = text.split()
    processed_parts = []
    
    for part in parts:
        if any(char.isdigit() for char in part):
            try:
                clean_part = ''.join(
                    filter(lambda x: x.isalnum() or x == '.', part)
                ).rstrip('.')
                
                if clean_part and clean_part.replace('.', '', 1).isdigit():
                    val = float(clean_part) if '.' in clean_part else int(clean_part)
                    part = num2words(val).replace('-', ' ').replace(',', '')
            except:
                pass
        processed_parts.append(part)
    
    text = ' '.join(processed_parts)
    
    # Remove all punctuation
    text = re.sub(r'[^\w\s]', '', text)
    
    # Remove extra whitespace
    return ' '.join(text.split())


def clean_script_text(text: str) -> str:
    """
    Remove emotional tags [happy] and SSML breaks <break.../> from script text.
    """
    # Remove emotional/action tags like [happy], [scoffing], etc.
    text = re.sub(r'\[.*?\]', '', text)
    
    # Remove SSML tags like <break time="0.5s"/>
    text = re.sub(r'<[^>]+>', '', text)
    
    return text.strip()


def find_sequence_match(
    transcript_words: List[Dict],
    start_index: int,
    target_sequence: List[str],
    search_limit: int
) -> int:
    """
    Finds the starting index of a word sequence in the transcript.
    """
    if not target_sequence:
        return -1
        
    seq_len = len(target_sequence)
    # Optimization: pre-calculate normalized target for faster comparison
    # (Already passed in as normalized list)
    
    for i in range(start_index, search_limit):
        # Boundary check
        if i + seq_len > len(transcript_words):
            break
            
        # Check first word first for speed
        if normalize_text(transcript_words[i]['word']) == target_sequence[0]:
            # Check full sequence
            match = True
            for k in range(1, seq_len):
                if normalize_text(transcript_words[i + k]['word']) != target_sequence[k]:
                    match = False
                    break
            if match:
                return i
                
    return -1


def align_transcript_with_script(
    transcript_words: List[Dict],
    script_segments: List[Dict]
) -> List[Dict]:
    """
    Aligns word-level timestamps from Whisper with script segments using 
    a robust two-phase sequential strategy.

    Strategy:
    Phase 1: Calculate expected word counts per segment from script text.
    Phase 2: For each segment boundary, use dual-anchor fuzzy matching to find
             the best split point. A segment ends where the next one begins.
    
    Critical: The search cursor ALWAYS advances monotonically.
    """
    import difflib
    
    aligned_segments = []
    total_words = len(transcript_words)
    
    if not script_segments or total_words == 0:
        return []
    
    print(f"\n[ALIGNMENT] Robustly aligning {len(script_segments)} segments with {total_words} transcript words...")

    # --- Helper Functions ---
    def simple_normalize(text: str) -> str:
        """Basic normalization for comparing script and transcript text."""
        # Remove things in brackets []
        text = re.sub(r'\[.*?\]', '', text)
        # Remove xml tags <...>
        text = re.sub(r'<[^>]+>', '', text)
        # Replace dashes with spaces to match num2words expansion (twenty-one -> twenty one)
        text = text.replace('-', ' ')
        # Remove punctuation and lowercase
        text = re.sub(r'[^\w\s]', '', text).lower()
        return ' '.join(text.split())
    
    def get_normalized_words(text: str) -> List[str]:
        """Get list of normalized words from script text."""
        return simple_normalize(text).split()
    
    def fuzzy_match_score(text1: str, text2: str) -> float:
        """Calculate similarity score between two text strings."""
        if not text1 or not text2:
            return 0.0
        return difflib.SequenceMatcher(None, text1, text2).ratio()
    
    def find_sequence_start(
        start_idx: int,
        target_words: List[str],
        search_limit: int,
        min_match_len: int = 2
    ) -> int:
        """
        Find where a sequence of target words begins in the transcript.
        Returns the index or -1 if not found.
        Uses progressively shorter matches as fallback.
        """
        if not target_words:
            return start_idx
            
        # Try matching with progressively shorter sequences
        for match_len in range(min(5, len(target_words)), min_match_len - 1, -1):
            search_seq = target_words[:match_len]
            
            for k in range(start_idx, min(search_limit, total_words - match_len + 1)):
                match = True
                for j in range(match_len):
                    w_transcript = transcript_words[k + j]['word']
                    w_clean = re.sub(r'[^\w\s]', '', w_transcript).lower()
                    if w_clean != search_seq[j]:
                        match = False
                        break
                
                if match:
                    return k
        
        return -1

    # --- Phase 1: Calculate expected word counts ---
    segment_word_counts = []
    for segment in script_segments:
        words = get_normalized_words(segment.get('text', ''))
        # Estimate: script words roughly equal transcript words
        # Numbers expand (e.g., "$427" -> "four hundred twenty seven dollars")
        # so we give a 1.5x multiplier for segments with numbers
        has_numbers = bool(re.search(r'\d', segment.get('text', '')))
        multiplier = 1.5 if has_numbers else 1.0
        estimated_count = int(len(words) * multiplier)
        segment_word_counts.append(max(1, estimated_count))
    
    # Calculate proportional distribution of transcript words
    total_estimated = sum(segment_word_counts)
    proportional_counts = []
    for count in segment_word_counts:
        proportion = count / total_estimated if total_estimated > 0 else 1.0 / len(script_segments)
        proportional_counts.append(int(total_words * proportion))
    
    # Adjust to ensure we use all words
    diff = total_words - sum(proportional_counts)
    if diff != 0 and proportional_counts:
        proportional_counts[-1] += diff

    # --- Phase 2: Find optimal segment boundaries ---
    current_idx = 0
    
    for i, segment in enumerate(script_segments):
        raw_text = segment.get('text', '')
        target_words = get_normalized_words(raw_text)
        estimated_word_count = proportional_counts[i]
        
        # Calculate search boundaries
        search_start = current_idx
        
        # The expected end of this segment
        expected_end = min(current_idx + estimated_word_count, total_words)
        
        # Search window: allow some slack for misalignment
        search_window = max(20, estimated_word_count // 2)
        
        # Determine the segment start
        segment_start_idx = current_idx
        
        # Try to find the segment's start sequence if we're not at the beginning
        if i > 0 and target_words:
            found_start = find_sequence_start(
                current_idx,
                target_words,
                min(current_idx + search_window, total_words),
                min_match_len=2
            )
            
            if found_start != -1 and found_start >= current_idx:
                segment_start_idx = found_start
                print(f"   Seg {i}: Found start sequence at word index {found_start}")
            else:
                # Fallback: use the current index (strict sequential)
                segment_start_idx = current_idx
                if target_words:
                    print(f"   Seg {i}: Start sequence '{' '.join(target_words[:3])}...' not found, using index {current_idx}")
        
        # Determine the segment end
        segment_end_idx = expected_end
        
        # Strategy: Use BOTH end-of-current and start-of-next for best boundary detection
        current_end_candidate = -1
        next_start_candidate = -1
        
        # A. Try to find the END of current segment (last 2-3 words)
        if len(target_words) >= 2:
            end_words = target_words[-min(3, len(target_words)):]
            # Search in a window around expected end
            search_start_for_end = max(segment_start_idx + 1, expected_end - search_window)
            search_end_for_end = min(expected_end + search_window, total_words)
            
            for match_len in range(len(end_words), 0, -1):
                search_seq = end_words[-match_len:]
                for k in range(search_start_for_end, min(search_end_for_end, total_words - match_len + 1)):
                    match = True
                    for j in range(match_len):
                        w_transcript = transcript_words[k + j]['word']
                        w_clean = re.sub(r'[^\w\s]', '', w_transcript).lower()
                        if w_clean != search_seq[j]:
                            match = False
                            break
                    if match:
                        # Found the end sequence - the segment ends AFTER this match
                        current_end_candidate = k + match_len
                        break
                if current_end_candidate != -1:
                    break
        
        # B. Try to find the START of next segment
        if i + 1 < len(script_segments):
            next_segment = script_segments[i + 1]
            next_target_words = get_normalized_words(next_segment.get('text', ''))
            
            if next_target_words:
                # Search for next segment's start in a window around expected end
                search_start_for_next = max(segment_start_idx + 1, expected_end - search_window)
                search_end_for_next = min(expected_end + search_window, total_words)
                
                next_start_candidate = find_sequence_start(
                    search_start_for_next,
                    next_target_words,
                    search_end_for_next,
                    min_match_len=2
                )
        
        # C. Decide the best boundary - PRIORITY: next segment start
        # This ensures no words are orphaned between segments
        if next_start_candidate != -1 and next_start_candidate > segment_start_idx:
            # ALWAYS prefer next segment's start as the boundary
            segment_end_idx = next_start_candidate
            print(f"   Seg {i}: End found via next segment's start at index {segment_end_idx}")
        elif current_end_candidate != -1 and current_end_candidate > segment_start_idx:
            # Fallback: use end-of-current match
            segment_end_idx = current_end_candidate
            print(f"   Seg {i}: End found via current segment's last words at index {segment_end_idx}")
        else:
            # Use proportional estimate
            segment_end_idx = max(segment_start_idx + 1, expected_end)
            if i + 1 < len(script_segments):
                print(f"   Seg {i}: Using proportional estimate for end: {segment_end_idx}")
        
        # For last segment, ensure all remaining words are captured
        if i + 1 >= len(script_segments):
            segment_end_idx = total_words
        
        # Safety: Ensure we don't go backwards
        segment_end_idx = max(segment_start_idx, segment_end_idx)
        
        # Assign words to this segment
        assigned_words = transcript_words[segment_start_idx:segment_end_idx]
        
        # Build enriched segment
        enriched = segment.copy()
        enriched['words'] = assigned_words
        
        if assigned_words:
            enriched['start'] = assigned_words[0]['start']
            enriched['end'] = assigned_words[-1]['end']
        else:
            # Zero duration if no words (but this should be rare now)
            if aligned_segments:
                enriched['start'] = aligned_segments[-1]['end']
                enriched['end'] = enriched['start']
            else:
                enriched['start'] = 0.0
                enriched['end'] = 0.0
        
        word_preview = [w['word'] for w in assigned_words[:3]] if assigned_words else []
        print(f"   Seg {i} ({segment.get('character', 'Unknown')[:8]}): {len(assigned_words)} words | {enriched['start']:.2f}s - {enriched['end']:.2f}s | First: {word_preview}")
        
        aligned_segments.append(enriched)
        
        # CRITICAL: Always advance the cursor
        current_idx = segment_end_idx

    # Final validation
    empty_segments = sum(1 for s in aligned_segments if len(s.get('words', [])) == 0)
    if empty_segments > 0:
        print(f"   [WARNING] {empty_segments} segments have no words assigned")
    
    print(f"[ALIGNMENT] Complete. Processed {len(aligned_segments)} segments.")
    
    return aligned_segments


def generate_timestamps_from_audio(
    audio_file: str,
    output_file: str,
    script_content: Optional[List[Dict]] = None,
    language: str = "en",
    model_size: str = "base",
) -> str:
    """
    Generates word-level timestamps from audio using Whisper.
    If script_content is provided, aligns words to script segments.
    
    Args:
        audio_file: Path to audio file
        output_file: Path for JSON output
        script_content: List of script segments (cold_hook + dialogue combined)
        language: Language code
        model_size: Whisper model size
    """
    print(f"[WHISPER] Starting transcription")
    print(f"   Input: {audio_file}")
    print(f"   Output: {output_file}")
    print(f"   Model: {model_size}")
    
    audio_path = Path(audio_file)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_file}")
    
    try:
        # Load Whisper model
        print(f"\n[LOADING] Loading Whisper '{model_size}' model...")
        model = whisper.load_model(model_size)
        
        # Transcribe with word timestamps
        print("[TRANSCRIBE] Transcribing audio...")
        result = model.transcribe(
            str(audio_path),
            language=language,
            word_timestamps=True,
            verbose=False,
        )
        
        # Extract and process word-level timestamps
        flat_words = []
        
        for segment in result["segments"]:
            if "words" not in segment:
                continue
            
            words_list = segment["words"]
            i = 0
            
            while i < len(words_list):
                word_data = words_list[i]
                word_text = word_data["word"].strip()
                start_time = word_data["start"]
                end_time = word_data["end"]
                
                # --- MERGING LOGIC START ---
                # Check for split currency/numbers e.g. "$20," + "496" or "$2" + "million"
                # This ensures we expand "$20,496" as a single unit -> "twenty thousand ... dollars"
                if word_text.startswith('$') and (len(word_text) < 2 or word_text[-1] in ',.' or word_text[1].isdigit()):
                    next_idx = i + 1
                    while next_idx < len(words_list):
                        next_word = words_list[next_idx]["word"].strip()
                        
                        # Case 1: Number continuation (digits or punctuation + digits)
                        # e.g. "496", ",000"
                        if re.match(r'^[0-9,.]+$', next_word):
                            word_text += next_word
                            end_time = words_list[next_idx]["end"]
                            next_idx += 1
                        
                        # Case 2: Magnitude words
                        # e.g. "million", "billion"
                        elif next_word.lower() in ['hundred', 'thousand', 'million', 'billion', 'trillion']:
                            word_text += " " + next_word
                            end_time = words_list[next_idx]["end"]
                            next_idx += 1
                        
                        else:
                            break
                    
                    # Advance main loop index to skip merged words
                    # We negate 1 because the loop adds 1 at the end
                    i = next_idx - 1

                # --- MERGING LOGIC END ---

                # Expand the word (handle numbers, currency, etc.)
                expanded_words = expand_number_to_words(word_text)
                
                if not expanded_words:
                    # If empty after expansion/cleaning, skip
                    i += 1
                    continue
                    
                # Calculate duration per word
                original_duration = end_time - start_time
                if original_duration < 0: original_duration = 0
                
                num_new_words = len(expanded_words)
                duration_per_word = original_duration / num_new_words
                
                for idx, w in enumerate(expanded_words):
                    w_start = start_time + (idx * duration_per_word)
                    w_end = w_start + duration_per_word
                    
                    flat_words.append({
                        "word": w,
                        "start": round(w_start, 2),
                        "end": round(w_end, 2)
                    })
                
                i += 1
        
        # Build output data
        output_data = {
            "audio_file": audio_file,
            "language": result.get("language", language),
            "full_transcript": result["text"].strip(),
            "words": flat_words
        }
        
        # Align with script if provided
        if script_content:
            print("\n[ALIGN] Aligning with production script...")
            print(f"   Total script segments: {len(script_content)}")
            
            # Perform alignment
            aligned_segments = align_transcript_with_script(
                flat_words,
                script_content
            )
            
            output_data["segments"] = aligned_segments
        
        # Save output
        output_path = Path(output_file)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n[SUCCESS] Timestamps saved to {output_file}")
        return str(output_path)
        
    except Exception as e:
        error_msg = f"[ERROR] Whisper transcription failed: {str(e)}"
        print(f"\n{error_msg}")
        raise RuntimeError(error_msg)


# Usage example
if __name__ == "__main__":
    # Load your production plan and extract segments
    with open("production_plan.json", "r") as f:
        plan = json.load(f)
    
    # Only use dialogue
    script = plan.get("script", {})
    script_content = []
    script_content.extend(script.get("dialogue", []))
    
    # Generate timestamps with alignment
    generate_timestamps_from_audio(
        audio_file="narration.mp3",
        output_file="timestamps.json",
        script_content=script_content,  # Pass combined segments list
        model_size="base"
    )