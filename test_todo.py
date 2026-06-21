from todo import apply, move_key, order_keys
from server import render


def test():
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

    # task reorder (up/down swap with neighbour; no-op at the edges)
    seq = [{"text": "a", "done": False}, {"text": "b", "done": False}, {"text": "c", "done": False}]
    assert [x["text"] for x in apply(seq, "down", ["1"])] == ["b", "a", "c"]
    assert [x["text"] for x in apply(seq, "up", ["3"])] == ["a", "c", "b"]
    assert [x["text"] for x in apply(seq, "up", ["1"])] == ["a", "b", "c"]    # top no-op
    assert [x["text"] for x in apply(seq, "down", ["3"])] == ["a", "b", "c"]  # bottom no-op

    # full task reorder via permutation (drag-and-drop)
    assert [x["text"] for x in apply(seq, "order", ["3", "1", "2"])] == ["c", "a", "b"]
    for bad in (["1", "2"], ["1", "2", "2"], ["1", "2", "9"]):  # not a full permutation
        try:
            apply(seq, "order", bad)
            assert False, bad
        except ValueError:
            pass

    # list reorder
    d = {"x": [], "y": [], "z": []}
    assert list(move_key(d, "y", "up")) == ["y", "x", "z"]
    assert list(move_key(d, "z", "down")) == ["x", "y", "z"]    # bottom no-op
    assert list(move_key(d, "q", "up")) == ["x", "y", "z"]      # unknown no-op
    assert list(order_keys(d, ["z", "x", "y"])) == ["z", "x", "y"]
    assert list(order_keys(d, ["z", "x"])) == ["x", "y", "z"]   # incomplete -> no-op

    # render: active panel + switch tabs, all user text escaped
    data = {"groceries": [{"text": "<b>boom</b>", "done": False}], "work<x>": []}
    page = render(data, "groceries").decode()
    assert "&lt;b&gt;boom&lt;/b&gt;" in page and "<b>boom</b>" not in page  # task text escaped
    assert "groceries" in page                                  # active list shown
    assert "work&lt;x&gt;" in page and "work<x>" not in page     # other list (tab) escaped
    assert 'href="/?list=work' in page                          # switch link present
    print("ok")


if __name__ == "__main__":
    test()
