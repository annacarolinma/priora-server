from app.repositories import notification_repository as repo


class FakeTx:
    def __init__(self):
        self.calls = []

    def run(self, query, **params):
        self.calls.append(params)

        class R:
            def single(self_inner):
                return {"n": len(params.get("ids", []))}

        return R()


def test_author_never_notified_and_no_duplicates():
    tx = FakeTx()
    n = repo.create_notifications(tx, ["a", "b", "b", "c", None], "X", "msg", "caso1", "a")
    assert n == 2
    assert tx.calls[0]["ids"] == ["b", "c"]


def test_no_recipients_means_no_query():
    tx = FakeTx()
    assert repo.create_notifications(tx, ["a", None], "X", "msg", "caso1", "a") == 0
    assert tx.calls == []
