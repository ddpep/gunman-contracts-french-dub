import argparse
import datetime
import json
import os
import sys

from common import refuse_if_running

DEFAULT_GAME = r"C:/Program Files (x86)/Steam/steamapps/common/Gunman Contracts - Stand Alone"

BACKUP_NAME = "GC-FR-patch-backup.json"


GA_REL = "GameAssembly.dll"
GA_SIG_OLD = bytes.fromhex("84C07547FFC789BB900A0000")
GA_SIG_NEW = bytes.fromhex("84C0EB47FFC789BB900A0000")
GA_PATCH_REL = 2
GA_OLD = 0x75
GA_NEW = 0xEB

S1_REL = "GunmanContracts_Data/sharedassets1.assets"

SLIDER_WINDOWS = [
    {
        "name": "language switch (copy 1)",
        "old": bytes.fromhex("00000000C50902000000000000000000000000000000000000000000000000000000803F010000000000803F01000000"),
        "new": bytes.fromhex("00000000C509020000000000000000000000000000000000000000000000000000000040010000000000803F01000000"),
    },
    {
        "name": "language switch (copy 2)",
        "old": bytes.fromhex("0000000001D701000000000000000000000000000000000000000000000000000000803F010000000000000001000000"),
        "new": bytes.fromhex("0000000001D7010000000000000000000000000000000000000000000000000000000040010000000000000001000000"),
    },
]


def check_all(game):
    print(f"Game: {game}")
    ok = True

    ga = os.path.join(game, GA_REL)
    s1 = os.path.join(game, S1_REL)
    for p in (ga, s1):
        if not os.path.isfile(p):
            print(f"  [ERROR] file not found: {p}")
            ok = False
    if not ok:
        return None

    with open(ga, "rb") as f:
        ga_blob = f.read()
    if ga_blob.count(GA_SIG_OLD) == 1:
        print("  GameAssembly.dll : to patch (jne)")
        ga_state = "to_patch"
    elif ga_blob.count(GA_SIG_NEW) == 1:
        print("  GameAssembly.dll : already patched (jmp)")
        ga_state = "patched"
    else:
        print("  [ERROR] changeLanguage signature missing or ambiguous in"
              " GameAssembly.dll (different game version?)")
        ga_state = None
        ok = False

    with open(s1, "rb") as f:
        s1_blob = f.read()
    slider_states = []
    for w in SLIDER_WINDOWS:
        if s1_blob.count(w["old"]) == 1:
            st = "to patch"
        elif s1_blob.count(w["new"]) == 1:
            st = "already patched"
        else:
            st = "UNKNOWN (file modified or different version)"
            ok = False
        print(f"  sharedassets1.assets : {w['name']} -> {st}")
        slider_states.append(st)

    print()
    print("Status:", "ready" if ok else "WARNING: see errors above")
    return {"ga": ga_state, "sliders": slider_states} if ok else None


def apply_patch(game):
    state = check_all(game)
    if state is None:
        print("Nothing was modified.")
        return 1

    ga = os.path.join(game, GA_REL)
    s1 = os.path.join(game, S1_REL)

    backup = {
        "date": datetime.datetime.now().isoformat(timespec="seconds"),
        "game": game,
        "patches": [],
    }

    if state["ga"] == "patched":
        print("  [--] GameAssembly.dll : already patched")
    else:
        with open(ga, "r+b") as f:
            blob = f.read()
            off = blob.find(GA_SIG_OLD) + GA_PATCH_REL
            f.seek(off)
            f.write(bytes([GA_NEW]))
        backup["patches"].append({
            "file": GA_REL, "offset": off,
            "old": f"{GA_OLD:02x}", "new": f"{GA_NEW:02x}",
        })
        print(f"  [OK] GameAssembly.dll : 0x{GA_OLD:02x} -> 0x{GA_NEW:02x}")

    for w in SLIDER_WINDOWS:
        with open(s1, "r+b") as f:
            blob = f.read()
            n_old, n_new = blob.count(w["old"]), blob.count(w["new"])
            if n_new == 1 and n_old == 0:
                print(f"  [--] {w['name']} : already patched")
                continue
            if n_old != 1:
                print(f"  [ERROR] {w['name']} : unexpected bytes, site skipped")
                continue
            off = blob.find(w["old"])
            f.seek(off)
            f.write(w["new"])
        backup["patches"].append({
            "file": S1_REL, "offset": off,
            "old": w["old"].hex(), "new": w["new"].hex(),
        })
        print(f"  [OK] {w['name']} : maxValue 1.0 -> 2.0")

    backup_path = os.path.join(game, BACKUP_NAME)
    with open(backup_path, "w", encoding="utf-8") as f:
        json.dump(backup, f, indent=1)
    print("\nOriginal bytes backed up to: " + backup_path)
    print("Patch applied. Launch the game: Options -> Language should offer"
          " English / Deutsch / Francais.")
    return 0


def restore(game):
    ga = os.path.join(game, GA_REL)
    s1 = os.path.join(game, S1_REL)
    for p in (ga, s1):
        if not os.path.isfile(p):
            print(f"[ERROR] file not found: {p}")
            return 1

    with open(ga, "r+b") as f:
        blob = f.read()
        n_old, n_new = blob.count(GA_SIG_OLD), blob.count(GA_SIG_NEW)
        if n_new == 1 and n_old == 0:
            off = blob.find(GA_SIG_NEW) + GA_PATCH_REL
            f.seek(off)
            f.write(bytes([GA_OLD]))
            print("  [OK] GameAssembly.dll : restored (jmp -> jne)")
        elif n_old == 1 and n_new == 0:
            print("  [--] GameAssembly.dll : already original")
        else:
            print("  [ERROR] GameAssembly.dll : unexpected state, left untouched")

    for w in SLIDER_WINDOWS:
        with open(s1, "r+b") as f:
            blob = f.read()
            n_old, n_new = blob.count(w["old"]), blob.count(w["new"])
            if n_new == 1 and n_old == 0:
                off = blob.find(w["new"])
                f.seek(off)
                f.write(w["old"])
                print(f"  [OK] {w['name']} : restored (maxValue 2.0 -> 1.0)")
            elif n_old == 1 and n_new == 0:
                print(f"  [--] {w['name']} : already original")
            else:
                print(f"  [ERROR] {w['name']} : unexpected state, left untouched")

    print("\nRestore complete.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Standalone French patch for Gunman Contracts"
                                             " - Stand Alone (no mod loader)")
    ap.add_argument("game", nargs="?", default=DEFAULT_GAME,
                    help="game folder (the one containing GameAssembly.dll)")
    ap.add_argument("--check", action="store_true", help="check only, write nothing")
    ap.add_argument("--restore", action="store_true", help="restore the original bytes")
    args = ap.parse_args(argv)

    game = args.game.replace("\\", "/")
    if not args.check:
        refuse_if_running()
    if args.restore:
        return restore(game)
    if args.check:
        return 0 if check_all(game) is not None else 1
    return apply_patch(game)


if __name__ == "__main__":
    sys.exit(main())
