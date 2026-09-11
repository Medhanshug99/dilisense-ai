from typing import List

def chunk_groups(children: List[int], parent_min: int, parent_max: int) -> List[List[int]]:
    total = len(children)
    if total == 0: return []
    if total < parent_min: return [children]
    n_groups = (total + parent_max - 1) // parent_max
    n_max_groups = total // parent_min
    if n_max_groups < n_groups:
        return [children]
    target_size = total // n_groups
    leftover = total - n_groups * target_size
    sizes = [target_size] * n_groups
    for i in range(leftover):
        sizes[i] += 1
    groups = []
    i = 0
    for size in sizes:
        groups.append(children[i:i+size])
        i += size
    return groups

parent_min, parent_max = 4, 6

print("USER REQUESTED CASES")
print("=" * 60)
for n in [10, 8, 13, 25]:
    groups = chunk_groups(list(range(n)), parent_min, parent_max)
    sizes = [len(g) for g in groups]
    valid = all(parent_min <= s <= parent_max for s in sizes) or (n < parent_min)
    print(f"  n={n:3d}  groups={sizes}  total={sum(sizes)}  valid={valid}")

print()
print("FULL PATTERN n=4..30")
print("=" * 60)
for n in range(4, 31):
    groups = chunk_groups(list(range(n)), parent_min, parent_max)
    sizes = [len(g) for g in groups]
    print(f"  n={n:2d}  groups={sizes}")

print()
print("VALIDATION n=0..1000")
print("=" * 60)
fails = []
for n in range(0, 1001):
    groups = chunk_groups(list(range(n)), parent_min, parent_max)
    sizes = [len(g) for g in groups]
    total = sum(sizes)
    if total != n:
        fails.append((n, "total mismatch"))
        continue
    if n < parent_min:
        if not (len(sizes) == 1 and sizes[0] == n):
            fails.append((n, "small doc not single group"))
        continue
    for s in sizes:
        if not (parent_min <= s <= parent_max):
            fails.append((n, f"size {s} out of range"))
            break
print(f"Result: {'ALL PASS' if not fails else f'{len(fails)} FAIL'}")
if fails:
    for f in fails[:20]: print(f)
