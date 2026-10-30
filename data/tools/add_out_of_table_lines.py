import argparse
import json
import os
import sys

from common import DATA, DE_SLOT, EOL, FR_SLOT, load_table, refuse_if_running, save_table

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_OF_TABLE = os.path.join(HERE, "..", "data", "fr_strings_out_of_table.json")
FIELDS = 11


def row(key, fr, overwrite_german):
    f = [""] * FIELDS
    f[0] = key
    f[FR_SLOT] = fr
    if overwrite_german:
        f[DE_SLOT] = fr
    f[-1] = "end"
    return "|".join(f)


def sync_rows(lines, targets, overwrite_german=False):

    end = len(lines)
    while end > 0 and not lines[end - 1].strip():
        end -= 1
    slots = (FR_SLOT, DE_SLOT) if overwrite_german else (FR_SLOT,)
    out, updated, seen = [], [], set()
    for line in lines[:end]:
        f = line.split("|")
        k = f[0]
        if k in targets and len(f) > FR_SLOT:
            seen.add(k)
            if any(f[s] != targets[k] for s in slots):
                old = f[FR_SLOT]
                for s in slots:
                    f[s] = targets[k]
                out.append("|".join(f))
                updated.append((k, old, targets[k]))
                continue
        out.append(line)
    to_add = sorted((c, v) for c, v in targets.items() if c not in seen)
    return out + [row(c, v, overwrite_german) for c, v in to_add] + lines[end:], to_add, updated


def main():
    ap = argparse.ArgumentParser(description="Sync the lines that are not in the game table")
    ap.add_argument("data", nargs="?", default=DATA)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--overwrite-de", action="store_true",
                    help="also write French into Deutsch (fallback without the menu patch)")
    args = ap.parse_args()
    if not args.apply and not args.dry_run:
        sys.exit("choose --dry-run or --apply")
    if args.apply:
        refuse_if_running()

    targets = json.load(open(OUT_OF_TABLE, encoding="utf-8"))
    path, env, asset = load_table(args.data)
    lines = asset.m_Script.split(EOL)
    new_lines, to_add, updated = sync_rows(lines, targets, args.overwrite_de)

    already = len(targets) - len(to_add)
    print(f"  lines to add: {len(to_add)}   (already present: {already})")
    for c, v in to_add[:6]:
        print(f"    + {c[:44]:44s} {v[:52]}")
    if to_add:
        print("    ...")
    print(f"  lines to UPDATE: {len(updated)}")
    for c, old, new in updated[:8]:
        print(f"    ~ {c[:40]:40s} {old[:40]!r} -> {new[:40]!r}")

    if args.dry_run:
        print("\n  --dry-run: nothing was written.")
        return

    if not to_add and not updated:
        print("\n  nothing to write: the table already carries every line.")
        return

    save_table(path, env, asset, new_lines)
    print(f"  lines added: {len(to_add)} | lines updated: {len(updated)}"
          f"   (table total: {len(new_lines) - 1})")


if __name__ == "__main__":
    main()
