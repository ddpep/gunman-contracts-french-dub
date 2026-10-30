# Doublage français — Gunman Contracts : Stand Alone

Interface, sous-titres et voix en français pour **Gunman Contracts — Stand Alone**.

> English: see [README.md](README.md).

## Installer

1. Double-clique sur `INSTALLER.bat`.
2. Accepte la demande d'élévation de Windows.
3. Lance le jeu, puis choisis **Français** dans les options.

Aucun mod manager, aucun MelonLoader. Le script prépare son propre environnement Python ; s'il est
absent, il propose de l'installer. Installation manuelle : [INSTALLATION.md](INSTALLATION.md).

## Désinstaller

Vérifie l'intégrité des fichiers du jeu dans Steam (Propriétés → Fichiers installés → Vérifier
l'intégrité). Cela restaure tout ce que l'installeur a modifié.

L'installeur conserve aussi une copie des originaux dans `GunmanContracts_Data/GC-FR-backups` et des
fichiers `*.orig`, utiles pour comparer deux états pendant le développement.

## Fonctionnement

Les textes et le menu sont écrits dans les fichiers d'assets du jeu : la colonne française de la
table de chaînes est remplie, et deux signatures d'octets sont patchées pour que le sélecteur de
langue propose une troisième position. Les voix sont injectées sous forme de payloads FSB5 ajoutés
aux ressources audio. Rien n'est remplacé avant que les originaux aient été copiés.

Une mise à jour du jeu écrase les fichiers patchés. Relance l'installeur ensuite ; il refuse d'écrire
s'il ne reconnaît pas la version.

## Bon à savoir

- Les voix sont synthétiques (générées par IA), pas enregistrées par des comédiens.
- Le français s'ajoute comme troisième langue ; anglais et allemand continuent de fonctionner.
- Aucun fichier du jeu n'est distribué ici : seulement des données ajoutées et des scripts qui
  modifient des références internes, dans des fichiers que l'utilisateur possède déjà.
