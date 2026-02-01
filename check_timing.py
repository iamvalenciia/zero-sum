import json

data = json.load(open('data/video-script.json', 'r', encoding='utf-8'))

print("=== IMAGES TIMING ===")
for i, seg in enumerate(data['video_plan']):
    for img in seg.get('contextual_images', []):
        print(f"Seg {i}: {img['id']} -> {img['start_time']}s to {img['end_time']}s")
