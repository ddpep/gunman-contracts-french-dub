import json
import os
import shutil
import sys

TEXT_FILES = ("resources.assets", "sharedassets1.assets", "sharedassets2.assets",
              "sharedassets3.assets", "sharedassets4.assets", "globalgamemanagers")


def _tools(tools_dir):
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    import common
    import apply_text
    import add_out_of_table_lines
    import apply_scene_hints
    import apply_french_patch
    return common, apply_text, add_out_of_table_lines, apply_scene_hints, apply_french_patch


def install_texts(data_dir, tools_dir, data_dir_json, log=print):
    common, apply_text, add_out_of_table, apply_scene_hints, apply_french_patch = _tools(tools_dir)
    if common.game_running():
        return "le jeu tourne : ferme-le avant d'installer"
    french = json.load(open(os.path.join(data_dir_json, "fr_strings.json"), encoding="utf-8"))
    path, env, asset = common.load_table(data_dir)
    lines = asset.m_Script.split(common.EOL)
    out, changed = apply_text.translate_lines(lines, french, False)
    log(f"table : {changed} ligne(s) à écrire")
    if changed:
        for a, b in zip(lines, out):
            if a != b:
                assert len(a.split("|")) == len(b.split("|")), "champ modifié ? abandon"
        common.save_table(path, env, asset, out)
        log("table écrite")
    else:
        common.release(env)
        log("table déjà à jour")

    targets = json.load(open(os.path.join(data_dir_json, "fr_strings_out_of_table.json"), encoding="utf-8"))
    path, env, asset = common.load_table(data_dir)
    new_lines, to_add, updated = add_out_of_table.sync_rows(asset.m_Script.split(common.EOL), targets, False)
    log(f"hors-table : {len(to_add)} à ajouter, {len(updated)} à mettre à jour")
    if to_add or updated:
        common.save_table(path, env, asset, new_lines)
    else:
        common.release(env)

    pairs = {k: v for k, v in json.load(open(os.path.join(data_dir_json, "scene_hints.json"), encoding="utf-8")).items()
             if not k.startswith("_")}
    for sc in apply_scene_hints.SCENES:
        p = os.path.join(data_dir, sc)
        if not os.path.exists(p):
            continue
        raw = open(p, "rb").read()
        new_raw, reps = apply_scene_hints.replace_in_bytes(raw, pairs)
        if reps:
            common.backup(p)
            common.write_replacing(p, new_raw)
            log(f"indices : {sc} ({len(reps)} remplacements)")
    log("indices : ok")

    rc = apply_french_patch.apply_patch(os.path.dirname(data_dir))
    if rc == 0:
        log("menu français : ok")
        return None
    log("menu français : NON APPLIQUÉ — signatures introuvables (version du jeu changée ?)")
    return "menu français non appliqué : le patch ne reconnaît pas cette version du jeu"


def restore_texts(data_dir, log=print):
    n = 0
    for f in TEXT_FILES:
        orig = os.path.join(data_dir, f + ".orig")
        if os.path.exists(orig):
            shutil.copy2(orig, os.path.join(data_dir, f))
            log(f"  restauré : {f}")
            n += 1
    try:
        import apply_french_patch
        if apply_french_patch.restore(os.path.dirname(data_dir)) == 0:
            log("  menu : signatures restaurées")
    except Exception as ex:
        log("  menu : restauration impossible (%s)" % ex)
    if not n:
        log("  aucun .orig à restaurer")
    return n
