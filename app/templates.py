from datetime import datetime, timezone

from fastapi.templating import Jinja2Templates
from markdown_it import MarkdownIt
from markupsafe import Markup

templates = Jinja2Templates(directory="templates")

# HTML cru fica desativado: tudo que o usuário digitar como tag é escapado.
# O markdown-it também recusa links javascript:, vbscript:, file: e data:.
_markdown = (
    MarkdownIt("commonmark", {"html": False, "breaks": True, "typographer": False})
    .enable("table")
    .enable("strikethrough")
)


def render_markdown(text: str | None) -> Markup:
    if not text:
        return Markup("")
    return Markup(_markdown.render(text))


def time_ago(value: datetime | None) -> str:
    """Formata datas como "há 5 min", "há 2 dias" etc."""
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    seconds = int((datetime.now(timezone.utc) - value).total_seconds())
    if seconds < 60:
        return "agora mesmo"
    minutes = seconds // 60
    if minutes < 60:
        return f"há {minutes} min"
    hours = minutes // 60
    if hours < 24:
        return f"há {hours} h"
    days = hours // 24
    if days < 30:
        return "ontem" if days == 1 else f"há {days} dias"
    return value.strftime("%d/%m/%Y")


templates.env.filters["markdown"] = render_markdown
templates.env.filters["time_ago"] = time_ago
