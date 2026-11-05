from datetime import datetime, timezone

from fastapi.templating import Jinja2Templates
from jinja2 import pass_context
from markdown_it import MarkdownIt
from markupsafe import Markup, escape

from .wiki import WIKILINK_RE, normalize_title

templates = Jinja2Templates(directory="templates")

# HTML cru fica desativado: tudo que o usuário digitar como tag é escapado.
# O markdown-it também recusa links javascript:, vbscript:, file: e data:.
_markdown = (
    MarkdownIt("commonmark", {"html": False, "breaks": True, "typographer": False})
    .enable("table")
    .enable("strikethrough")
)


def _wikilink_rule(state, silent: bool) -> bool:
    """Regra inline: [[Título]] ou [[Título|texto]] vira link para a página."""
    if not state.src.startswith("[[", state.pos):
        return False
    match = WIKILINK_RE.match(state.src, state.pos)
    if match is None:
        return False
    if not silent:
        token = state.push("wikilink", "", 0)
        target = match.group(1).strip()
        token.meta = {"target": target, "label": (match.group(2) or target).strip()}
    state.pos = match.end()
    return True


def _render_wikilink(self, tokens, idx, options, env) -> str:
    meta = tokens[idx].meta
    label = escape(meta["label"])
    page_id = (env or {}).get("wiki_index", {}).get(normalize_title(meta["target"]))
    if page_id is None:
        return (
            f'<span class="wikilink wikilink-missing" '
            f'title="Nenhuma página visível com o título “{escape(meta["target"])}”">{label}</span>'
        )
    return (
        f'<a class="wikilink" href="/p/{page_id}" hx-get="/pages/{page_id}/blocks-editor" '
        f'hx-target="#page-editor-container" hx-push-url="/p/{page_id}">{label}</a>'
    )


_markdown.inline.ruler.before("link", "wikilink", _wikilink_rule)
_markdown.add_render_rule("wikilink", _render_wikilink)


@pass_context
def render_markdown(context, text: str | None) -> Markup:
    if not text:
        return Markup("")
    env = {"wiki_index": context.get("wiki_index") or {}}
    return Markup(_markdown.render(text, env))


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
