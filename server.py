#!/usr/bin/env python3
"""Web UI for the todo boards. Run: ./server.py  (starts the server and opens your browser)."""
import html
import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlsplit

from todo import load, save, apply, move_key, order_keys, rename_key, copy_key

URL = "http://localhost:8000"

# Whole-document undo/redo. Each entry is a full snapshot of `data`; simpler and
# always correct vs per-op inverses, and a todo list is tiny.
# Single globals: localhost, one user. Reset on restart.
HISTORY = 10
UNDO, REDO = [], []

PAGE = """<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>todo</title>
<style>
  html {{ color-scheme: light dark; }}
  :root, :root[data-theme="light"] {{ --bg:#fff; --fg:#222; --muted:#999; --border:#ddd; --field:#fff; --accent:#2563eb; }}
  @media (prefers-color-scheme: dark) {{
    :root {{ --bg:#181818; --fg:#e6e6e6; --muted:#888; --border:#3a3a3a; --field:#242424; --accent:#3b82f6; }}
  }}
  :root[data-theme="dark"] {{ --bg:#181818; --fg:#e6e6e6; --muted:#888; --border:#3a3a3a; --field:#242424; --accent:#3b82f6; }}
  body {{ font: 16px/1.5 system-ui, sans-serif; max-width: 72rem; margin: 2rem auto; padding: 0 1.5rem; background: var(--bg); color: var(--fg); }}
  h1 {{ display: flex; align-items: center; margin-bottom: 1rem; }}
  #theme {{ cursor: pointer; background: none; border: 0; color: inherit; font-size: 1.3rem; padding: 0; }}
  h2 {{ display: flex; align-items: center; gap: .3rem; font-size: 1.05rem; margin: 0 0 .2rem; }}
  ul {{ list-style: none; padding: 0; margin: 0; }}
  li {{ display: flex; align-items: center; gap: .3rem; padding: .15rem 0; }}
  li.empty {{ color: var(--muted); font-style: italic; }}
  .name, .text {{ flex: 1; }}
  li.done .text {{ text-decoration: line-through; color: var(--muted); }}
  .grip {{ cursor: grab; opacity: .35; }}
  .drag {{ opacity: .4; }}
  button {{ cursor: pointer; background: none; border: 0; font: inherit; padding: .15rem .25rem; color: inherit; opacity: .7; }}
  button:hover {{ opacity: 1; }}
  form.inline {{ display: inline; white-space: nowrap; }}
  #toolbar {{ display: flex; align-items: center; gap: .15rem; margin: 1rem 0; padding: .3rem .4rem;
    border: 1px solid var(--border); border-radius: .4rem; width: max-content; }}
  #toolbar button {{ font-size: 1.15rem; opacity: 1; padding: .25rem .5rem; border-radius: .3rem; }}
  #toolbar button:not(:disabled):hover {{ background: var(--field); }}
  #toolbar button:disabled {{ opacity: .25; cursor: default; }}
  #toolbar .bar {{ width: 1px; align-self: stretch; background: var(--border); margin: .15rem .3rem; }}
  [data-kind] {{ cursor: pointer; }}
  .selected {{ outline: 2px solid var(--accent); outline-offset: 2px; border-radius: .2rem; }}
  #pills {{ display: flex; flex-wrap: wrap; gap: .4rem; margin: 1rem 0; }}
  .tab {{ padding: .25rem .7rem; border: 1px solid var(--border); border-radius: 999px; text-decoration: none; color: inherit; cursor: pointer; }}
  .tab.active {{ background: var(--accent); border-color: var(--accent); color: #fff; }}
  #boardhead {{ display: flex; align-items: center; gap: .3rem; margin: .5rem 0; font-size: 1.3rem; }}
  #boardhead .name {{ font-weight: 600; }}
  section {{ border-top: 1px solid var(--border); padding-top: .35rem; margin-top: .9rem; }}
</style>
<script>var s=localStorage.getItem('theme');if(s)document.documentElement.setAttribute('data-theme',s);</script>
<h1><span class="name">todo</span><button id="theme" type="button" title="toggle light/dark">&#9681;</button></h1>
{toolbar}
{pills}
{board}
"""

