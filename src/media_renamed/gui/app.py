import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk

from ..api.tmdb import TMDBClient
from ..core.models import (
    MediaType,
    RenameConfig,
    RenameOperation,
    TitleLanguage,
)
from ..core.renamer import rename_media
from ..core.scanner import MediaScanner


class PreviewWindow(Adw.Window):
    def __init__(self, parent, operations, on_confirm):
        super().__init__(
            transient_for=parent,
            modal=True,
            title="Prévia das renomeações",
            default_width=900,
            default_height=600,
        )

        self.operations = operations
        self.on_confirm = on_confirm

        header = Adw.HeaderBar()

        cancel_button = Gtk.Button(label="Cancelar")
        cancel_button.connect(
            "clicked",
            lambda _: self.close(),
        )

        confirm_button = Gtk.Button(label="Renomear")
        confirm_button.add_css_class("suggested-action")
        confirm_button.connect(
            "clicked",
            self.on_confirm_clicked,
        )

        header.pack_start(cancel_button)
        header.pack_end(confirm_button)

        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=12,
        )
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)

        ready = sum(
            operation.status == "ready"
            for operation in operations
        )

        blocked = sum(
            operation.status != "ready"
            for operation in operations
        )

        summary = Gtk.Label(
            label=(
                f"{ready} arquivo(s) pronto(s) para renomear"
                f" • {blocked} item(ns) com problema"
            )
        )
        summary.set_halign(Gtk.Align.START)

        text_view = Gtk.TextView()
        text_view.set_editable(False)
        text_view.set_cursor_visible(False)
        text_view.set_monospace(True)
        text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)

        lines = []

        for operation in operations:
            if operation.status == "ready":
                line = (
                    f"✓ {operation.source.name}\n"
                    f"  → {operation.destination.name}"
                )

                if operation.subtitle_source:
                    line += (
                        f"\n  ↳ {operation.subtitle_source.name}"
                        f" → "
                        f"{operation.subtitle_destination.name}"
                    )

            elif operation.status == "unchanged":
                line = (
                    f"= {operation.source.name}\n"
                    f"  {operation.message}"
                )

            else:
                line = (
                    f"! {operation.source.name}\n"
                    f"  {operation.message}"
                )

            lines.append(line)

        text_view.get_buffer().set_text(
            "\n\n".join(lines)
        )

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_child(text_view)

        content.append(summary)
        content.append(scroll)

        root = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL
        )
        root.append(header)
        root.append(content)

        self.set_content(root)

        if ready == 0:
            confirm_button.set_sensitive(False)

    def on_confirm_clicked(self, button):
        self.on_confirm(self.operations)
        self.close()


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, application):
        super().__init__(
            application=application,
            title="Media Renamed",
            default_width=700,
            default_height=620,
        )

        self.selected_folder: Path | None = None
        self.operations: list[RenameOperation] = []
        self.scanning = False

        self.config = RenameConfig(
            media_type=MediaType.AUTO,
            language=TitleLanguage.AUTO,
        )

        self.build_ui()

    def build_ui(self):
        header = Adw.HeaderBar()

        title = Adw.WindowTitle(
            title="Media Renamed",
            subtitle="Renomeador de arquivos de mídia",
        )

        header.set_title_widget(title)

        folder_group = Adw.PreferencesGroup(
            title="Pasta"
        )

        self.folder_row = Adw.ActionRow(
            title="Diretório de trabalho",
            subtitle="Nenhuma pasta selecionada",
        )

        folder_button = Gtk.Button(
            label="Selecionar pasta"
        )
        folder_button.set_valign(Gtk.Align.CENTER)
        folder_button.add_css_class("suggested-action")
        folder_button.connect(
            "clicked",
            self.on_select_folder,
        )

        self.folder_row.add_suffix(folder_button)
        folder_group.add(self.folder_row)

        media_group = Adw.PreferencesGroup(
            title="Configuração"
        )

        media_model = Gtk.StringList.new([
            "Automático",
            "Séries",
            "Filmes / Documentários",
            "Música",
        ])

        self.media_dropdown = Gtk.DropDown(
            model=media_model
        )
        self.media_dropdown.set_selected(0)
        self.media_dropdown.connect(
            "notify::selected",
            self.on_media_changed,
        )

        media_row = Adw.ActionRow(
            title="Tipo de mídia",
            subtitle="Define como os arquivos serão interpretados",
        )
        media_row.add_suffix(self.media_dropdown)

        language_model = Gtk.StringList.new([
            "Automático",
            "Português (Brasil)",
            "Original",
        ])

        self.language_dropdown = Gtk.DropDown(
            model=language_model
        )
        self.language_dropdown.set_selected(0)
        self.language_dropdown.connect(
            "notify::selected",
            self.on_language_changed,
        )

        language_row = Adw.ActionRow(
            title="Idioma dos títulos",
            subtitle="Idioma usado nos nomes obtidos do TMDB",
        )
        language_row.add_suffix(self.language_dropdown)

        self.hidden_switch = Gtk.Switch()
        self.hidden_switch.set_valign(Gtk.Align.CENTER)
        self.hidden_switch.connect(
            "notify::active",
            self.on_hidden_changed,
        )

        hidden_row = Adw.ActionRow(
            title="Incluir arquivos ocultos",
            subtitle="Também analisar arquivos cujo nome começa com '.'",
        )
        hidden_row.add_suffix(self.hidden_switch)

        media_group.add(media_row)
        media_group.add(language_row)
        media_group.add(hidden_row)

        action_group = Adw.PreferencesGroup(
            title="Ações"
        )

        self.analyze_button = Gtk.Button(
            label="Analisar pasta"
        )
        self.analyze_button.add_css_class(
            "suggested-action"
        )
        self.analyze_button.connect(
            "clicked",
            self.on_analyze,
        )

        self.rename_button = Gtk.Button(
            label="Renomear arquivos"
        )
        self.rename_button.set_sensitive(False)
        self.rename_button.connect(
            "clicked",
            self.on_rename,
        )

        action_group.add(self.analyze_button)
        action_group.add(self.rename_button)

        status_group = Adw.PreferencesGroup(
            title="Status"
        )

        self.status_row = Adw.ActionRow(
            title="Estado",
            subtitle="Selecione uma pasta para começar.",
        )

        status_group.add(self.status_row)

        content = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=18,
        )

        content.set_margin_top(18)
        content.set_margin_bottom(18)
        content.set_margin_start(18)
        content.set_margin_end(18)

        content.append(folder_group)
        content.append(media_group)
        content.append(action_group)
        content.append(status_group)

        toolbar_view = Adw.ToolbarView()
        toolbar_view.add_top_bar(header)
        toolbar_view.set_content(content)

        self.set_content(toolbar_view)

    def on_select_folder(self, button):
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Selecionar pasta")

        dialog.select_folder(
            self,
            None,
            self.on_folder_selected,
        )

    def on_folder_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
        except GLib.Error as error:
            self.set_status(
                f"Seleção cancelada ou indisponível: {error}"
            )
            return

        if folder is None:
            return

        path = folder.get_path()

        if not path:
            return

        self.selected_folder = Path(path)

        self.folder_row.set_subtitle(path)

        self.set_status(
            "Pasta selecionada. Pronto para analisar."
        )

        self.rename_button.set_sensitive(False)
        self.operations = []

    def on_media_changed(self, dropdown, param):
        options = [
            MediaType.AUTO,
            MediaType.TV,
            MediaType.MOVIE,
            MediaType.MUSIC,
        ]

        self.config.media_type = options[
            dropdown.get_selected()
        ]

    def on_language_changed(self, dropdown, param):
        options = [
            TitleLanguage.AUTO,
            TitleLanguage.PT_BR,
            TitleLanguage.ORIGINAL,
        ]

        self.config.language = options[
            dropdown.get_selected()
        ]

    def on_hidden_changed(self, switch, param):
        self.config.show_hidden = switch.get_active()

    def on_analyze(self, button):
        if not self.selected_folder:
            self.show_alert(
                "Nenhuma pasta selecionada",
                "Selecione uma pasta antes de iniciar a análise.",
            )
            return

        self.scanning = True
        self.analyze_button.set_sensitive(False)
        self.rename_button.set_sensitive(False)

        self.set_status(
            "Analisando arquivos e consultando o TMDB..."
        )

        folder = self.selected_folder
        config = self.config

        thread = threading.Thread(
            target=self._scan_worker,
            args=(folder, config),
            daemon=True,
        )

        thread.start()

    def _scan_worker(self, folder, config):
        try:
            client = TMDBClient()
            scanner = MediaScanner(client)

            operations = scanner.scan(
                folder,
                config,
            )

            GLib.idle_add(
                self._scan_finished,
                operations,
                None,
            )

        except Exception as error:
            GLib.idle_add(
                self._scan_finished,
                None,
                error,
            )

    def _scan_finished(self, operations, error):
        self.scanning = False
        self.analyze_button.set_sensitive(True)

        if error:
            self.set_status("Erro durante a análise.")

            self.show_alert(
                "Erro na análise",
                str(error),
            )

            return False

        self.operations = operations

        ready = sum(
            operation.status == "ready"
            for operation in operations
        )

        blocked = sum(
            operation.status != "ready"
            for operation in operations
        )

        self.rename_button.set_sensitive(
            ready > 0
        )

        self.set_status(
            f"Análise concluída: "
            f"{ready} pronto(s), "
            f"{blocked} com problema."
        )

        preview = PreviewWindow(
            self,
            operations,
            self.confirm_rename,
        )

        preview.present()

        return False

    def on_rename(self, button):
        if not self.operations:
            return

        preview = PreviewWindow(
            self,
            self.operations,
            self.confirm_rename,
        )

        preview.present()

    def confirm_rename(self, operations):
        ready_operations = [
            operation
            for operation in operations
            if operation.status == "ready"
        ]

        success = 0
        errors = []

        for operation in ready_operations:
            try:
                rename_media(
                    operation.source,
                    operation.destination,
                    operation.subtitle_source,
                )
                success += 1

            except Exception as error:
                errors.append(
                    f"{operation.source.name}: {error}"
                )

        if errors:
            message = (
                f"{success} arquivo(s) renomeado(s).\n\n"
                f"Falhas:\n"
                + "\n".join(errors)
            )
        else:
            message = (
                f"{success} arquivo(s) renomeado(s) "
                "com sucesso."
            )

        self.set_status(message)
        self.rename_button.set_sensitive(False)
        self.operations = []

        self.show_alert(
            "Operação concluída",
            message,
        )

    def set_status(self, message):
        self.status_row.set_subtitle(message)

    def show_alert(self, title, message):
        dialog = Gtk.AlertDialog()
        dialog.set_message(title)
        dialog.set_detail(message)
        dialog.show(self)


class MediaRenamedApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="io.github.media_renamed"
        )

    def do_activate(self):
        window = self.props.active_window

        if window is None:
            window = MainWindow(self)

        window.present()
