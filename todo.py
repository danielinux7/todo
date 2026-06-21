#!/usr/bin/env python3
"""Tiny todo: boards > lists > tasks.

  todo                              list all boards
  todo <board>                      list the lists in a board
  todo <board> <list>              show tasks in a list
  todo <board> <list> add <text>    add a task (creates board/list as needed)
  todo <board> <list> done <n>      toggle task n done/undone
  todo <board> <list> up|down <n>   move task n up or down
  todo <board> <list> rm <n>        remove task n
  todo <board> <list> drop          delete the list
  todo <board> drop                 delete the board
"""
import sys, json, os
from typing import Any

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "todos.json")


def migrate(data) -> dict[str, Any]:
    """Upgrade older formats to {board: {list: [tasks]}}."""
    if isinstance(data, list):  # oldest: one unnamed task list
        data = {"todo": data} if data else {}
    if data and all(isinstance(v, list) for v in data.values()):  # {list: [tasks]}
        data = {board: ({"Tasks": tasks} if tasks else {}) for board, tasks in data.items()}
    return data


def load() -> dict[str, Any]:
    """Return {board: {list: [tasks]}}, migrating older files."""
    try:
        with open(FILE) as f:
            return migrate(json.load(f))
    except FileNotFoundError:
        return {}


def save(data):
    with open(FILE, "w") as f:
        json.dump(data, f, indent=2)


def show(todos):
    if not todos:
        print("No tasks.")
        return
    for i, t in enumerate(todos, 1):
        print(f"{i}. [{'x' if t['done'] else ' '}] {t['text']}")


def apply(todos, cmd, args):
    """Return a new task list after applying cmd. Raise ValueError on bad input."""
    if cmd == "add":
        text = " ".join(args).strip()
        if not text:
            raise ValueError("add what? usage: todo <board> <list> add <text>")
        return todos + [{"text": text, "done": False}]
    if cmd in ("done", "rm", "up", "down"):
        try:
            n = int(args[0]) - 1
        except (IndexError, ValueError):
            raise ValueError(f"usage: todo <board> <list> {cmd} <task number>")
        if not 0 <= n < len(todos):
            raise ValueError(f"no task {n + 1} (have {len(todos)})")
        todos = [dict(t) for t in todos]
        if cmd == "done":
            todos[n]["done"] = not todos[n]["done"]
        elif cmd == "rm":
            todos.pop(n)
        else:  # up / down: swap with neighbour, no-op at the edge
            j = n - 1 if cmd == "up" else n + 1
            if 0 <= j < len(todos):
                todos[n], todos[j] = todos[j], todos[n]
        return todos
    if cmd == "order":  # full reorder by 1-based positions (drag-and-drop)
        try:
            idx = [int(a) - 1 for a in args]
        except ValueError:
            raise ValueError("order needs task numbers")
        if sorted(idx) != list(range(len(todos))):
            raise ValueError("order must list every task exactly once")
        return [dict(todos[i]) for i in idx]
    raise ValueError(__doc__)


def move_key(data, name, direction):
    """Move key `name` up/down among the keys of `data`. Returns a reordered dict."""
    keys = list(data)
    if name not in keys or direction not in ("up", "down"):
        return data
    i = keys.index(name)
    j = i - 1 if direction == "up" else i + 1
    if 0 <= j < len(keys):
        keys[i], keys[j] = keys[j], keys[i]
    return {k: data[k] for k in keys}


def order_keys(data, names):
    """Reorder `data` to match `names`. No-op unless `names` is exactly all current keys."""
    if sorted(names) != sorted(data):
        return data
    return {k: data[k] for k in names}


def main(argv):
    data = load()
    if not argv:  # list boards
        if not data:
            print("No boards. Create: todo <board> <list> add <text>")
            return
        for board, lists in data.items():
            tasks = sum(len(t) for t in lists.values())
            print(f"{board} ({len(lists)} lists, {tasks} tasks)")
        return
    board, rest = argv[0], argv[1:]
    if rest == ["drop"]:  # delete a board
        if data.pop(board, None) is None:
            sys.exit(f"no board '{board}'")
        save(data)
        print(f"dropped board '{board}'")
        return
    lists = data.get(board, {})
    if not rest:  # list the lists in a board
        if not lists:
            print(f"(no lists in '{board}')")
        for name, tasks in lists.items():
            done = sum(t["done"] for t in tasks)
            print(f"{name} ({done}/{len(tasks)})")
        return
    name, rest = rest[0], rest[1:]
    if rest == ["drop"]:  # delete a list
        if lists.pop(name, None) is None:
            sys.exit(f"no list '{name}' in '{board}'")
        data[board] = lists
        save(data)
        print(f"dropped list '{name}'")
        return
    if not rest:  # show tasks in a list
        show(lists.get(name, []))
        return
    try:
        lists[name] = apply(lists.get(name, []), rest[0], rest[1:])
    except ValueError as e:
        sys.exit(str(e))
    data[board] = lists
    save(data)
    show(lists[name])


if __name__ == "__main__":
    main(sys.argv[1:])
