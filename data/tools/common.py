import datetime
import os
import shutil
import subprocess
import sys

DATA = r"C:/Program Files (x86)/Steam/steamapps/common/Gunman Contracts - Stand Alone/GunmanContracts_Data"
EXE = "GunmanContracts.exe"
DE_SLOT = 2
FR_SLOT = 3
EOL = "\r\n"
MIN_RATIO = 0.9


def game_running():

    try:
        out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {EXE}"],
                             capture_output=True, timeout=20).stdout or b""
    except Exception:                                                   # noqa: BLE001
        return None
    return EXE.encode()[:14] in out


def refuse_if_running():
    state = game_running()
    if state:
        sys.exit("REFUSING: the game is running. Close it first.")
    if state is None:
        print("WARNING: could not check whether the game is running - verify by hand.")


def backup(path):
    orig = path + ".orig"
    if not os.path.exists(orig):
        shutil.copy2(path, orig)
        print("  original kept:", orig)
    stamp = path + ".orig-backup-" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(path, stamp)
    print("  backup:", stamp)


def write_replacing(path, blob, verify=None):

    size = os.path.getsize(path)
    if len(blob) < MIN_RATIO * size:
        sys.exit(f"REFUSING to write: output {len(blob)} bytes against {size} on disk")
    tmp = path + ".tmp-write"
    with open(tmp, "wb") as fh:
        fh.write(blob)
    error = verify(tmp) if verify else None
    if error:
        os.remove(tmp)
        sys.exit("REFUSING to install: " + error)
    os.replace(tmp, path)


def find_languages(env):
    for obj in env.objects:
        if obj.type.name != "TextAsset":
            continue
        data = obj.read()
        if getattr(data, "m_Name", "") == "languages":
            return data
    return None


def load_table(data_dir):
    import UnityPy

    path = os.path.join(data_dir, "resources.assets")
    if not os.path.exists(path):
        sys.exit("game not found at " + path)
    env = UnityPy.load(path)
    asset = find_languages(env)
    if asset is None:
        sys.exit("TextAsset 'languages' not found - unexpected game build")
    return path, env, asset


def release(env):

    import gc

    containers = list(getattr(env, "files", {}).values())
    single = getattr(env, "file", None)
    if single is not None:
        containers.append(single)
    for container in containers:
        reader = getattr(container, "reader", None)
        if reader is not None:
            reader.dispose()
    gc.collect()


def save_table(path, env, asset, lines):
    import UnityPy

    text = EOL.join(lines)
    asset.m_Script = text
    asset.save()
    blob = env.file.save()

    def same_table(tmp):
        check = UnityPy.load(tmp)
        written = find_languages(check)
        ok = written is not None and written.m_Script == text
        release(check)
        return None if ok else \
            "the written table does not read back identical"

    backup(path)
    release(env)
    write_replacing(path, blob, same_table)
