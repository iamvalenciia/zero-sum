import json

with open('data/video-script.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

with open('timestamps_clean.txt', 'w', encoding='utf-8') as out:
    for item in data['video_plan']:
        start = item.get('start')
        text = item.get('text', '').replace('\n', ' ')
        out.write(f"{start}: {text[:100]}\n")
