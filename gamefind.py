import os

GAME_SUB = "Gunman Contracts - Stand Alone"
DATA_DIR = "GunmanContracts_Data"
EXE_NAME = "GunmanContracts.exe"

STATE_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "GC-FR-Installer")


def default_paths():
    cands = [
        "C:/Program Files (x86)/Steam/steamapps/common/" + GAME_SUB,
        "C:/Program Files/Steam/steamapps/common/" + GAME_SUB,
        "D:/Steam/steamapps/common/" + GAME_SUB,
        "E:/Steam/steamapps/common/" + GAME_SUB,
        "F:/Steam/steamapps/common/" + GAME_SUB,
        "G:/Steam/steamapps/common/" + GAME_SUB,
    ]
    try:
        sysdrive = os.environ.get("SystemDrive", "C:")
        cands.insert(0, sysdrive + "/Steam/steamapps/common/" + GAME_SUB)
    except OSError:
        pass
    out, seen = [], set()
    for c in cands:
        c = _norm(c)
        if c not in seen:
            seen.add(c)
            out.append(c)
    return out


def steam_libraries():
    roots = []
    try:
        import winreg
        for hive, sub in ((winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"),
                          (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam"),
                          (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Valve\Steam")):
            try:
                with winreg.OpenKey(hive, sub) as k:
                    p, _ = winreg.QueryValueEx(k, "InstallPath")
                    if p and p not in roots:
                        roots.append(p)
            except OSError:
                continue
    except ImportError:
        pass
    vdf = os.path.join(roots[0], "steamapps", "libraryfolders.vdf") if roots else None
    if vdf and os.path.isfile(vdf):
        try:
            text = open(vdf, encoding="utf-8", errors="replace").read()
            import re
            for m in re.finditer(r'"path"\s+"([^"]+)"', text):
                p = m.group(1).replace("\\\\", "\\")
                if os.path.isdir(p) and p not in roots:
                    roots.append(p)
        except OSError:
            pass
    for cand in (r"C:\Program Files (x86)\Steam", r"C:\Program Files\Steam"):
        if os.path.isdir(cand) and cand not in roots:
            roots.append(cand)
    return roots


def _norm(p):
    if not p:
        return p
    p = p.replace("\\", "/")
    if len(p) > 2 and p[1] == ":":
        return p[:2] + "/" + "/".join(s for s in p[2:].split("/") if s not in ("",))
    return p


def _contains(directory, filename, tries=4, wait=2):
    import time
    for _ in range(tries):
        try:
            if filename in os.listdir(directory):
                return True
        except OSError:
            pass
        time.sleep(wait)
    try:
        return filename in os.listdir(directory)
    except OSError:
        return False


def _exists(path, directory=False, tries=2, wait=1):
    import time
    check = os.path.isdir if directory else os.path.isfile
    for _ in range(tries):
        try:
            if check(path):
                return True
        except OSError:
            pass
        time.sleep(wait)
    return check(path)


def remember_game(path):
    try:
        os.makedirs(STATE_DIR, exist_ok=True)
        with open(os.path.join(STATE_DIR, "last_game.txt"), "w", encoding="utf-8") as f:
            f.write(path)
    except OSError:
        pass


def recalled_game():
    try:
        with open(os.path.join(STATE_DIR, "last_game.txt"), encoding="utf-8") as f:
            p = _norm(f.read().strip())
        if p and _contains(p, EXE_NAME):
            return p, _norm(os.path.join(p, DATA_DIR))
    except OSError:
        pass
    return None, None


def find_game(manual=None, timeout_s=45, log=None):
    import time
    def say(m):
        if log:
            try:
                log(m)
            except OSError:
                pass
    deadline = time.time() + timeout_s
    if manual:
        manual = _norm(manual)
        if _contains(manual, EXE_NAME):
            return manual, _norm(os.path.join(manual, DATA_DIR))
    for base in default_paths():
        if time.time() > deadline:
            break
        say(f"  recherche : {base}")
        if _contains(base, EXE_NAME):
            return base, _norm(os.path.join(base, DATA_DIR))
    for root in steam_libraries():
        say(f"  registre Steam : {root}")
        root = _norm(root)
        for base in (_norm(os.path.join(root, "steamapps", "common", GAME_SUB)),
                     _norm(os.path.join(root, "common", GAME_SUB))):
            say(f"  recherche : {base}")
            if _contains(base, EXE_NAME):
                return base, _norm(os.path.join(base, DATA_DIR))
    say("  introuvable — passez par Parcourir")
    return None, None


def game_running():
    try:
        import subprocess
        out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq GunmanContracts.exe"],
                             capture_output=True, timeout=20).stdout or b""
        return b"GunmanContracts.exe" in out
    except Exception:
        return None
