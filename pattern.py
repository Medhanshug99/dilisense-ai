parent_min, parent_max = 4, 6

def chunk_groups(children, parent_min, parent_max):
    total = len(children)
    if total == 0: return []
    if total < parent_min: return [children]
    n_min_groups = (total + parent_max - 1) // parent_max
    n_max_groups = total // parent_min
    if n_max_groups < n_min_groups:
        return [children]
    n_groups = n_min_groups
    target = total // n_groups
    leftover = total - n_groups * target
    sizes = [target] * n_groups
    for i in range(leftover):
        sizes[i] += 1
    return sizes

print('n=7 case:')
print(chunk_groups(list(range(7)), 4, 6))
print('n=11 case:')
print(chunk_groups(list(range(11)), 4, 6))
print()
print('PATTERN n=4..20:')
for n in range(4, 21):
    print(f'  n={n:2d}  groups={chunk_groups(list(range(n)), 4, 6)}')
