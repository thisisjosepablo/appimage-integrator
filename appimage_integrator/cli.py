"""CLI for reversible, user-level AppImage integration."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

APP_ROOT = Path.home() / ".local/opt/appimages"
DESKTOP_ROOT = Path.home() / ".local/share/applications"
ICON_ROOT = Path.home() / ".local/share/icons/hicolor"
MANIFEST_ROOT = Path.home() / ".local/share/appimage-integrator"
ICON_SUFFIXES = {".png": ("256x256", ".png"), ".svg": ("scalable", ".svg"), ".xpm": ("48x48", ".xpm")}


class IntegrationError(Exception):
    """Expected user-facing operation failure."""


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9._+-]+", "-", value.strip().lower())
    value = re.sub(r"-{2,}", "-", value).strip("-.")
    return value or "appimage-app"


def desktop_escape(value: str) -> str:
    """Escape a value for a Desktop Entry key (not an Exec argument)."""
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "").replace("\t", "\\t")


def exec_quote(path: Path) -> str:
    """Quote a single executable path according to Desktop Entry Exec rules."""
    raw = str(path)
    raw = raw.replace("\\", "\\\\").replace('"', '\\"').replace("`", "\\`").replace("$", "\\$")
    return f'"{raw}"'


def user_paths() -> tuple[Path, Path, Path, Path]:
    return APP_ROOT, DESKTOP_ROOT, ICON_ROOT, MANIFEST_ROOT


def load_manifest(app_id: str) -> dict[str, Any]:
    path = MANIFEST_ROOT / f"{app_id}.json"
    if not path.is_file():
        raise IntegrationError(f"No existe una integración administrada con ID «{app_id}».")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise IntegrationError(f"El manifiesto está dañado: {path}") from exc
    if data.get("id") != app_id:
        raise IntegrationError("El identificador del manifiesto no coincide; se cancela por seguridad.")
    return data


def save_json_atomic(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def install(args: argparse.Namespace) -> int:
    input_path = Path(args.appimage).expanduser()
    if input_path.is_symlink():
        raise IntegrationError("Usa la ruta al archivo real, no un enlace simbólico.")
    source = input_path.resolve()
    if not source.is_file():
        raise IntegrationError(f"No existe el archivo: {source}")
    if not os.access(source, os.R_OK):
        raise IntegrationError(f"No se puede leer el archivo: {source}")
    name = args.name.strip() if args.name else source.stem
    if not name or any(ch in name for ch in "\r\n\0"):
        raise IntegrationError("El nombre visible no puede estar vacío ni contener saltos de línea.")
    app_id = slugify(args.id or name)
    app_home = APP_ROOT / app_id
    final_image = app_home / source.name
    desktop = DESKTOP_ROOT / f"{app_id}.desktop"
    manifest_path = MANIFEST_ROOT / f"{app_id}.json"
    icon_source = Path(args.icon).expanduser().resolve() if args.icon else None
    icon_target: Path | None = None

    if icon_source:
        if not icon_source.is_file() or icon_source.suffix.lower() not in ICON_SUFFIXES:
            raise IntegrationError("--icon debe ser un archivo PNG, SVG o XPM existente.")
        if not os.access(icon_source, os.R_OK):
            raise IntegrationError("No se puede leer el icono indicado.")

    existing = manifest_path.exists() or desktop.exists() or app_home.exists()
    if existing and not args.force:
        raise IntegrationError(f"Ya existe una integración o destino para «{app_id}». Desinstala la integración existente antes de instalarla de nuevo.")

    if args.dry_run:
        print("Plan (sin cambios):")
        print(f"  Origen: {source}")
        print(f"  Destino: {final_image} ({'mover' if args.move else 'copiar'})")
        print(f"  Lanzador: {desktop}")
        print(f"  Icono: {icon_source or 'icono genérico del tema'}")
        print(f"  Manifiesto: {manifest_path}")
        return 0

    APP_ROOT.mkdir(parents=True, exist_ok=True)
    DESKTOP_ROOT.mkdir(parents=True, exist_ok=True)
    MANIFEST_ROOT.mkdir(parents=True, exist_ok=True)
    app_home.mkdir(parents=True, exist_ok=False)
    moved_source = False
    icon_created = False
    desktop_created = False
    manifest_created = False
    try:
        if args.move:
            if source == final_image:
                pass
            else:
                shutil.move(str(source), str(final_image))
                moved_source = True
        else:
            shutil.copy2(source, final_image)
        final_image.chmod(final_image.stat().st_mode | 0o111)

        icon_name = app_id
        if icon_source:
            bucket, suffix = ICON_SUFFIXES[icon_source.suffix.lower()]
            app_folder = ICON_ROOT / bucket / "apps"
            app_folder.mkdir(parents=True, exist_ok=True)
            icon_target = app_folder / f"{app_id}{suffix}"
            if icon_target.exists():
                raise IntegrationError(f"El icono de destino ya existe: {icon_target}")
            shutil.copy2(icon_source, icon_target)
            icon_created = True

        desktop_text = "\n".join([
            "[Desktop Entry]",
            "Version=1.0",
            "Type=Application",
            f"Name={desktop_escape(name)}",
            f"Exec={exec_quote(final_image)} %U",
            f"TryExec={exec_quote(final_image)}",
            f"Icon={icon_name}",
            "Terminal=false",
            "Categories=Utility;",
            "StartupNotify=true",
            "",
        ])
        # Exclusive create prevents overwriting a launcher not owned by this tool.
        with desktop.open("x", encoding="utf-8") as handle:
            desktop_created = True
            handle.write(desktop_text)
        desktop.chmod(0o644)
        manifest = {
            "schema_version": 1,
            "id": app_id,
            "name": name,
            "appimage": str(final_image),
            "desktop_file": str(desktop),
            "icon_file": str(icon_target) if icon_target else None,
            "source": str(source),
            "moved_source": moved_source,
        }
        save_json_atomic(manifest_path, manifest)
        manifest_created = True
    except Exception:
        for path, created in ((desktop, desktop_created), (icon_target, icon_created), (manifest_path, manifest_created)):
            if path and created:
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
        if final_image.exists():
            try:
                if moved_source and not source.exists():
                    source.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(final_image), str(source))
                else:
                    final_image.unlink()
            except OSError:
                print(f"Aviso: no se pudo restaurar automáticamente {final_image}", file=sys.stderr)
        try:
            app_home.rmdir()
        except OSError:
            pass
        raise

    print(f"Integración creada: {desktop}")
    print(f"AppImage: {final_image}")
    print("No se ha ejecutado la aplicación.")
    return 0


def list_apps(_: argparse.Namespace) -> int:
    if not MANIFEST_ROOT.exists():
        print("No hay integraciones administradas.")
        return 0
    count = 0
    for path in sorted(MANIFEST_ROOT.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            print(f"{data.get('id', path.stem)}\t{data.get('name', '(sin nombre)')}\t{data.get('appimage', '')}")
            count += 1
        except (OSError, json.JSONDecodeError):
            print(f"AVISO: manifiesto ilegible: {path}", file=sys.stderr)
    if not count:
        print("No hay integraciones administradas.")
    return 0


def show_app(args: argparse.Namespace) -> int:
    data = load_manifest(slugify(args.id))
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


def uninstall(args: argparse.Namespace) -> int:
    app_id = slugify(args.id)
    data = load_manifest(app_id)
    managed_root = (APP_ROOT / app_id).resolve()
    # Compare lexical absolute paths: resolve() follows replaced symlinks.
    desktop = Path(data.get("desktop_file", "")).expanduser().absolute()
    appimage_path = Path(data.get("appimage", "")).expanduser().absolute()
    app_home = appimage_path.parent
    if desktop != (DESKTOP_ROOT / f"{app_id}.desktop").absolute():
        raise IntegrationError("El manifiesto apunta a un lanzador fuera de la ruta administrada; se cancela.")
    if app_home != (APP_ROOT / app_id).absolute() or appimage_path.name in ("", ".", ".."):
        raise IntegrationError("El manifiesto apunta a una AppImage fuera de su carpeta administrada; se cancela.")
    icon_value = data.get("icon_file")
    icon = Path(icon_value).expanduser().absolute() if icon_value else None
    if icon and ICON_ROOT.absolute() not in icon.parents:
        raise IntegrationError("El manifiesto apunta a un icono fuera de la carpeta administrada; se cancela.")
    if args.dry_run:
        print(f"Se eliminaría el lanzador: {desktop}")
        if icon:
            print(f"Se eliminaría el icono: {icon}")
        if args.remove_appimage:
            print(f"Se eliminaría la AppImage administrada: {app_home}")
        print(f"Se eliminaría el manifiesto: {MANIFEST_ROOT / (app_id + '.json')}")
        return 0

    desktop.unlink(missing_ok=True)
    if icon:
        icon.unlink(missing_ok=True)
    if args.remove_appimage:
        shutil.rmtree(app_home, ignore_errors=False)
    (MANIFEST_ROOT / f"{app_id}.json").unlink(missing_ok=True)
    print(f"Integración eliminada: {app_id}")
    if not args.remove_appimage and app_home.exists():
        print(f"La AppImage se conserva en: {app_home}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="appimage-integrator",
        description="Integra y administra AppImages en el escritorio de tu usuario, sin sudo.")
    parser.add_argument("--version", action="version", version="appimage-integrator 0.2.0")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("install", help="integrar una AppImage")
    p.add_argument("appimage", help="ruta a la AppImage")
    p.add_argument("--name", help="nombre mostrado en el menú")
    p.add_argument("--id", help="identificador estable (por defecto se deriva del nombre)")
    p.add_argument("--icon", help="icono local PNG, SVG o XPM; no se extrae ni ejecuta la AppImage")
    p.add_argument("--move", action="store_true", help="mover en vez de copiar (por defecto copia)")
    p.add_argument("--dry-run", action="store_true", help="mostrar el plan sin cambiar archivos")
    p.set_defaults(func=install)
    p = sub.add_parser("list", help="listar integraciones administradas")
    p.set_defaults(func=list_apps)
    p = sub.add_parser("show", help="mostrar el manifiesto de una integración")
    p.add_argument("id")
    p.set_defaults(func=show_app)
    p = sub.add_parser("uninstall", help="quitar una integración")
    p.add_argument("id")
    p.add_argument("--remove-appimage", action="store_true", help="eliminar también la AppImage administrada")
    p.add_argument("--dry-run", action="store_true", help="mostrar lo que se eliminaría")
    p.set_defaults(func=uninstall)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        return args.func(args)
    except IntegrationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"Error del sistema: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
