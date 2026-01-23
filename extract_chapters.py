import json

def extract_timestamps(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    video_plan = data.get('video_plan', [])
    
    output_file = r'c:\Users\juanf\OneDrive\Escritorio\zero-sum-yt\timestamps_output.txt'
    with open(output_file, 'w', encoding='utf-8') as out:
        out.write(f"{'Time':<10} | {'Audio Duration':<10} | {'Character':<10} | {'Text'}\n")
        out.write("-" * 100 + "\n")
        
        for segment in video_plan:
            start_time = segment.get('start', 0.0)
            end_time = segment.get('end', 0.0)
            duration = end_time - start_time
            character = segment.get('character', 'Unknown')
            text = segment.get('text', '').replace('\n', ' ')
            
            # Format time as MM:SS
            minutes = int(start_time // 60)
            seconds = int(start_time % 60)
            formatted_time = f"{minutes:02}:{seconds:02}"
            
            out.write(f"{formatted_time:<10} | {duration:<10.2f} | {character:<10} | {text[:50]}...\n")
    print(f"Output written to {output_file}")

if __name__ == "__main__":
    extract_timestamps(r'c:\Users\juanf\OneDrive\Escritorio\zero-sum-yt\data\video-script.json')
