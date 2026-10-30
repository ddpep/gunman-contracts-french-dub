import hashlib
import json
import os
import struct

TEXT_PROBES = [
    "story_outpost_intro_4",
    "handler_range_runsuccess_newbest_3",
    "story_range_upperfloorsyringe_handler_04 - v2",
    "handler_range_afterruns_runs_3",
    "story_warehouse_vadim_end_1",
]

AUDIO_ASSETS = [f"sharedassets{n}.assets" for n in (1, 2, 3, 4, 5)]


def md5(b):
    return hashlib.md5(b).hexdigest()


def check_text(data_dir, fr_strings, log=print):
    import UnityPy
    want = json.load(open(fr_strings, encoding="utf-8"))
    env = UnityPy.load(os.path.join(data_dir, "resources.assets"))
    table = None
    for obj in env.objects:
        if obj.type.name != "TextAsset":
            continue
        d = obj.read()
        if getattr(d, "m_Name", "") == "languages":
            table = d
            break
    if table is None:
        return False, "table 'languages' introuvable"
    rows = {ln.split("|")[0]: ln.split("|") for ln in table.m_Script.split("\r\n") if "|" in ln}
    bad = [k for k in TEXT_PROBES if len(rows.get(k, [])) <= 3 or rows[k][3] != want.get(k, "") or not want.get(k)]
    for k in TEXT_PROBES:
        log(f"  texte {k[:44]:44s} {'OK' if k not in bad else 'MANQUANT'}")
    if bad:
        return False, f"{len(bad)} ligne(s) de contrôle non traduites"
    return True, f"{len(TEXT_PROBES)} lignes de contrôle FR en place"


def check_audio(data_dir, vo_repo, manifest_entries, log=print):
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "gc"))
    from unity_assets import clips, resource_blob, payload_at
    by_asset = {}
    for e in manifest_entries:
        by_asset.setdefault(e["asset"], []).append(e)
    total_same = total_diff = total_missing = 0
    for asset in AUDIO_ASSETS:
        entries = by_asset.get(asset, [])
        if not entries:
            continue
        base = asset.replace(".assets", "")
        blob = resource_blob(os.path.join(data_dir, base + ".resource"))
        found = clips(os.path.join(data_dir, asset))
        same = diff = missing = 0
        for e in entries:
            d = found.get(e["key"])
            if d is None or not d.m_Resource:
                missing += 1
                log(f"  MANQUANT {e['key']}")
                continue
            inst = payload_at(blob, d.m_Resource)
            pay = open(os.path.join(vo_repo, e["payload"]), "rb").read()
            if md5(inst) == md5(pay):
                same += 1
            else:
                diff += 1
        total_same += same
        total_diff += diff
        total_missing += missing
        log(f"  audio {base:16s} {same:4d} conformes, {diff:4d} différentes, {missing:4d} manquantes")
    if total_missing:
        return False, f"{total_missing} répliques absentes du jeu ({total_same} conformes)"
    if total_diff:
        return False, f"{total_diff} répliques différentes du doublage"
    return True, f"{total_same} répliques conformes"


def check_menu(game_root, tools_dir, log=print):

    import contextlib
    import io
    import sys
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    try:
        import apply_french_patch
    except Exception as ex:  # noqa: BLE001
        return False, f"outil de patch menu indisponible : {ex}"
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            state = apply_french_patch.check_all(game_root)
    except Exception as ex:  # noqa: BLE001
        return False, f"contrôle du patch menu impossible : {ex}"
    if state is None:
        return False, ("patch menu absent ou signature introuvable "
                       "(version du jeu différente de celle attendue)")
    if state["ga"] != "patched":
        return False, "GameAssembly.dll non patché : le menu n'offre pas le français"
    for st in state["sliders"]:
        if st != "already patched":
            return False, "curseur de langue non étendu : la troisième position est inatteignable"
    return True, "'Français' sélectionnable dans le menu"
