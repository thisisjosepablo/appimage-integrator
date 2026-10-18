# AppImage Integrator

**A safe, reversible, user-level desktop integration manager for Linux AppImages.**

AppImage Integrator organizes an AppImage, creates a standards-compliant `.desktop` launcher, manages an optional icon, and records enough metadata to uninstall cleanly. It is designed for people who want their downloaded AppImages to behave like ordinary desktop applications—without root access.

> **Security note:** An AppImage is executable code. This tool never launches an application to install it. Resource extraction, which may execute the AppImage runtime, is deliberately not part of the default workflow.

## Goals

- User-only installation: no `sudo`, no writes to `/usr`.
- Reversible operations and conservative overwrite behavior.
- Desktop Entry files with correctly quoted executable paths.
- Stable IDs, duplicate detection, inventory, dry runs and uninstall.
- No third-party Python dependencies.
- Automated tests and CI.

## Requirements

- Linux
- Python 3.10+
- A desktop environment supporting the freedesktop.org Desktop Entry specification

## Quick start

Clone the repository and run the tool directly:

```bash
git clone https://github.com/thisisjosepablo/appimage-integrator.git
cd appimage-integrator
python3 -m appimage_integrator --help
```

For development, install it in an isolated environment:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
appimage-integrator --help
```

An optional graphical interface is also available when Tkinter is installed:

```bash
appimage-integrator-gui
```

Install directly from the source checkout without publishing a package:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
appimage-integrator --help
```

On some distributions Tkinter is packaged separately (for example, as `python3-tk`). The CLI remains fully usable without a graphical environment.

### Install an AppImage

```bash
appimage-integrator install ~/Downloads/MyApp.AppImage
```

By default the source is **copied**, not moved, into `~/.local/opt/appimages/<app-id>/`. Keeping the original until the user verifies the launcher is safer. To move it instead:

```bash
appimage-integrator install ~/Downloads/MyApp.AppImage --move
```

Preview changes without writing anything:

```bash
appimage-integrator install ~/Downloads/MyApp.AppImage --dry-run
```

Set a display name or provide a trusted icon:

```bash
appimage-integrator install ~/Downloads/MyApp.AppImage \
  --name "My App" --icon ~/Pictures/my-app.png
```

Manage integrations:

```bash
appimage-integrator list
appimage-integrator show my-app
appimage-integrator uninstall my-app
```

Uninstall removes only files recorded in the tool's manifest. It keeps the managed AppImage unless `--remove-appimage` is explicitly provided.

## Files and locations

| Purpose | Location |
| --- | --- |
| Managed applications | `~/.local/opt/appimages/<id>/` |
| Desktop launchers | `~/.local/share/applications/` |
| Managed icons | `~/.local/share/icons/hicolor/` |
| Integration manifests | `~/.local/share/appimage-integrator/` |

The tool creates a manifest for each integration. Do not edit these manifests manually while an operation is in progress.

## Security model

- Never invokes the installed application during normal installation.
- Does not request administrator privileges.
- Copies by default; moving is an explicit option.
- Does not overwrite an existing managed destination without `--force`.
- Uses a manifest to restrict uninstall cleanup to files owned by this tool.
- Treats names and paths as untrusted input and escapes Desktop Entry values.
- Does not download, update, or execute arbitrary remote content.

An optional icon must be a local PNG, SVG, or XPM file. AppImage-internal icon extraction is not automatic because `--appimage-extract` executes the target AppImage's runtime and is not supported by every AppImage generation. If you choose to inspect an untrusted AppImage, do so in a sandbox.

## Development

```bash
python -m unittest discover -s tests -v
```

The tests use temporary directories and inert fixture files; they do not execute AppImages or require a graphical session.

CI runs the unit test suite on supported Python versions. Contributions should include tests for behavior changes; see [CONTRIBUTING.md](CONTRIBUTING.md).

## Roadmap

- [x] Optional basic Tkinter GUI
- [ ] File-manager context-menu integration
- [ ] Desktop-file and icon discovery through safe, external tooling
- [ ] Update workflows that respect upstream AppImage update metadata
- [x] End-to-end lifecycle tests for install, dry-run, duplicate detection, rollback, and uninstall path validation
- [ ] More distribution/desktop-environment integration tests
- [x] Automated wheel/source artifact build workflow (not yet signed)
- [ ] Signed releases and reproducible release artifacts

## License

MIT. See [LICENSE](LICENSE).

This is an independent community project and is not affiliated with Apple or the AppImage project.
