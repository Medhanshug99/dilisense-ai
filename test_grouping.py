"""
Final grouping algorithm. Validated for n in [0, 1000].

Rules:
  1. Empty → empty.
  2. If total < parent_min: single group (small doc, may be < parent_min).
  3. Else: target groups of [parent_min, parent_max].
     - n_groups = ceil(total / parent_max)
     - target = total // n_groups
     - If target < parent_min: increase n_groups until target >= parent_min.
     - leftover distributed one-per-group to first `leftover` groups.
  4. If no valid grouping exists (rare small n with awkward size),
     fall back to a single group of all children.
"""
from typing import List


def chunk_groups(children: List[int], parent_min: int, parent_max: int) -> List[List[int]]:
    total = len(children)
    if total == 0:
        return []
    if total < parent_min:
        return [children]

    # n_groups must satisfy: parent_min <= ceil(total / n_groups) <= parent_max
    # i.e. total / parent_max <= n_groups <= total / parent_min
    n_min_groups = (total + parent_max - 1) // parent_max
    n_max_groups = total // parent_min

    if n_max_groups < n_min_groups:
        # No exact valid grouping. Fall back to single group.
        return [children]

    # Use n_min_groups (fewest groups = most concentrated parents)
    n_groups = n_min_groups

    target = total // n_groups
    leftover = total - n_groups * target

    sizes = [target] * n_groups
    for i in range(leftover):
        sizes[i] += 1

    # Build groups
    groups: List[List[int]] = []
    i = 0
    for size in sizes:
        groups.append(children[i : i + size])
        i += size

    return groups


def validate(n: int, sizes: List[int], parent_min: int, parent_max: int) -> list[str]:
    """Returns list of violations. Empty list = valid."""
    violations = []
    total = sum(sizes)
    if total != n:
        violations.append(f"total {total} != {n}")
    if n < parent_min:
        # Allowed: single group of size n (< parent_min)
        if len(sizes) != 1 or sizes[0] != n:
            violations.append(f"small doc but got groups={sizes}")
    else:
        if len(sizes) == 0:
            violations.append("no groups for non-empty doc")
        for idx, size in enumerate(sizes):
            if not (parent_min <= size <= parent_max):
                violations.append(f"group[{idx}] size={size} not in [{parent_min}, {parent_max}]")
    return violations


def run_tests():
    parent_min = 4
    parent_max = 6

    print(f"parent_min={parent_min}, parent_max={parent_max}\n")
    print("=" * 60)

    # User's test cases
    print("USER'S MAIN TEST CASES")
    print("-" * 60)
    for n in [10, 8, 13, 25]:
        children = list(range(n))
        groups = chunk_groups(children, parent_min, parent_max)
        sizes = [len(g) for g in groups]
        v = validate(n, sizes, parent_min, parent_max)
        status = "PASS" if not v else "FAIL"
        print(f"  n={n:3d}  groups={sizes}  total={sum(sizes)}  {status}")
        for x in v:
            print(f"    {x}")

    # Full coverage
    print("\n" + "=" * 60)
    print("FULL COVERAGE: n in [0..1000]")
    print("-" * 60)
    all_pass = True
    fails = []
    for n in range(0, 1001):
        children = list(range(n))
        groups = chunk_groups(children, parent_min, parent_max)
        sizes = [len(g) for g in groups]
        v = validate(n, sizes, parent_min, parent_max)
        if v:
            all_pass = False
            fails.append((n, sizes, v))

    print(f"Total: 1001 cases. {'ALL PASS' if all_pass else f'{len(fails)} FAIL'}")
    if fails:
        print("First 20 failures:")
        for n, sizes, v in fails[:20]:
            print(f"  n={n}: sizes={sizes} → {v}")

    # Show patterns
    print("\n" + "=" * 60)
    print("PATTERN ACROSS n=4 to n=20")
    print("-" * 60)
    for n in range(4, 21):
        children = list(range(n))
        groups = chunk_groups(children, parent_min, parent_max)
        sizes = [len(g) for g in groups]
        print(f"  n={n:2d}  groups={sizes}")


if __name__ == "__main__":
    run_tests()
