with open(r'c:\Users\vinic\Documents\clone\frontend\src\pages\MaintenancePage.jsx', 'r', encoding='utf-8') as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if 'className="w-full min-w-[' in line or 'tab ===' in line or 'map(o => (' in line:
        print(f'{i+1}: {line.strip()}')
