import argparse
import json
import os
import sys

from common import DATA, DE_SLOT, EOL, FR_SLOT, load_table, refuse_if_running, save_table

HERE = os.path.dirname(os.path.abspath(__file__))
STRINGS = os.path.join(HERE, "..", "data", "fr_strings.json")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Write the translated strings into the game table")
    parser.add_argument("data", nargs="?", default=DATA, help="path to GunmanContracts_Data")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite-de", action="store_true",
                        help="also write French into Deutsch for games without a French language option")
    return parser.parse_args(argv)


def translate_line(line, french, overwrite_german):
    fields = line.split("|")
    if fields[0] not in french or len(fields) <= FR_SLOT:
        return line, False

    translation = french[fields[0]]
    changed = False
    if fields[FR_SLOT] != translation:
        fields[FR_SLOT] = translation
        changed = True
    if overwrite_german and fields[DE_SLOT] != translation:
        fields[DE_SLOT] = translation
        changed = True
    return "|".join(fields), changed


def translate_lines(lines, french, overwrite_german=False):
    out, changed = [], 0
    for i, line in enumerate(lines):
        if i > 0:
            line, was_changed = translate_line(line, french, overwrite_german)
            changed += was_changed
        out.append(line)
    return out, changed


def main():
    args = parse_args()
    if not args.apply and not args.dry_run:
        sys.exit("choose --dry-run or --apply")
    if args.apply:
        refuse_if_running()
    french = json.load(open(STRINGS, encoding="utf-8"))
    path, env, asset = load_table(args.data)

    lines = asset.m_Script.split(EOL)
    out, changed = translate_lines(lines, french, args.overwrite_de)
    for a, b in zip(lines, out):
        if a != b:
            assert len(a.split("|")) == len(b.split("|")), "field count changed - aborting"

    print("entries to update:", changed)
    print("Deutsch overwrite:", "enabled" if args.overwrite_de else "disabled")
    if args.dry_run:
        print("--dry-run: nothing was written.")
        return
    if changed:
        save_table(path, env, asset, out)
    print("entries updated:", changed)
    if args.overwrite_de:
        print("done. In game: Options > Language > Deutsch.")
    else:
        print("done. Select French in game if available; Deutsch was left unchanged.")


if __name__ == "__main__":
    main()