TOOLBAR = """<div id="toolbar">
  <form class="inline" action="/undo" method="post"><input type="hidden" name="board" value="{active}">
    <button title="Undo" {undis}>&#8634;</button></form>
  <form class="inline" action="/redo" method="post"><input type="hidden" name="board" value="{active}">
    <button title="Redo" {redis}>&#8635;</button></form>
  <span class="bar"></span>
  <button id="t-add" type="button" title="Add (board / list / task by what's selected)">&#43;</button>
  <button id="t-up" type="button" title="Move up" disabled>&#8593;</button>
  <button id="t-down" type="button" title="Move down" disabled>&#8595;</button>
  <span class="bar"></span>
  <button id="t-edit" type="button" title="Edit selected" disabled>&#9998;</button>
  <button id="t-copy" type="button" title="Copy selected" disabled>&#10697;</button>
  <button id="t-del" type="button" title="Delete selected" disabled>&#128465;</button>
</div>"""

BOARD = """<div id="board">
  <div id="boardhead">
    <span class="name" data-kind="board" data-board="{bname}">{bname}</span>
  </div>
  <div id="lists" data-board="{bname}">{lists}</div>
</div>"""

LIST = """<section data-list="{list}">
  <h2><span class="grip" draggable="true" title="drag to reorder">&#10303;</span>
    <span class="name" data-kind="list" data-board="{board}" data-list="{list}">{list}</span></h2>
  <ul data-board="{board}" data-list="{list}">{items}</ul>
</section>"""

ITEM = """<li class="{cls}" draggable="true" data-n="{n}">
  <span class="grip" title="drag to reorder">&#10303;</span>
  <form class="inline" action="/done" method="post">
    <input type="hidden" name="board" value="{board}"><input type="hidden" name="list" value="{list}"><input type="hidden" name="n" value="{n}">
    <button title="toggle">{box}</button></form>
  <span class="text" data-kind="item" data-board="{board}" data-list="{list}" data-n="{n}" data-text="{text}">{text}</span>
</li>"""

PILL = '<a class="tab{cls}" href="/?board={url}" data-name="{esc}" draggable="true">{esc}</a>'

