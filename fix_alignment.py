import re

# Read the file
with open('src/core/asset_assembler.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the line numbers we need to replace
start_line = None
end_line = None

for i, line in enumerate(lines):
    if 'if visual_assets and isinstance(visual_assets, list) and visual_assets:' in line:
        start_line = i
    if start_line and 'transition_sound = None' in line:
        end_line = i
        break

print(f"Found block from line {start_line+1} to {end_line+1}")

if start_line and end_line:
    # Get the indentation
    indent = '            '
    
    new_block = f'''{indent}if visual_assets and isinstance(visual_assets, list) and visual_assets:
{indent}    filtered_assets = [va for va in visual_assets if va.get('visual_asset_id') != used_opening_id]
{indent}    
{indent}    for va in filtered_assets:
{indent}        visual_id = va.get('visual_asset_id')
{indent}        if not visual_id:
{indent}            continue
{indent}        
{indent}        # Use word indices for precise timing
{indent}        start_idx = va.get('start_word_index')
{indent}        end_idx = va.get('end_word_index')
{indent}        
{indent}        if start_idx is not None and words:
{indent}            start_idx = max(0, min(start_idx, len(words) - 1))
{indent}            end_idx = max(start_idx, min(end_idx or start_idx, len(words) - 1))
{indent}            start_t = words[start_idx]['start']
{indent}            end_t = words[end_idx]['end']
{indent}        else:
{indent}            seg_start = words[0]['start'] if words else segment.get('start', 0)
{indent}            seg_end = words[-1]['end'] if words else segment.get('end', 0)
{indent}            start_t, end_t = seg_start, seg_end
{indent}
{indent}        contextual_images.append({{
{indent}            "id": visual_id,
{indent}            "path": self._find_contextual_image_path(visual_id),
{indent}            "start_time": round(start_t, 3),
{indent}            "end_time": round(end_t, 3),
{indent}            "is_fullscreen": va.get('is_fullscreen', True)
{indent}        }})

'''
    
    # Replace lines
    new_lines = lines[:start_line] + [new_block] + lines[end_line:]
    
    with open('src/core/asset_assembler.py', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    
    print("OK - File updated!")
else:
    print("Could not find the block to replace")
