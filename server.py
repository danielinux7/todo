#!/usr/bin/env python3
"""Web UI for the todo boards. Run: ./server.py  (starts the server and opens your browser)."""
import html
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlsplit

from todo import load, save, apply, move_key, order_keys

URL = "http://localhost:8000"

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
  body {{ font: 16px/1.5 system-ui, sans-serif; max-width: 52rem; margin: 3rem auto; padding: 0 1rem; background: var(--bg); color: var(--fg); }}
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
  form.add {{ display: flex; gap: .5rem; margin: .3rem 0 0; }}
  form.add input {{ flex: 1; padding: .4rem; background: var(--field); color: var(--fg); border: 1px solid var(--border); border-radius: .3rem; }}
  form.add button {{ opacity: 1; }}
  .add.hidden {{ display: none; }}
  .add-btn {{ font-size: 1.2rem; line-height: 1; }}
  form.inline {{ display: inline; white-space: nowrap; }}
  #pills {{ display: flex; flex-wrap: wrap; gap: .4rem; margin: 1rem 0; }}
  .tab {{ padding: .25rem .7rem; border: 1px solid var(--border); border-radius: 999px; text-decoration: none; color: inherit; cursor: pointer; }}
  .tab.active {{ background: var(--accent); border-color: var(--accent); color: #fff; }}
  #boardhead {{ display: flex; align-items: center; gap: .3rem; margin: .5rem 0; font-size: 1.3rem; }}
  #boardhead .name {{ font-weight: 600; }}
  section {{ border-top: 1px solid var(--border); padding-top: .35rem; margin-top: .9rem; }}
</style>
<script>var s=localStorage.getItem('theme');if(s)document.documentElement.setAttribute('data-theme',s);</script>
<h1><span class="name">todo</span><button id="theme" type="button" title="toggle light/dark">&#9681;</button></h1>
<form class="add" action="/addboard" method="post">
  <input name="name" placeholder="New board" required>
  <button>Add board</button>
</form>
{pills}
{board}
"""

BOARD = """<div id="board">
  <div id="boardhead">
    <form class="inline" action="/moveboard" method="post">
      <input type="hidden" name="board" value="{bname}">
      <button name="dir" value="up" title="move board left">&#8249;</button>
      <button name="dir" value="down" title="move board right">&#8250;</button></form>
    <span class="name">{bname}</span>
    <button class="add-btn" type="button" title="add a list">+</button>
    <form class="inline" action="/dropboard" method="post">
      <input type="hidden" name="board" value="{bname}">
      <button title="delete board">&#10005;</button></form>
  </div>
  <form class="add hidden" action="/addlist" method="post">
    <input type="hidden" name="board" value="{bname}">
    <input name="name" placeholder="New list" required>
    <button>Add</button>
  </form>
  <div id="lists" data-board="{bname}">{lists}</div>
</div>"""

LIST = """<section data-list="{list}">
  <h2><span class="grip" draggable="true" title="drag to reorder">&#10303;</span><span class="name">{list}</span>
    <button class="add-btn" type="button" title="add an item">+</button>
    <form class="inline" action="/movelist" method="post">
      <input type="hidden" name="board" value="{board}"><input type="hidden" name="list" value="{list}">
      <button name="dir" value="up" title="move list up">&#8593;</button>
      <button name="dir" value="down" title="move list down">&#8595;</button></form>
    <form class="inline" action="/droplist" method="post">
      <input type="hidden" name="board" value="{board}"><input type="hidden" name="list" value="{list}">
      <button title="delete list">&#10005;</button></form>
  </h2>
  <form class="add hidden" action="/add" method="post">
    <input type="hidden" name="board" value="{board}"><input type="hidden" name="list" value="{list}">
    <input name="text" placeholder="New item" required>
    <button>Add</button>
  </form>
  <ul data-board="{board}" data-list="{list}">{items}</ul>
</section>"""

ITEM = """<li class="{cls}" draggable="true" data-n="{n}">
  <span class="grip" title="drag to reorder">&#10303;</span>
  <form class="inline" action="/done" method="post">
    <input type="hidden" name="board" value="{board}"><input type="hidden" name="list" value="{list}"><input type="hidden" name="n" value="{n}">
    <button title="toggle">{box}</button></form>
  <span class="text">{text}</span>
  <form class="inline" action="/move" method="post">
    <input type="hidden" name="board" value="{board}"><input type="hidden" name="list" value="{list}"><input type="hidden" name="n" value="{n}">
    <button name="dir" value="up" title="move up">&#8593;</button>
    <button name="dir" value="down" title="move down">&#8595;</button></form>
  <form class="inline" action="/rm" method="post">
    <input type="hidden" name="board" value="{board}"><input type="hidden" name="list" value="{list}"><input type="hidden" name="n" value="{n}">
    <button title="delete">&#10005;</button></form>
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

function persist(url, body) {
  fetch(url, {method: 'POST', body}).then(() => location.reload());
}

const pills = document.getElementById('pills');
if (pills) sortable(pills, '.tab', () => {
  const body = new URLSearchParams();
  pills.querySelectorAll('.tab').forEach(t => body.append('board', t.dataset.name));
  persist('/reorderboards', body);
});

const lists = document.getElementById('lists');
if (lists) sortable(lists, 'section[data-list]', () => {
  const body = new URLSearchParams();
  body.append('board', lists.dataset.board);
  lists.querySelectorAll('section[data-list]').forEach(s => body.append('list', s.dataset.list));
  persist('/reorderlists', body);
});

document.querySelectorAll('ul[data-list]').forEach(ul => sortable(ul, 'li[data-n]', () => {
  const order = [...ul.querySelectorAll('li[data-n]')].map(li => li.dataset.n).join(',');
  persist('/reorder', new URLSearchParams({board: ul.dataset.board, list: ul.dataset.list, order}));
}));

document.querySelectorAll('.add-btn').forEach(btn => btn.onclick = () => {
  const form = btn.closest('section, #board').querySelector('form.add');
  form.classList.toggle('hidden');
  if (!form.classList.contains('hidden')) form.querySelector('input[name="name"], input[name="text"]').focus();
});
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


def render(data, active):
    boards = list(data)
    if active not in data:
        active = boards[0] if boards else ""
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
    return (PAGE.format(pills=pills, board=board) + SCRIPT).encode()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parts = urlsplit(self.path)
        if parts.path != "/":
            self.send_error(404)
            return
        active = parse_qs(parts.query).get("board", [""])[0]
        body = render(load(), active)
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        form = parse_qs(self.rfile.read(length).decode())
        first = lambda k: form.get(k, [""])[0]
        data = load()
        board = first("board")
        stay = board  # board to return to after the action
        try:
            if self.path == "/addboard":
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
            save(data)
        except ValueError:
            pass  # ponytail: bad input -> ignore, just re-render
        self.send_response(303)
        self.send_header("Location", "/?board=" + quote(stay) if stay else "/")
        self.end_headers()

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
