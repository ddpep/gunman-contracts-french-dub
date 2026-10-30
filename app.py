import ctypes
import gc
import json
import os
import queue
import shutil
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox

HERE = os.path.dirname(os.path.abspath(__file__))


def res(*parts):
    base = getattr(sys, "_MEIPASS", HERE)
    return os.path.join(base, *parts)


sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "gc"))
import gamefind
import statecheck
import texts
from injector import inject_payloads, load_payloads

DATA = res("data")
VO_REPO = res("data", "vo")


def log_to(widget, q, root):
    try:
        while True:
            item = q.get_nowait()
            if isinstance(item, tuple):
                kind = item[0]
                if kind == "log":
                    widget.insert(tk.END, item[1] + "\n")
                    widget.see(tk.END)
                elif kind == "state":
                    _, key, color, text = item
                    if key not in root.sections:
                        return
                    dot, dot_id, detail = root.sections[key]
                    dot.itemconfig(dot_id, fill=color)
                    detail.config(text=text)
                elif kind == "path":
                    root.path_var.set(item[1])
                continue
            widget.insert(tk.END, str(item) + "\n")
            widget.see(tk.END)
    except queue.Empty:
        pass


def with_retry(fn, log, tries=4):
    import time
    for i in range(tries):
        try:
            return fn()
        except OSError as ex:
            if i == tries - 1:
                raise
            log(f"  fichier verrouillé ({ex.strerror or ex}), nouvel essai…")
            time.sleep(3)
    return None


BACKUP_DIRNAME = "GC-FR-backups"


def _backup_dir(data_dir):

    d = os.path.join(data_dir, BACKUP_DIRNAME)
    os.makedirs(d, exist_ok=True)
    return d


def _lengths_by_asset(manifest):
    out = {}
    for e in manifest:
        if e.get("length_s"):
            out.setdefault(e["asset"], {})[e["key"]] = float(e["length_s"])
    return out


def _swap_in_place(tmp_path, target_path):
    gc.collect()
    try:
        os.replace(tmp_path, target_path)
    except PermissionError:
        shutil.copy2(tmp_path, target_path)
        os.remove(tmp_path)


def install_audio(data_dir, log=print):

    manifest = json.load(open(os.path.join(VO_REPO, "voice_manifest.json"), encoding="utf-8"))["entries"]
    lengths = _lengths_by_asset(manifest)
    bk = _backup_dir(data_dir)
    tmpdir = os.path.join(data_dir, ".gc-fr-tmp")
    os.makedirs(tmpdir, exist_ok=True)

    done = 0
    try:
        for n in (1, 2, 3, 4, 5):
            asset = "sharedassets%d.assets" % n
            base = "sharedassets%d" % n
            src_a = os.path.join(data_dir, asset)
            src_r = os.path.join(data_dir, base + ".resource")
            if not (os.path.exists(src_a) and os.path.exists(src_r)):
                log("  %s absent, ignore" % base)
                continue

            for src in (src_a, src_r):
                dst = os.path.join(bk, os.path.basename(src))
                if not os.path.exists(dst):
                    shutil.copy2(src, dst)
                    log("  sauvegarde : %s" % os.path.basename(src))

            payloads = load_payloads(VO_REPO, manifest, by_asset=asset)
            tmp_a = os.path.join(tmpdir, asset)
            tmp_r = os.path.join(tmpdir, base + ".resource")
            cnt, _ = inject_payloads(src_a, src_r, tmp_a, tmp_r, payloads, lengths.get(asset))
            gc.collect()

            swapped = []
            try:
                for t, target in ((tmp_a, src_a), (tmp_r, src_r)):
                    _swap_in_place(t, target)
                    swapped.append(target)
            except Exception:
                for target in swapped:
                    shutil.copy2(os.path.join(bk, os.path.basename(target)), target)
                log("  ECHEC sur %s : fichiers d'origine restaures" % base)
                raise
            done += cnt
            log("  %s : %d repliques ecrites" % (base, cnt))
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    return done


