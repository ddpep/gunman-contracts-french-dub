import json
import os
import sys
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
NAME = "GunmanContracts-FR"
FILES = ["app.py", "gamefind.py", "injector.py", "statecheck.py", "texts.py",
         "INSTALLER.bat", "README.md", "README.fr.md", "INSTALLATION.md",
         "requirements.txt"]
DIRS = ["data", "gc"]
EXCLUDE_DIRS = {"__pycache__", ".venv", "venv", ".git", ".github"}
EXCLUDE_EXT = {".pyc", ".pyo"}
MANIFEST = "data/vo/voice_manifest.json"


def entries():
    missing = [n for n in FILES if not os.path.isfile(os.path.join(ROOT, n))]
    if missing:
        raise SystemExit("fichiers attendus absents : %s" % ", ".join(missing))
    for name in FILES:
        p = os.path.join(ROOT, name)
        yield p, name
    for d in DIRS:
        base = os.path.join(ROOT, d)
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [x for x in dirnames if x not in EXCLUDE_DIRS]
            for f in sorted(filenames):
                if os.path.splitext(f)[1] in EXCLUDE_EXT:
                    continue
                full = os.path.join(dirpath, f)
                yield full, os.path.relpath(full, ROOT).replace("\\", "/")


def expected_payloads():
    with open(os.path.join(ROOT, MANIFEST), encoding="utf-8") as f:
        return len(json.load(f)["entries"])


def main():
    out = os.path.join(ROOT, "dist", NAME + ".zip")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for full, rel in entries():
            z.write(full, rel)

    with zipfile.ZipFile(out) as z:
        names = z.namelist()
        bad = z.testzip()

    payloads = sum(1 for n in names if n.startswith("data/vo/payloads/") and n.endswith(".fsb5"))
    wanted = expected_payloads()
    backslash = sum(1 for n in names if "\\" in n)

    print("archive  : %s" % out)
    print("entrees  : %d" % len(names))
    print("payloads : %d (manifeste : %d)" % (payloads, wanted))
    print("taille   : %.1f Mo" % (os.path.getsize(out) / 1048576.0))

    errors = []
    if bad:
        errors.append("archive corrompue (%s)" % bad)
    if MANIFEST not in names:
        errors.append("%s absent" % MANIFEST)
    if "INSTALLER.bat" not in names:
        errors.append("INSTALLER.bat absent")
    if payloads != wanted:
        errors.append("payloads %d, manifeste %d" % (payloads, wanted))
    if backslash:
        errors.append("%d entree(s) avec des separateurs Windows" % backslash)

    for e in errors:
        print("REFUS : " + e, file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
