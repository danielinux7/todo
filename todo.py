#!/usr/bin/env python3
"""Tiny todo list with multiple lists.

  todo                      list all lists
  todo <list>               show tasks in <list>
  todo <list> add <text>    add a task (creates the list)
  todo <list> done <n>      toggle task n done/undone
  todo <list> up|down <n>   move task n up or down
  todo <list> rm <n>        remove task n
  todo <list> drop          delete the whole list
"""
import sys, json, os

FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "todos.json")


def load():
    """Return {list_name: [todos]}. Migrates the old single-list file."""
    try:
        with open(FILE) as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}
    if isinstance(data, list):  # old format: one unnamed list
        return {"todo": data} if data else {}
    return data


def save(todos):
    with open(FILE, "w") as f:
        json.dump(todos, f, indent=2)


def show(todos):
    if not todos:
        print("No tasks.")
        return
    for i, t in enumerate(todos, 1):
        print(f"{i}. [{'x' if t['done'] else ' '}] {t['text']}")


def apply(todos, cmd, args):
    """Return new list after applying cmd. Raise ValueError on bad input."""
    if cmd == "add":
        text = " ".join(args).strip()
        if not text:
            raise ValueError("add what? usage: todo <list> add <text>")
        return todos + [{"text": text, "done": False}]
    if cmd in ("done", "rm", "up", "down"):
        try:
            n = int(args[0]) - 1
        except (IndexError, ValueError):
            raise ValueError(f"usage: todo <list> {cmd} <task number>")
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
    """Move list `name` up/down among the lists. Returns a reordered dict."""
    keys = list(data)
    if name not in keys or direction not in ("up", "down"):
        return data
    i = keys.index(name)
    j = i - 1 if direction == "up" else i + 1
    if 0 <= j < len(keys):
        keys[i], keys[j] = keys[j], keys[i]
    return {k: data[k] for k in keys}


def order_keys(data, names):
    """Reorder lists to match `names`. No-op unless `names` is exactly all current names."""
    if sorted(names) != sorted(data):
        return data
    return {k: data[k] for k in names}


def main(argv):
    data = load()
    if not argv:  # list all lists
        if not data:
            print("No lists. Create one: todo <list> add <text>")
            return
        for name, todos in data.items():
            done = sum(t["done"] for t in todos)
            print(f"{name} ({done}/{len(todos)})")
        return
    name, rest = argv[0], argv[1:]
    if not rest:  # show one list
        show(data.get(name, []))
        return
    if rest[0] == "drop":  # delete a whole list
        if data.pop(name, None) is None:
            sys.exit(f"no list '{name}'")
        save(data)
        print(f"dropped '{name}'")
        return
    try:
        data[name] = apply(data.get(name, []), rest[0], rest[1:])
    except ValueError as e:
        sys.exit(str(e))
    save(data)
    show(data[name])


if __name__ == "__main__":
    main(sys.argv[1:])