SCRIPT = """<script>
const root = document.documentElement;
document.getElementById('theme').onclick = () => {
  const cur = root.getAttribute('data-theme')
    || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  const next = cur === 'dark' ? 'light' : 'dark';
  root.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
};

function sortable(container, sel, onDrop) {
  let dragged = null;
  container.addEventListener('dragstart', e => {
    dragged = e.target.closest(sel);
    if (dragged) dragged.classList.add('drag');
  });
  container.addEventListener('dragover', e => {
    if (!dragged || dragged.parentElement !== container) return;
    e.preventDefault();
    const after = [...container.querySelectorAll(sel + ':not(.drag)')]
      .find(el => e.clientY < el.getBoundingClientRect().top + el.offsetHeight / 2);
    container.insertBefore(dragged, after || null);
  });
  container.addEventListener('dragend', () => {
    if (!dragged) return;
    dragged.classList.remove('drag');
    onDrop();
    dragged = null;
  });
}

function post(url, params) {
  fetch(url, {method: 'POST', body: new URLSearchParams(params)}).then(() => location.reload());
}

const pills = document.getElementById('pills');
if (pills) sortable(pills, '.tab', () => {
  const body = new URLSearchParams();
  pills.querySelectorAll('.tab').forEach(t => body.append('board', t.dataset.name));
  fetch('/reorderboards', {method: 'POST', body}).then(() => location.reload());
});

const lists = document.getElementById('lists');
if (lists) sortable(lists, 'section[data-list]', () => {
  const body = new URLSearchParams();
  body.append('board', lists.dataset.board);
  lists.querySelectorAll('section[data-list]').forEach(s => body.append('list', s.dataset.list));
  fetch('/reorderlists', {method: 'POST', body}).then(() => location.reload());
});

document.querySelectorAll('ul[data-list]').forEach(ul => sortable(ul, 'li[data-n]', () => {
  const order = [...ul.querySelectorAll('li[data-n]')].map(li => li.dataset.n).join(',');
  post('/reorder', {board: ul.dataset.board, list: ul.dataset.list, order});
}));

// Click a board name / list name / task to select it; the toolbar acts on the selection.
let sel = null;
const tbtn = id => document.getElementById(id);
function select(el) {
  if (sel) sel.classList.remove('selected');
  sel = sel === el ? null : el;
  if (sel) sel.classList.add('selected');
  ['t-up', 't-down', 't-edit', 't-copy', 't-del'].forEach(id => tbtn(id).disabled = !sel);
}
document.querySelectorAll('[data-kind]').forEach(el => el.onclick = e => { e.stopPropagation(); select(el); });

function ids() { const d = sel.dataset; return {kind: d.kind, board: d.board || '', list: d.list || '', n: d.n || ''}; }

// Add: child of the selection (board->list, list/task->task), or a new board when nothing is selected.
tbtn('t-add').onclick = () => {
  if (!sel) { const v = prompt('New board:'); if (v) post('/addboard', {name: v}); return; }
  const d = sel.dataset;
  if (d.kind === 'board') { const v = prompt('New list:'); if (v) post('/addlist', {board: d.board, name: v}); }
  else { const v = prompt('New task:'); if (v) post('/add', {board: d.board, list: d.list, text: v}); }
};

const MOVE = {item: '/move', list: '/movelist', board: '/moveboard'};
tbtn('t-up').onclick = () => sel && post(MOVE[sel.dataset.kind], {...ids(), dir: 'up'});
tbtn('t-down').onclick = () => sel && post(MOVE[sel.dataset.kind], {...ids(), dir: 'down'});

const DEL = {item: '/rm', list: '/droplist', board: '/dropboard'};
tbtn('t-del').onclick = () => sel && post(DEL[sel.dataset.kind], ids());
tbtn('t-copy').onclick = () => sel && post('/copy', ids());
tbtn('t-edit').onclick = () => {
  if (!sel) return;
  const d = sel.dataset, v = prompt('Edit:', d.text || d.list || d.board);
  if (v !== null) post('/edit', {...ids(), text: v});
};
</script>"""


def render_list(board, name, tasks):
    eb, el = html.escape(board), html.escape(name)
    items = "".join(
        ITEM.format(
            cls="done" if t["done"] else "",
            board=eb, list=el, n=i,
            box="&#9745;" if t["done"] else "&#9744;",
            text=html.escape(t["text"]),
        )
        for i, t in enumerate(tasks, 1)
    ) or '<li class="empty">empty</li>'
    return LIST.format(board=eb, list=el, items=items)


