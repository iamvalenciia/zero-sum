import json

def extract_timestamps():
    try:
        with open('data/video-script.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        video_plan = data.get('video_plan', [])
        
        with open('timestamps_output.txt', 'w', encoding='utf-8') as out:
            out.write(f"Total video_plan items: {len(video_plan)}\n")
            for i, item in enumerate(video_plan):
                start = item.get('start', -1)
                character = item.get('character', 'Unknown')
                text = item.get('text', '')
                clean_text = text.replace('\n', ' ').strip()
                out.write(f"{start:.2f} | {character}: {clean_text}\n")
            
        print("Done writing to timestamps_output.txt")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    extract_timestamps()
