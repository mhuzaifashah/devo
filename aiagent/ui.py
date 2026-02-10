class ConsoleUI:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self._console = None
        self._accent = "#cfecf7"
        self._logo_colors = ("#cfecf7", "#cfecf7")
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
                    "accent": self._accent,
                }
            )
            self._console = Console(theme=theme)

    def _lerp_color(self, start_hex, end_hex, t):
        start_hex = start_hex.lstrip("#")
        end_hex = end_hex.lstrip("#")
        sr, sg, sb = [int(start_hex[i : i + 2], 16) for i in (0, 2, 4)]
        er, eg, eb = [int(end_hex[i : i + 2], 16) for i in (0, 2, 4)]
        r = int(sr + (er - sr) * t)
        g = int(sg + (eg - sg) * t)
        b = int(sb + (eb - sb) * t)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _build_logo(self, width):
        try:
            from rich_pyfiglet import RichFiglet

            return RichFiglet(
                "DEVO",
                font="ansi_shadow",
                colors=list(self._logo_colors),
                horizontal=True,
                width=width,
                remove_blank_lines=True,
            )
        except Exception:
            pass
        try:
            from rich.text import Text
        except Exception:
            return "DEVO"

        art_lines = [
            " _____  _____  _   _  _____ ",
            "|  __ \\|  ___|| | | ||  _  |",
            "| |  \\/| |__  | | | || | | |",
            "| | __ |  __| | | | || | | |",
            "| |_\\ \\| |___ \\ \\_/ /\\ \\_/ /",
            " \\____/\\____/  \\___/  \\___/ ",
        ]
        max_len = max(len(line) for line in art_lines)
        start, end = self._logo_colors
        text = Text()
        for line in art_lines:
            padded = line.ljust(max_len)
            for idx, ch in enumerate(padded):
                if ch == " ":
                    text.append(ch)
                    continue
                color = self._lerp_color(start, end, idx / max(1, max_len - 1))
                text.append(ch, style=color)
            text.append("\n")
        return text

    def banner(self, provider, model, workspace_manager, safety_mode):
        if not self.enabled or not self._console:
            return
        try:
            from rich.panel import Panel
            from rich.table import Table
            from rich.align import Align
            from rich.text import Text
        except Exception:
            return

        console_width = self._console.size.width if self._console else 80
        total_gap = 2
        box_width = max(32, int((console_width - total_gap) / 2))
        art = self._build_logo(box_width)
        info = Text(
            f"MODEL: {model}\nPROVIDER: {provider}\nWORKSPACE: {workspace_manager.default_name}"
        )

        logo_height = art.height if hasattr(art, "height") else len(str(art).splitlines())
        top_pad = 1
        bottom_pad = 1
        info_lines = info.plain.splitlines()
        info_height = len(info_lines) + top_pad + bottom_pad
        logo_total = logo_height + top_pad + bottom_pad
        if info_height < logo_total:
            extra = logo_total - info_height
            extra_top = extra // 2
            extra_bottom = extra - extra_top
        else:
            extra_top = 0
            extra_bottom = 0

        info_pad_top = top_pad + extra_top
        info_pad_bottom = bottom_pad + extra_bottom

        table = Table.grid(expand=True)
        table.add_column(width=box_width)
        table.add_column(width=box_width)
        logo_panel = Panel(art, border_style="accent", padding=(1, 1), width=box_width)
        info_panel = Panel(
            Align.left(info),
            border_style="accent",
            padding=(info_pad_top, 2, info_pad_bottom, 2),
            width=box_width,
        )
        table.add_row(logo_panel, info_panel)
        self._console.print(table)

    def prompt(self):
        if self.enabled and self._console:
            return self._console.input(f"[{self._accent}]devo[/] ")
        return input("devo ")

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