def render(data, active, can_undo=False, can_redo=False):
    boards = list(data)
    if active not in data:
        active = boards[0] if boards else ""
    toolbar = TOOLBAR.format(active=html.escape(active),
                             undis="" if can_undo else "disabled",
                             redis="" if can_redo else "disabled")
    pills = "".join(
        PILL.format(cls=" active" if b == active else "", url=html.escape(quote(b)), esc=html.escape(b))
        for b in boards
    )
    pills = '<nav id="pills">{}</nav>'.format(pills) if pills else ""
    if active:
        sections = "".join(render_list(active, name, tasks) for name, tasks in data[active].items())
        sections = sections or "<p>No lists yet. Add one above.</p>"
        board = BOARD.format(bname=html.escape(active), lists=sections)
    else:
        board = "<p>Create a board to get started.</p>"
    return (PAGE.format(toolbar=toolbar, pills=pills, board=board) + SCRIPT).encode()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parts = urlsplit(self.path)
        if parts.path != "/":
            self.send_error(404)
            return
        active = parse_qs(parts.query).get("board", [""])[0]
        body = render(load(), active, bool(UNDO), bool(REDO))
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        global UNDO, REDO
        length = int(self.headers.get("Content-Length", 0))
        form = parse_qs(self.rfile.read(length).decode())
        first = lambda k: form.get(k, [""])[0]
        data = load()
        before = json.loads(json.dumps(data))  # snapshot before mutating
        board = first("board")
        stay = board  # board to return to after the action
        undoredo = self.path in ("/undo", "/redo")
        try:
            if self.path == "/undo":
                if UNDO:
                    REDO.append(before); del REDO[:-HISTORY]
                    data = UNDO.pop()
            elif self.path == "/redo":
                if REDO:
                    UNDO.append(before); del UNDO[:-HISTORY]
                    data = REDO.pop()
            elif self.path == "/addboard":
                name = first("name").strip()
                if name and name not in data:
                    data[name] = {}
                stay = name
            elif self.path == "/dropboard":
                data.pop(board, None)
                stay = ""
            elif self.path == "/moveboard":
                data = move_key(data, board, first("dir"))
            elif self.path == "/reorderboards":
                data = order_keys(data, form.get("board", []))
            elif self.path == "/edit":
                data = self.do_edit(data, first)
            elif self.path == "/copy":
                data = self.do_copy(data, first)
            elif self.path in ("/addlist", "/droplist", "/movelist", "/reorderlists"):
                lists = data.get(board)
                if lists is not None:
                    if self.path == "/addlist":
                        name = first("name").strip()
                        if name and name not in lists:
                            lists[name] = []
                    elif self.path == "/droplist":
                        lists.pop(first("list"), None)
                    elif self.path == "/movelist":
                        data[board] = move_key(lists, first("list"), first("dir"))
                    else:  # /reorderlists
                        data[board] = order_keys(lists, form.get("list", []))
            elif self.path in ("/add", "/done", "/rm", "/move", "/reorder"):
                lists = data.get(board)
                name = first("list")
                if lists is not None and name in lists:
                    if self.path == "/add":
                        cmd, arg = "add", [first("text")]
                    elif self.path == "/move":
                        cmd, arg = first("dir"), [first("n")]
                    elif self.path == "/reorder":
                        cmd, arg = "order", first("order").split(",")
                    else:
                        cmd, arg = self.path[1:], [first("n")]
                    lists[name] = apply(lists[name], cmd, arg)
            else:
                self.send_error(404)
                return
            if undoredo:
                save(data)
            elif data != before:  # only real changes enter history
                UNDO.append(before); del UNDO[:-HISTORY]; REDO.clear()
                save(data)
        except ValueError:
            pass  # ponytail: bad input -> ignore, just re-render
        self.send_response(303)
        self.send_header("Location", "/?board=" + quote(stay) if stay else "/")
        self.end_headers()

    def do_edit(self, data, first):
        """Rename a board/list or retext a task to first('text')."""
        kind, board, text = first("kind"), first("board"), first("text").strip()
        if kind == "board":
            return rename_key(data, board, text)
        lists = data.get(board)
        if lists is None:
            return data
        if kind == "list":
            data[board] = rename_key(lists, first("list"), text)
        elif kind == "item" and text:
            name = first("list")
            n = int(first("n")) - 1
            if name in lists and 0 <= n < len(lists[name]):
                lists[name][n] = {**lists[name][n], "text": text}
        return data

    def do_copy(self, data, first):
        """Duplicate a board/list (deep copy, '<name> copy') or a task (right after it)."""
        kind, board = first("kind"), first("board")
        if kind == "board":
            return copy_key(data, board)
        lists = data.get(board)
        if lists is None:
            return data
        if kind == "list":
            data[board] = copy_key(lists, first("list"))
        elif kind == "item":
            name = first("list")
            n = int(first("n")) - 1
            if name in lists and 0 <= n < len(lists[name]):
                lists[name].insert(n + 1, dict(lists[name][n]))
        return data

    def log_message(self, format, *args):
        pass  # quiet


if __name__ == "__main__":
    try:
        srv = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
    except OSError:
        print(f"todo already running at {URL} -- opening browser")
        webbrowser.open(URL)
    else:
        print(f"todo on {URL}  (Ctrl-C to stop)")
        webbrowser.open(URL)
        srv.serve_forever()
