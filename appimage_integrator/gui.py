"""Optional Tkinter interface; install tkinter from your distribution if absent."""
from __future__ import annotations

import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("AppImage Integrator")
        root.geometry("660x420")
        root.minsize(560, 360)
        frame = ttk.Frame(root, padding=18)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="AppImage Integrator", font=("", 18, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Integra aplicaciones en tu escritorio sin permisos de administrador.").pack(anchor="w", pady=(2, 16))

        self.appimage = tk.StringVar()
        self.name = tk.StringVar()
        self.icon = tk.StringVar()
        self.move = tk.BooleanVar(value=False)

        self._file_row(frame, "AppImage", self.appimage, self.pick_appimage, 0)
        self._entry_row(frame, "Nombre visible", self.name, 1)
        self._file_row(frame, "Icono opcional", self.icon, self.pick_icon, 2)
        ttk.Checkbutton(frame, text="Mover el archivo original (por defecto se copia)", variable=self.move).grid(row=3, column=1, sticky="w", pady=8)
        actions = ttk.Frame(frame)
        actions.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(10, 6))
        ttk.Button(actions, text="Instalar", command=self.install).pack(side="left")
        ttk.Button(actions, text="Ver integraciones", command=self.list_apps).pack(side="left", padx=8)
        ttk.Button(actions, text="Desinstalar por ID…", command=self.uninstall).pack(side="left")
        self.output = tk.Text(frame, height=7, wrap="word", state="disabled")
        self.output.grid(row=5, column=0, columnspan=3, sticky="nsew", pady=(8, 0))
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(5, weight=1)

    def _file_row(self, parent: ttk.Frame, label: str, var: tk.StringVar, command, row: int) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, sticky="ew", padx=8, pady=5)
        ttk.Button(parent, text="Examinar…", command=command).grid(row=row, column=2, pady=5)

    def _entry_row(self, parent: ttk.Frame, label: str, var: tk.StringVar, row: int) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=5)
        ttk.Entry(parent, textvariable=var).grid(row=row, column=1, columnspan=2, sticky="ew", padx=8, pady=5)

    def pick_appimage(self) -> None:
        path = filedialog.askopenfilename(title="Selecciona una AppImage", filetypes=[("AppImage", "*.AppImage *.appimage"), ("Todos los archivos", "*")])
        if path:
            self.appimage.set(path)
            if not self.name.get():
                from pathlib import Path
                self.name.set(Path(path).stem)

    def pick_icon(self) -> None:
        path = filedialog.askopenfilename(title="Selecciona un icono", filetypes=[("Iconos", "*.png *.svg *.xpm"), ("Todos los archivos", "*")])
        if path:
            self.icon.set(path)

    def run_cli(self, args: list[str]) -> None:
        try:
            result = subprocess.run([sys.executable, "-m", "appimage_integrator", *args], capture_output=True, text=True, timeout=180)
            output = (result.stdout + result.stderr).strip() or f"El comando terminó con código {result.returncode}."
            self.output.configure(state="normal")
            self.output.delete("1.0", "end")
            self.output.insert("1.0", output)
            self.output.configure(state="disabled")
            if result.returncode:
                messagebox.showerror("Operación no completada", output)
            else:
                messagebox.showinfo("AppImage Integrator", output)
        except (OSError, subprocess.TimeoutExpired) as exc:
            messagebox.showerror("Error", str(exc))

    def install(self) -> None:
        if not self.appimage.get().strip():
            messagebox.showwarning("Falta la AppImage", "Selecciona primero un archivo AppImage.")
            return
        args = ["install", self.appimage.get().strip()]
        if self.name.get().strip():
            args += ["--name", self.name.get().strip()]
        if self.icon.get().strip():
            args += ["--icon", self.icon.get().strip()]
        if self.move.get():
            args.append("--move")
        if not messagebox.askyesno("Confirmar instalación", "Se creará un lanzador de escritorio. ¿Continuar?"):
            return
        self.run_cli(args)

    def list_apps(self) -> None:
        self.run_cli(["list"])

    def uninstall(self) -> None:
        app_id = simpledialog.askstring("Desinstalar", "ID de la integración (consulta «Ver integraciones»):")
        if app_id and messagebox.askyesno("Confirmar", f"¿Eliminar el lanzador de «{app_id}»? La AppImage se conservará."):
            self.run_cli(["uninstall", app_id])


def main() -> int:
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        print(f"No se pudo iniciar la interfaz gráfica: {exc}", file=sys.stderr)
        return 1
    App(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
