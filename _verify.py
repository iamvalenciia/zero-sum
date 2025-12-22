import json

with open(r'data/video-script.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

seg = d['video_plan'][1]
words = seg.get('words', [])
print(f"Analyst segment: Start={seg.get('start')} End={seg.get('end')}")
print(f"Num words with animation: {len(words)}")
print("\nLast 5 words with times:")
for w in words[-5:]:
    print(f"  {w['text']}: {w['start']:.2f}-{w['end']:.2f}")

print("\n--- Skeptic (segment 2) ---")
seg2 = d['video_plan'][2]
print(f"Character: {seg2.get('character')}")
print(f"Start: {seg2.get('start')}, End: {seg2.get('end')}")
words2 = seg2.get('words', [])
print("First 3 words:")
for w in words2[:3]:
    print(f"  {w['text']}: {w['start']:.2f}-{w['end']:.2f}")