def restore_audio(data_dir, log=print):
    bk = os.path.join(data_dir, BACKUP_DIRNAME)
    if not os.path.isdir(bk):
        raise RuntimeError("aucune sauvegarde dans %s" % BACKUP_DIRNAME)
    n = 0
    for name in sorted(os.listdir(bk)):
        src = os.path.join(bk, name)
        dst = os.path.join(data_dir, name)
        if os.path.isfile(src):
            shutil.copy2(src, dst)
            n += 1
            log("  restaure : %s" % name)
    return n


def elevated():
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return True


def relaunch_elevated(argv):
    params = " ".join('"%s"' % a for a in argv)
    rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable,
                                             '"%s" %s' % (os.path.abspath(__file__), params),
                                             HERE, 1)
    return rc > 32


class App:
    def __init__(self, root):
        self.root = root
        root.title("Gunman Contracts — installateur FR")
        self.game, self.data = None, None
        self.q = queue.Queue()
        top = tk.Frame(root)
        top.pack(fill=tk.X, padx=8, pady=6)
        tk.Label(top, text="Jeu :").pack(side=tk.LEFT)
        self.path_var = tk.StringVar(value="recherche du jeu…")
        tk.Entry(top, textvariable=self.path_var, width=64, state="readonly").pack(side=tk.LEFT, padx=6)
        tk.Button(top, text="Parcourir…", command=self.browse).pack(side=tk.LEFT)
        self.sections = {}
        for key, title in (("text", "Textes et menu français"), ("audio", "Doublage audio")):
            fr = tk.LabelFrame(root, text=title, font=("Segoe UI", 10, "bold"))
            fr.pack(fill=tk.X, padx=10, pady=5)
            dot = tk.Canvas(fr, width=22, height=22, highlightthickness=0)
            dot.pack(side=tk.LEFT, padx=8)
            dot_id = dot.create_oval(4, 4, 18, 18, fill="gray", outline="")
            detail = tk.Label(fr, text="en attente…", anchor="w", font=("Segoe UI", 10))
            detail.pack(side=tk.LEFT, fill=tk.X, expand=True)
            btns = tk.Frame(fr)
            btns.pack(side=tk.RIGHT, padx=6)
            tk.Button(btns, text="Vérifier", command=lambda k=key: self.run("check", k)).pack(side=tk.LEFT)
            tk.Button(btns, text="Installer", command=lambda k=key: self.run("install", k)).pack(side=tk.LEFT, padx=4)
            tk.Button(btns, text="Restaurer", command=lambda k=key: self.run("restore", k)).pack(side=tk.LEFT)
            self.sections[key] = (dot, dot_id, detail)
        logbar = tk.Frame(root)
        logbar.pack(fill=tk.X, padx=10)
        self.log_visible = tk.BooleanVar(value=False)
        tk.Checkbutton(logbar, text="Journal détaillé", variable=self.log_visible,
                       command=self.toggle_log).pack(side=tk.LEFT)
        logframe = tk.Frame(root)
        self.log_scroll = tk.Scrollbar(logframe)
        self.log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.logw = tk.Text(logframe, height=12, width=100, state="normal", font=("Consolas", 9),
                            yscrollcommand=self.log_scroll.set)
        self.log_scroll.config(command=self.logw.yview)
        self.logw.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.logframe = logframe
        self.toggle_log()
        self.log("Démarrage — recherche du jeu (Steam)…")
        threading.Thread(target=self._boot, daemon=True).start()
        self.after_boot_check()

    def toggle_log(self):
        if self.log_visible.get():
            self.logframe.pack(fill=tk.BOTH, expand=True, padx=10, pady=6)
            self.root.geometry("")
        else:
            self.logframe.pack_forget()
            self.root.geometry("")
            self.root.update_idletasks()
            self.root.geometry(f"{self.root.winfo_width()}x{self.root.winfo_reqheight()}")

    def after_boot_check(self):
        self._drain()
        if self.game or self.path_var.get() not in ("recherche du jeu…",):
            return
        self.root.after(200, self.after_boot_check)

    def _boot(self):
        try:
            game, data = gamefind.recalled_game()
            if not data:
                self.log("Recherche du jeu (Steam)…")
                game, data = gamefind.find_game(timeout_s=45, log=self.log)
        except Exception as ex:  # noqa: BLE001
            self.set_path("(détection impossible — utilisez Parcourir)")
            self.log(f"ERREUR détection : {ex}")
            return
        if not data:
            self.set_path("(non trouvé — utilisez Parcourir)")
            self.log("Jeu introuvable automatiquement — utilisez Parcourir…")
            return
        self.game, self.data = game, data
        gamefind.remember_game(game)
        self.set_path(game)
        self.log(f"Jeu trouvé : {game}")
        for k in ("text", "audio"):
            self.run("check", k)

    def log(self, msg):
        self.q.put(("log", msg))

    def set_state(self, key, color, text):
        self.q.put(("state", key, color, text))

    def set_path(self, value):
        self.q.put(("path", value))

    def browse(self):
        start = "C:/"
        for cand in gamefind.default_paths():
            parent = os.path.dirname(cand)
            if os.path.isdir(parent):
                start = parent
                break
        d = filedialog.askdirectory(title="Dossier du jeu (celui qui contient GunmanContracts.exe)",
                                    initialdir=start, mustexist=True)
        if d:
            g, data = gamefind.find_game(d)
            if g:
                self.game, self.data = g, data
                gamefind.remember_game(g)
                self.path_var.set(g)
                for k in ("text", "audio"):
                    self.run("check", k)
            else:
                messagebox.showerror("Jeu introuvable", "Pas de GunmanContracts_Data/resources.assets ici.")

    def run(self, action, key):
        if not self.data:
            import gamefind as _gf
            start = "C:/"
            for cand in _gf.default_paths():
                parent = os.path.dirname(cand)
                if os.path.isdir(parent):
                    start = parent
                    break
            d = filedialog.askdirectory(title="Dossier du jeu (GunmanContracts.exe est dedans)",
                                        initialdir=start, mustexist=True)
            if not d:
                return
            g, data = gamefind.find_game(d, timeout_s=60)
            if not g:
                messagebox.showerror("Jeu introuvable", "Pas de GunmanContracts.exe ici.")
                return
            self.game, self.data = g, data
            gamefind.remember_game(g)
            self.set_path(g)
            self.log(f"Jeu : {g}")
        if gamefind.game_running():
            messagebox.showwarning("Jeu ouvert", "Ferme le jeu avant toute écriture ou vérification.")
            return
        self.set_state(key, "orange", "en cours…")
        threading.Thread(target=self._work, args=(action, key), daemon=True).start()
        self.root.after(200, self._drain)

    def _drain(self):
        log_to(self.logw, self.q, self)
        if any(t.is_alive() for t in threading.enumerate() if t is not threading.main_thread()):
            self.root.after(200, self._drain)
        elif not self.q.empty():
            self.root.after(200, self._drain)

    def _work(self, action, key):
        log = lambda m: self.q.put(("log", m))
        try:
            if key == "text":
                self._text(action, log)
            elif key == "audio":
                self._audio(action, log)
        except Exception as ex:  # noqa: BLE001 (show, don't crash the GUI)
            log(f"ERREUR : {ex}")
            self.set_state(key, "red", f"erreur : {ex}")

    def _text(self, action, log):
        tools = os.path.join(DATA, "tools")
        if action == "restore":
            n = with_retry(lambda: texts.restore_texts(self.data, log), log)
            self.set_state("text", "gray", "%d fichier(s) restaure(s) - relance une verification" % n)
            return

        ok_t, d_t = statecheck.check_text(self.data, os.path.join(DATA, "fr_strings.json"), log)
        ok_m, d_m = statecheck.check_menu(os.path.dirname(self.data), tools, log)

        if action == "check":
            detail = d_t + " / " + d_m
            self.set_state("text", "green" if (ok_t and ok_m) else "red", detail)
            return

        if ok_t and ok_m:
            self.set_state("text", "green", "deja installe - rien a faire")
            return

        err = with_retry(lambda: texts.install_texts(self.data, tools, DATA, log), log)
        if err:
            self.set_state("text", "red", err)
            return
        ok2, d2 = statecheck.check_text(self.data, os.path.join(DATA, "fr_strings.json"), log)
        okm2, dm2 = statecheck.check_menu(os.path.dirname(self.data), tools, log)
        if ok2 and okm2:
            self.set_state("text", "green", "textes installes, francais dans le menu")
        else:
            self.set_state("text", "red", (d2 if not ok2 else "") + " " + (dm2 if not okm2 else ""))

    def _install_audio(self, log):
        with_retry(lambda: install_audio(self.data, log), log)

    def _audio(self, action, log):
        manifest = json.load(open(os.path.join(VO_REPO, "voice_manifest.json"), encoding="utf-8"))["entries"]
        if action == "restore":
            try:
                n = restore_audio(self.data, log)
                self.set_state("audio", "gray", "%d fichier(s) restaure(s) - relance une verification" % n)
            except Exception as ex:
                self.set_state("audio", "red", "restauration impossible : %s" % ex)
            return
        if action == "install":
            ok_before, d_before = statecheck.check_audio(self.data, VO_REPO, manifest, log)
            if ok_before:
                self.set_state("audio", "green", "deja installe - rien a faire")
                return
            with_retry(lambda: self._install_audio(log), log)
            log("audio installe - verification...")
        ok, detail = statecheck.check_audio(self.data, VO_REPO, manifest, log)
        self.set_state("audio", "green" if ok else "red", detail)


