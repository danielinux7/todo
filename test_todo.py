from todo import apply, move_key, order_keys, migrate
from server import render


def test():
    # tasks (apply)
    t = apply([], "add", ["buy", "milk"])
    t = apply(t, "add", ["walk dog"])
    assert [x["text"] for x in t] == ["buy milk", "walk dog"]

    t = apply(t, "done", ["1"])
    assert t[0]["done"] is True

    t2 = apply(t, "rm", ["1"])
    assert [x["text"] for x in t2] == ["walk dog"]

    for bad in (["0"], ["9"], ["x"], []):  # zero, out-of-range, non-int, missing
        try:
            apply(t, "done", bad)
            assert False, bad
        except ValueError:
            pass

    # task reorder (up/down neighbour swap; no-op at the edges) and full permutation
    seq = [{"text": "a", "done": False}, {"text": "b", "done": False}, {"text": "c", "done": False}]
    assert [x["text"] for x in apply(seq, "down", ["1"])] == ["b", "a", "c"]
    assert [x["text"] for x in apply(seq, "up", ["3"])] == ["a", "c", "b"]
    assert [x["text"] for x in apply(seq, "up", ["1"])] == ["a", "b", "c"]    # top no-op
    assert [x["text"] for x in apply(seq, "down", ["3"])] == ["a", "b", "c"]  # bottom no-op
    assert [x["text"] for x in apply(seq, "order", ["3", "1", "2"])] == ["c", "a", "b"]
    for bad in (["1", "2"], ["1", "2", "2"], ["1", "2", "9"]):  # not a full permutation
        try:
            apply(seq, "order", bad)
            assert False, bad
        except ValueError:
            pass

    # dict reorder helpers (reused for both boards and lists)
    d = {"x": [], "y": [], "z": []}
    assert list(move_key(d, "y", "up")) == ["y", "x", "z"]
    assert list(move_key(d, "z", "down")) == ["x", "y", "z"]    # bottom no-op
    assert list(move_key(d, "q", "up")) == ["x", "y", "z"]      # unknown no-op
    assert list(order_keys(d, ["z", "x", "y"])) == ["z", "x", "y"]
    assert list(order_keys(d, ["z", "x"])) == ["x", "y", "z"]   # incomplete -> no-op

    # migration to boards > lists > tasks
    one = [{"text": "a", "done": False}]
    assert migrate([]) == {}
    assert migrate(one) == {"todo": {"Tasks": one}}               # oldest: bare task list
    assert migrate({"Work": one}) == {"Work": {"Tasks": one}}     # 2-level list -> board+list
    assert migrate({"Work": {"L": one}}) == {"Work": {"L": one}}  # already 3-level: unchanged
    assert migrate({}) == {}

    # render: boards as pills, active board's lists + tasks, all user text escaped
    data = {"Work": {"todo": [{"text": "<b>boom</b>", "done": False}], "done<x>": []}}
    page = render(data, "Work").decode()
    assert "&lt;b&gt;boom&lt;/b&gt;" in page and "<b>boom</b>" not in page  # task text escaped
    assert 'href="/?board=Work"' in page                          # board pill / switch link
    assert "done&lt;x&gt;" in page and "done<x>" not in page       # list name escaped
    assert 'class="add-btn"' in page                              # + buttons to add list/item
    assert 'class="add hidden"' in page                           # add forms collapsed until +
    print("ok")


if __name__ == "__main__":
    test()
