class Console:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self.console = None
        self.accent = "#cfecf7"
        self.logo_colors = ("#cfecf7", "#cfecf7")
        if enabled:
            try:
                from rich.console import Console as RichConsole
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
                    "accent": self.accent,
                }
            )
            self.console = RichConsole(theme=theme)

    def color_mix(self, start_hex: str, end_hex: str, ratio: float) -> str:
        start_hex = start_hex.lstrip("#")
        end_hex = end_hex.lstrip("#")
        start = [int(start_hex[i : i + 2], 16) for i in (0, 2, 4)]
        end = [int(end_hex[i : i + 2], 16) for i in (0, 2, 4)]
        red = int(start[0] + (end[0] - start[0]) * ratio)
        green = int(start[1] + (end[1] - start[1]) * ratio)
        blue = int(start[2] + (end[2] - start[2]) * ratio)
        return f"#{red:02x}{green:02x}{blue:02x}"

    def logo_make(self, width: int) -> object:
        try:
            from rich_pyfiglet import RichFiglet

            return RichFiglet(
                "DEVO",
                font="ansi_shadow",
                colors=list(self.logo_colors),
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

        rows = [
            " _____  _____  _   _  _____ ",
            "|  __ \\|  ___|| | | ||  _  |",
            "| |  \\/| |__  | | | || | | |",
            "| | __ |  __| | | | || | | |",
            "| |_\\ \\| |___ \\ \\_/ /\\ \\_/ /",
            " \\____/\\____/  \\___/  \\___/ ",
        ]
        row_len = max(len(line) for line in rows)
        start, end = self.logo_colors
        text = Text()
        for line in rows:
            for index, char in enumerate(line.ljust(row_len)):
                if char == " ":
                    text.append(char)
                    continue
                color = self.color_mix(start, end, index / max(1, row_len - 1))
                text.append(char, style=color)
            text.append("\n")
        return text

    def banner(self, provider: str, model: str, workspace: object, safety_mode: str) -> None:
        if not self.enabled or not self.console:
            return
        try:
            from rich.align import Align
            from rich.panel import Panel
            from rich.table import Table
            from rich.text import Text
        except Exception:
            return

        width = self.console.size.width
        gap = 2
        box = max(32, int((width - gap) / 2))
        art = self.logo_make(box)
        info = Text(
            f"MODEL: {model}\nPROVIDER: {provider}\nWORKSPACE: {workspace.default_name}"
        )

        logo_height = art.height if hasattr(art, "height") else len(str(art).splitlines())
        body_pad = 1
        info_height = len(info.plain.splitlines()) + body_pad + body_pad
        logo_total = logo_height + body_pad + body_pad
        extra = max(0, logo_total - info_height)
        pad_top = body_pad + (extra // 2)
        pad_bottom = body_pad + (extra - (extra // 2))

        table = Table.grid(expand=True)
        table.add_column(width=box)
        table.add_column(width=box)
        logo_panel = Panel(art, border_style="accent", padding=(1, 1), width=box)
        info_panel = Panel(
            Align.left(info),
            border_style="accent",
            padding=(pad_top, 2, pad_bottom, 2),
            width=box,
        )
        table.add_row(logo_panel, info_panel)
        self.console.print(table)

    def prompt(self) -> str:
        if self.enabled and self.console:
            return self.console.input(f"[{self.accent}]devo[/] ")
        return input("devo ")

    def print_info(self, message: str) -> None:
        if self.enabled and self.console:
            self.console.print(message, style="info")
            return
        print(message)

    def print_error(self, message: str) -> None:
        if self.enabled and self.console:
            self.console.print(message, style="error")
            return
        print(message)

    def print_output(self, output: str) -> None:
        if self.enabled and self.console:
            self.console.print(output)
            return
        print(output)


ConsoleUI = Console