def selftest():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--install", action="store_true",
                    help="also (re)install mod+audio (idempotent), then re-check.")
    ap.add_argument("--game", default=None)
    a, _ = ap.parse_known_args()
    game, data = gamefind.find_game(a.game, timeout_s=180)
    if not data:
        print("SELFTEST: jeu introuvable")
        return 2
    print("SELFTEST jeu: %s" % game)
    if a.install:
        if gamefind.game_running():
            print("SELFTEST: le jeu tourne, ecriture refusee")
            return 3
        err = with_retry(lambda: texts.install_texts(data, os.path.join(DATA, "tools"), DATA, print), print)
        if err:
            print("SELFTEST texte: %s" % err)
            return 4
        manifest = json.load(open(os.path.join(VO_REPO, "voice_manifest.json"), encoding="utf-8"))["entries"]
        ok_a, _ = statecheck.check_audio(data, VO_REPO, manifest, print)
        if ok_a:
            print("SELFTEST audio: deja installe, rien a faire")
        else:
            with_retry(lambda: install_audio(data, print), print)
        print("SELFTEST: installe, reverification...")
    manifest = json.load(open(os.path.join(VO_REPO, "voice_manifest.json"), encoding="utf-8"))["entries"]
    ok_t, d_t = statecheck.check_text(data, os.path.join(DATA, "fr_strings.json"), print)
    ok_m, d_m = statecheck.check_menu(game, os.path.join(DATA, "tools"), print)
    if ok_t and not ok_m:
        ok_t, d_t = False, d_t + " / " + d_m
    elif ok_t:
        d_t = d_t + " / " + d_m
    print("SELFTEST texte: %s - %s" % ("OK" if ok_t else "KO", d_t))
    ok_a, d_a = statecheck.check_audio(data, VO_REPO, manifest, print)
    print("SELFTEST audio: %s - %s" % ("OK" if ok_a else "KO", d_a))
    return 0 if (ok_t and ok_a) else 1


def main():
    import sys as _s
    import traceback
    if "--selftest" in _s.argv:
        _s.exit(selftest())
    if not elevated() and "--no-elevate" not in _s.argv:
        args = [a for a in _s.argv[1:] if a != "--no-elevate"]
        if relaunch_elevated(args):
            _s.exit(0)
    try:
        root = tk.Tk()
    except Exception:
        try:
            with open(os.path.join(os.path.expanduser("~"), "GC-FR-Installer-erreur.txt"), "w") as f:
                f.write(traceback.format_exc())
        except OSError:
            pass
        raise
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
