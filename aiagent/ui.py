class ConsoleUI:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self._console = None
        if enabled:
            try:
                from rich.console import Console
                from rich.theme import Theme
            except Exception:
                self.enabled = False
                return
            theme = Theme(
                {
                    "info": "cyan",
                    "warning": "yellow",
                    "error": "red",
                    "ok": "green",
                }
            )
            self._console = Console(theme=theme)

    def banner(self, provider, model, workspaces, safety_mode):
        if not self.enabled or not self._console:
            return
        try:
            from rich.panel import Panel
            from rich.table import Table
        except Exception:
            return

        table = Table(show_header=False, box=None)
        table.add_row("Provider", provider)
        table.add_row("Model", model)
        table.add_row("Safety", safety_mode)
        table.add_row(
            "Workspaces",
            ", ".join([f"{name}:{path}" for name, path in workspaces]) or "none",
        )
        self._console.print(Panel(table, title="AI Agent", border_style="info"))

    def print_info(self, message):
        if self.enabled and self._console:
            self._console.print(message, style="info")
        else:
            print(message)

    def print_error(self, message):
        if self.enabled and self._console:
            self._console.print(message, style="error")
        else:
            print(message)

    def print_output(self, output):
        if self.enabled and self._console:
            self._console.print(output)
        else:
            print(output)
