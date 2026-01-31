import re
p = r"c:\\Users\\uses\\Downloads\\face recognition\\webapp_new.py"
with open(p, 'rb') as f:
    s = f.read().decode('utf-8')
lines = []
for line in s.splitlines(True):
    m = re.match(r'^(\t+)', line)
    if m:
        tabs = len(m.group(1))
        line = ('    ' * tabs) + line[m.end():]
    lines.append(line)
new = ''.join(lines)
with open(p, 'w', newline='') as f:
    f.write(new)
print('normalized leading tabs to 4 spaces')
