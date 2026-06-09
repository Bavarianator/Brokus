"""Book opener – OS-agnostic file/editor/folder opening."""

import subprocess
import platform
import os
from shutil import which


class BookOpener:
    """Opens files, editors, and folders in an OS-agnostic way."""

    @staticmethod
    def open_file(filepath: str):
        """Open a file with the system's default application."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Datei nicht gefunden: {filepath}")

        system = platform.system()
        if system == "Darwin":
            subprocess.run(["open", filepath])
        elif system == "Windows":
            os.startfile(filepath)
        else:  # Linux and others
            subprocess.run(["xdg-open", filepath])

    @staticmethod
    def open_in_editor(filepath: str, editor: str | None = None):
        """Open a file in a terminal editor.

        Args:
            filepath: Path to the file.
            editor: Editor command (e.g., 'nano', 'vim', 'code').
                    Uses $EDITOR or 'nano' by default.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Datei nicht gefunden: {filepath}")

        editor = editor or os.environ.get("EDITOR", "nano")
        subprocess.run([editor, filepath])

    @staticmethod
    def open_folder(filepath: str):
        """Open the folder containing a file."""
        folder = os.path.dirname(os.path.abspath(filepath))
        if os.path.isdir(folder):
            BookOpener.open_file(folder)
        else:
            raise FileNotFoundError(f"Ordner nicht gefunden: {folder}")

    @staticmethod
    def open_with_app(filepath: str, app: str):
        """Open a file with a specific application.

        Args:
            filepath: Path to the file.
            app: Application command (e.g., 'code', 'typora', 'calibre').
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Datei nicht gefunden: {filepath}")

        subprocess.Popen([app, filepath])

    # Known editors
    EDITORS = {
        "vscode": ["code", "{file}"],
        "nano": ["nano", "{file}"],
        "vim": ["vim", "{file}"],
        "neovim": ["nvim", "{file}"],
        "notepadpp": ["notepad++", "{file}"],
        "typora": ["typora", "{file}"],
        "sublime": ["subl", "{file}"],
    }

    @classmethod
    def get_available_editors(cls) -> list[tuple[str, str]]:
        """Get list of (display_name, editor_key) for available editors."""
        available = []
        for key, cmd in cls.EDITORS.items():
            # Check if the editor is installed
            if which(cmd[0]):
                available.append((cmd[0].title(), key))
        # Always include nano as fallback
        if not any(k == "nano" for _, k in available):
            available.insert(0, ("Nano", "nano"))
        return available
