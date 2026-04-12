import json
from collections import defaultdict, Counter

with open(r'data\Group_2\103_2025_QH15_Luat_Tuong_Tro_Tu_Phap_Hinh_Su.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

clauses = data['clauses']
print(f"Total clauses: {len(clauses)}")

articles = set()
for c in clauses:
    articles.add(c['position']['article'])
print(f"Unique articles: {sorted(articles)}")
print(f"Number of unique articles: {len(articles)}")

expected = set(range(1, 43))
missing = expected - articles
extra = articles - expected
print(f"Missing articles: {sorted(missing) if missing else 'None'}")
print(f"Extra articles: {sorted(extra) if extra else 'None'}")

ids = [c['id'] for c in clauses]
dupes = {k:v for k,v in Counter(ids).items() if v > 1}
print(f"Duplicate IDs: {dupes if dupes else 'None'}")

# Article 3
art3 = [c for c in clauses if c['position']['article'] == 3]
print("\n=== Article 3 (Giai thich tu ngu) ===")
for c in art3:
    print(f"  ID: {c['id']}, clause: {c['position']['clause']}, content[:100]: {c['content'][:100]}")
print(f"Total clauses in Art 3: {len(art3)}")
definitions = [c for c in art3 if c['position']['clause'] and c['position']['clause'] >= 1]
print(f"Number of definitions (clauses 1+): {len(definitions)}")

# Article 9
art9 = [c for c in clauses if c['position']['article'] == 9]
print("\n=== Article 9 (Pham vi tuong tro tu phap) ===")
for c in art9:
    print(f"  ID: {c['id']}, clause: {c['position']['clause']}, content[:120]: {c['content'][:120]}")
print(f"Total clauses in Art 9: {len(art9)}")

# Clause counts per article
print("\n=== Clause counts per article ===")
art_clauses = defaultdict(list)
for c in clauses:
    art_clauses[c['position']['article']].append(c)
for art in sorted(art_clauses.keys()):
    cl_list = art_clauses[art]
    title = cl_list[0]['position']['article_title']
    clause_nums = [c['position']['clause'] for c in cl_list]
    print(f"  Art {art}: \"{title}\" - {len(cl_list)} clauses, clause_nums={clause_nums}")

# Check for Muc headers leaked into content
print("\n=== Check for 'Muc X.' leaked into clause content ===")
import re
muc_pattern = re.compile(r'Mục\s+\d+\.')
found_muc = False
for c in clauses:
    if muc_pattern.search(c['content']):
        print(f"  FOUND: {c['id']} contains Muc header: {c['content'][:200]}")
        found_muc = True
if not found_muc:
    print("  No 'Muc X.' headers found in clause content")

# Article 42 - last article, check completeness
print("\n=== Article 42 (last article - Dieu khoan chuyen tiep) ===")
art42 = [c for c in clauses if c['position']['article'] == 42]
for c in art42:
    print(f"  ID: {c['id']}, clause: {c['position']['clause']}")
    print(f"  title: {c['position']['article_title']}")
    print(f"  content: {c['content']}")
    print()

# Cross-references check
print("\n=== Cross-references sample ===")
xref_count = 0
for c in clauses:
    if c['cross_references']:
        xref_count += 1
        if xref_count <= 10:
            print(f"  {c['id']}: {c['cross_references']}")
print(f"Total clauses with cross-references: {xref_count}")

# Chapter assignments
print("\n=== Chapter boundaries ===")
chapter_articles = defaultdict(list)
for art in sorted(art_clauses.keys()):
    ch = art_clauses[art][0]['position']['chapter']
    chapter_articles[ch].append(art)
for ch in sorted(chapter_articles.keys()):
    arts = chapter_articles[ch]
    print(f"  Chapter {ch}: Articles {min(arts)}-{max(arts)} ({len(arts)} articles)")
