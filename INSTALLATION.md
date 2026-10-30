# Installer Python et les dépendances à la main

`INSTALLER.bat` fait tout automatiquement. Cette page sert quand il ne peut pas : Python absent et
`winget` indisponible, machine verrouillée, ou si tu préfères voir ce qui se passe.

Trois étapes, cinq minutes.

---

## 1. Installer Python

### Méthode rapide (winget)

Ouvre un terminal (`Win+R`, tape `cmd`, Entrée) et lance :

```
winget install --id Python.Python.3.12 --scope user
```

`--scope user` installe dans ton profil : **aucun droit administrateur**, rien au niveau machine.
Python atterrit dans `%LOCALAPPDATA%\Programs\Python\Python312\`.

### Méthode manuelle (sans winget)

1. Va sur **https://www.python.org/downloads/windows/**
2. Télécharge **Windows installer (64-bit)** de la version 3.12.
3. Lance l'installeur et **coche « Add python.exe to PATH »** en bas de la première fenêtre.
   C'est l'option que tout le monde oublie : sans elle, `python` est introuvable en ligne de commande.
4. Choisis **Install Now**. Pas besoin des droits administrateur si tu choisis
   « Install for me only ».

### Vérifier

Ferme et rouvre le terminal, puis :

```
python --version
```

Tu dois voir `Python 3.12.x`. Si la commande n'existe pas, essaie `py --version`.
Si aucune des deux ne répond, Python n'est pas dans le PATH : relance son installeur, choisis
« Modify » et coche « Add Python to environment variables ».

---

## 2. Préparer l'environnement du projet

Ouvre un terminal **dans le dossier de l'installeur** (clic droit dans le dossier → « Ouvrir dans le
Terminal », ou `cd` vers le chemin).

```
python -m venv .venv
.venv\Scripts\python.exe -m pip install --upgrade pip
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Pourquoi un venv

Pour ne rien installer dans ton Python global. Une seule dépendance est nécessaire, `UnityPy`, mais
elle en tire plusieurs (Pillow, lz4, fsspec, brotli) : les isoler évite de perturber d'autres projets.

### Vérifier

```
.venv\Scripts\python.exe -c "import UnityPy; print(UnityPy.__version__)"
```

Tu dois voir un numéro de version (`1.25.x`). S'il y a une erreur, l'étape `pip install` a échoué :
relis son message, la cause est presque toujours la connexion réseau ou un proxy d'entreprise.

---

## 3. Lancer l'installeur

```
.venv\Scripts\python.exe app.py
```

La fenêtre s'ouvre. Elle cherche le jeu, affiche deux lignes — **Textes et menu français** et
**Doublage audio** — avec pour chacune un bouton *Vérifier* et un bouton *Installer*.

Lance *Vérifier* d'abord : la pastille indique l'état actuel (grise = pas installé, verte = en place).
Puis *Installer* sur chaque ligne.

L'écriture dans `C:\Program Files (x86)\Steam\...` demande l'élévation : Windows affiche une demande,
clique **Oui**. C'est inévitable, le jeu est dans un dossier protégé.

### Vérification en ligne de commande

```
.venv\Scripts\python.exe app.py --selftest
```

Sortie attendue :

```
SELFTEST texte: OK - ...
SELFTEST audio: OK - répliques conformes
```

---

## Si ça bloque

| message | cause | solution |
|---|---|---|
| `python n'est pas reconnu` | Python absent du PATH | réinstalle en cochant « Add python.exe to PATH » |
| `impossible de créer .venv` | Python installé depuis le Microsoft Store | installe la version python.org, ou `winget install Python.Python.3.12` |
| `pip` échoue au téléchargement | proxy / pare-feu | `pip install --proxy http://user:pass@proxy:port -r requirements.txt` |
| `Le jeu est ouvert` | jeu en cours | ferme-le, l'installeur refuse d'écrire pendant qu'il tourne |
| pastille rouge sur l'audio | patch refusé | lance en administrateur (clic droit sur le terminal → « Exécuter en tant qu'administrateur ») |

---

## Ce que l'installeur modifie exactement

| fichier | action |
|---|---|
| `GunmanContracts_Data/sharedassets{1..5}.assets` | réoriente les `AudioClip` vers les nouvelles données |
| `GunmanContracts_Data/sharedassets{1..5}.resource` | reçoit les voix françaises à la suite des anglaises |
| `GunmanContracts_Data/GC-FR-backups/` | copie des originaux **avant** la première écriture |
| `GameAssembly.dll`, `sharedassets1.assets` | patch des deux signatures du menu de langue |
| `GC-FR-patch-backup.json` | octets d'origine de ces deux signatures |
| `GunmanContracts_Data/*.orig` | originaux des fichiers de textes |

Rien n'est supprimé. Les voix anglaises restent dans les fichiers ; l'installeur n'ajoute que des
données et change des références.
