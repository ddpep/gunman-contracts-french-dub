# Gunman Contracts — French dub

French interface, subtitles and voices for **Gunman Contracts — Stand Alone**.

> Joueurs francophones : voir [README.fr.md](README.fr.md).

## Install

1. Double-click `INSTALLER.bat`.
2. Accept the Windows elevation prompt.
3. Launch the game and pick **Français** in the options.

No mod manager, no MelonLoader. The script prepares its own Python environment; if Python is missing it
offers to install it. Manual instructions: [INSTALLATION.md](INSTALLATION.md).

## Undo

Verify the game's files in Steam (Properties → Installed files → Verify integrity). That restores
everything the installer modified.

The installer also keeps a copy of the originals in `GunmanContracts_Data/GC-FR-backups` and `*.orig`
files, which is useful when comparing states during development.

## How it works

Texts and menu are written into the game's asset files: the French column of the string table is
filled, and two byte signatures are patched so the language selector offers a third position. Voices
are injected as prebuilt FSB5 payloads appended to the audio resources. Nothing is replaced on disk
before the originals have been copied.

A game update overwrites the patched files. Run the installer again afterwards; it refuses to write
if it does not recognise the version.

## Notes

- The voices are synthetic (AI-generated), not recorded by actors.
- French adds a third language; English and German keep working.
- No game content is distributed here: only added data and scripts that repoint references inside
  files the user already owns.
