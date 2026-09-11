import json

import pytest

from app.conversation_memory import dialogue_events, profile_updates, source_views
from app.errors import ChatError
from app.prompt_context import build_messages
from app.repository import SQLiteRepository
from app.relationship import RelationshipState
from tests.test_persistence import commit, decision, start


@pytest.fixture
def repo(tmp_path):
    store = SQLiteRepository(tmp_path / "memory.sqlite3")
    store.upgrade()
    yield store
    store.engine.dispose()


@pytest.mark.parametrize("message,previous,expected", [
    ("나는 민석 이야", "네가 누구지?", {"name": "민석"}),
    ("내 이름은 민석이야", "", {"name": "민석"}),
    ("내 이름은 유이야", "", {"name": "유이"}),
    ("내 이름은 민수야", "", {"name": "민수"}),
    ("이제 홍으로 불러", "", {"preferred_address": "홍"}),
    ("나를 홍이라고 불러줘", "", {"preferred_address": "홍"}),
    ("나 민석 아니고 이제 홍이라고 불러", "", {"preferred_address": "홍"}),
    ("내 이름을 잊어줘", "", {"name": None}),
    ("나는 학생이야", "뭐 하고 있어?", {}),
    ("친구 이름은 민석이야", "", {}),
    ("내 이름은 민석이야?", "", {}),
    ("'내 이름은 민석이야'라고 했어", "", {}),
    ("나는 트럼프", "유이야. 너는?", {"name": "트럼프"}),
    ("나는 민석", "네 이름이 뭐야?", {"name": "민석"}),
    ("나는 트럼프", "오늘 뭐 했어?", {}),
    ("나는 학생", "유이야. 너는?", {}),
    ("나는 트럼프?", "유이야. 너는?", {}),
])
def test_explicit_profile_sources(message, previous, expected):
    assert profile_updates(message, previous) == expected


def raw(n, message="오늘도 안녕", reply="반가워!"):
    return dict(client_turn_id=str(n), user_message=message, decision={"reply": reply})


def test_profile_and_event_survive_500_turns_and_update_separately():
    rows = [raw(0, "내 이름은 민석이야"), raw(1, "책 추천해줘", "'도리언 그레이' 읽어봐.")]
    rows += [raw(n) for n in range(2, 502)]
    notes = source_views(rows, "책 이름이 뭐였지?")
    assert json.loads(notes[0]["content"])["value"] == "민석"
    event = json.loads(notes[1]["content"])
    assert event["value"] == "도리언 그레이" and event["actor"] == "character" and event["source_turn"] == "1"
    rows.append(raw(502, "이제 홍으로 불러"))
    notes = source_views(rows, "내 이름이 뭐였지?")
    assert {json.loads(n["content"])["key"]: json.loads(n["content"])["value"] for n in notes} == {
        "name": "민석", "preferred_address": "홍"}
    notes = source_views(rows, "내 이름은 준호야")
    assert json.loads(notes[0]["content"])["value"] == "준호"
    assert json.loads(source_views(rows, "내 이름을 잊어줘")[0]["content"])["value"] is None
    assert not any(n["kind"] == "episode" for n in source_views(rows, "좋아하는 영화 기억해?"))


def test_attributed_events_never_infer_completion_or_user_preference():
    events = dialogue_events("책 추천해줘", "'도리언 그레이' 읽어봐.", "source")
    assert events[0]["type"] == "recommendation" and events[0]["actor"] == "character"
    assert dialogue_events("책 이름이 뭐였지?", "아마도 '다른 제목'이었을 거야.", "bad") == []
    events = dialogue_events("약속할게", "내가 끓여줄게!", "promise")
    assert all(e["type"] == "proposal_or_promise_statement" for e in events)
    assert events[-1]["actor"] == "character" and "completed" not in str(events)
    assert dialogue_events("책은 빌려놨어?", "네, 아직 있어!", "ambiguous") == []
    assert dialogue_events("오늘 약속 취소할게", "알았어.", "cancel")[0]["type"] == "cancellation_statement"


def test_cancellation_ignores_negation_questions_and_reported_quotes():
    assert dialogue_events("약속은 취소 안 할게.", "알았어.", "negated") == []
    assert dialogue_events("약속은 취소는 안 할게.", "알았어.", "negated-topic") == []
    assert dialogue_events("약속을 취소하지는 않을게.", "알았어.", "negated-long") == []
    assert dialogue_events("약속 취소할까?", "글쎄.", "question") == []
    assert dialogue_events("친구가 '약속 취소할게'라고 말했어.", "그렇구나.", "reported") == []


def test_targeted_cancellation_keeps_unrelated_promise_evidence():
    rows = [raw(0, "내일 도서관에서 만나자.", "알았어."),
            raw(1, "모레 공원에서 만나자.", "알았어."),
            raw(2, "내일 도서관 약속만 취소할게.", "알았어.")]
    events = [json.loads(note["content"]) for note in source_views(rows, "우리 약속 뭐였지?")
              if note["kind"] == "episode"]
    assert any("공원" in event["quote"] and event["type"] == "proposal_or_promise_statement"
               for event in events)
    assert not any("도서관" in event["quote"] and event["type"] == "proposal_or_promise_statement"
                   for event in events)


def test_natural_movie_suggestion_and_scheduled_meeting_are_attributed_sources():
    rows = [raw(0, "너 이름이 뭐야", "유이야. 너는?"), raw(1, "나는 트럼프"),
            raw(2, "뭐가 재밌어?", "오늘 영화는 '인터스텔라' 어때?"),
            raw(3, "오늘 저녁 7시에 보러갈까", "좋아! 7 시에 만나요.")]
    movie = [json.loads(n["content"]) for n in source_views(rows, "영화 뭐였지?") if n["kind"] == "episode"]
    assert movie[0]["value"] == "인터스텔라" and movie[0]["actor"] == "character"
    meeting = [json.loads(n["content"]) for n in source_views(rows, "우리 몇 시에 만나?") if n["kind"] == "episode"]
    assert {e["actor"] for e in meeting} == {"user", "character"}
    assert all(e["type"] == "proposal_or_promise_statement" for e in meeting)
    notes = source_views(rows, "사진은 뭘로 찍어?")
    assert len(notes) == 1 and json.loads(notes[0]["content"])["value"] == "트럼프"
    assert dialogue_events("'인터스텔라' 추천했어?", "몰라", "q") == []
    assert dialogue_events("오늘 7시에 안 만나요.", "알았어", "negative") == []
    assert dialogue_events("'인터스텔라' 재밌어?", "몰라", "q") == []


def test_ambiguous_recall_uses_active_reference_and_ignores_closed_topic():
    movie_rows = [raw(0, "오늘 볼 영화 골라줘", "영화는 '리틀 포레스트' 어때?")]
    movie_history = [{"role": "user", "content": "네가 고른 작품으로 할래."},
                     {"role": "assistant", "content": "좋아."}]
    selected = [json.loads(note["content"]) for note in source_views(movie_rows, "그거 뭐였지?", movie_history)
                if note["kind"] == "episode"]
    assert len(selected) == 1 and selected[0]["value"] == "리틀 포레스트"

    rows = movie_rows + [raw(1, "주말에 읽을 책 골라줘", "'모모' 읽어봐.")]
    selected = [json.loads(note["content"]) for note in source_views(rows, "그거 뭐였지?", movie_history)
                if note["kind"] == "episode"]
    assert len(selected) == 1 and selected[0]["value"] == "모모"

    closed = [{"role": "user", "content": "영화 얘기는 그만하자. 이제 책상 위를 정리하고 있어."},
              {"role": "assistant", "content": "깔끔하게 해!"}]
    assert not any(note["kind"] == "episode" for note in source_views(rows, "그거 뭐였지?", closed))
    for unrelated in ("산책하기 좋은 날이야.", "새 정책을 확인했어.", "책상을 정리하고 있어."):
        history = [{"role": "user", "content": unrelated}, {"role": "assistant", "content": "그래."}]
        assert not any(note["kind"] == "episode" for note in source_views(rows, "그거 뭐였지?", history))


def test_ambiguous_recall_without_active_anchor_selects_no_episode():
    rows = [raw(0, "영화 추천해줘", "영화는 '리틀 포레스트' 어때?")]
    history = [{"role": "user", "content": "응 알았어."}, {"role": "assistant", "content": "좋아."}]
    assert not any(note["kind"] == "episode" for note in source_views(rows, "그게 뭐였더라?", history))


def test_ambiguous_location_uses_active_time_but_cancellation_clears_old_promise():
    rows = [raw(0, "오늘 저녁 8시에 영화 보러갈까?", "좋아. 만나자."),
            raw(1, "오늘 약속은 취소야", "알았어."),
            raw(2, "내일 6시에 다시 만나자", "그래.")]
    timed = [{"role": "user", "content": "벌써 6시네."}, {"role": "assistant", "content": "그러게."}]
    selected = [json.loads(note["content"]) for note in source_views(rows, "어딜?", timed)
                if note["kind"] == "episode"]
    assert selected and all(event["source_turn"] == "2" for event in selected)

    cancelled = [{"role": "user", "content": "오늘 영화 약속은 취소야. 어디에도 안 갈 거야."},
                 {"role": "assistant", "content": "알았어."}]
    assert not any(note["kind"] == "episode" for note in source_views(rows[:2], "어딜?", cancelled))


def test_source_views_only_read_committed_owner_data_and_reset(repo):
    sid, pid = start(repo)
    _, other = start(repo)
    commit(repo, pid, "name", "내 이름은 민석이야")
    commit(repo, pid, "book", "책 추천해줘", decision(reply="'도리언 그레이' 읽어봐."))
    for n in range(25):
        commit(repo, pid, f"filler{n}")
    assert len(repo.load(pid, "default").history) == 54
    assert len(repo.recall(pid, "default", "책 이름 뭐였지?")) == 2
    assert repo.recall(other, "default", "책 이름 뭐였지?") == []
    assert repo.recall(pid, "other-character", "책 이름 뭐였지?") == []
    reopened = SQLiteRepository(repo.path)
    try:
        assert reopened.recall(pid, "default", "책 이름 뭐였지?") == repo.recall(pid, "default", "책 이름 뭐였지?")
    finally:
        reopened.engine.dispose()
    before = repo.load(pid, "default")
    def fail(point):
        if point == "after_turn":
            raise RuntimeError("rollback")
    repo.failpoint = fail
    with pytest.raises(RuntimeError):
        commit(repo, pid, "failed", "내 이름은 준호야")
    assert repo.load(pid, "default") == before
    assert "준호" not in str(repo.recall(pid, "default", "내 이름?"))
    repo.failpoint = lambda _: None
    repo.reset_conversation(sid, pid, "default", RelationshipState())
    assert repo.recall(pid, "default", "책 이름?") == []
    assert repo.load(pid, "default").history == []


def build(history, notes, budget=4000, count=None, assistant_reply=None):
    return build_messages(system="rules", message="책 이름 뭐였지?", history=history, summary="",
        memories=notes, relationship={}, flags=[], budget=budget,
        count=count or (lambda ms: sum(len(m["content"]) for m in ms)), assistant_reply=assistant_reply)


def test_budget_reserves_evidence_and_removes_old_complete_pairs_efficiently():
    rows = [raw(0, "내 이름은 민석이야"), raw(1, "책 추천해줘", "'도리언 그레이' 읽어봐.")]
    notes = source_views(rows, "책 이름 뭐였지?")
    history = [{"role": role, "content": f"{n}: hello world"} for n in range(500) for role in ("user", "assistant")]
    calls = []
    def count(ms):
        calls.append(1)
        return sum(len(m["content"]) for m in ms)
    msgs, tokens, trimmed = build(history, notes, count=count)
    assert trimmed and tokens <= 4000 and len(calls) < 15
    assert "민석" in msgs[0]["content"] and "도리언 그레이" in msgs[0]["content"]
    assert msgs[-2] == history[-1] and len(msgs[1:-1]) % 2 == 0
    assert history[0]["content"] == "0: hello world"
    with pytest.raises(ChatError):
        build(history, notes, budget=10)


def test_metadata_budget_keeps_frozen_reply_and_same_sources():
    notes = source_views([raw(0, "내 이름은 민석이야")], "이름?")
    messages, _, _ = build([], notes, assistant_reply="민석이잖아!")
    assert "assistant_reply_to_analyze" in messages[0]["content"]
    assert "민석이잖아!" in messages[0]["content"]


def test_api_uses_raw_history_and_sources_without_extra_model_call(backend):
    client, store, llm = backend
    ids = client.post("/api/session", json={}).json()
    pid = ids["profile_id"]
    original_commit = store.commit
    store.commit = SQLiteRepository.commit.__get__(store)
    commit(store, pid, "intro", "내 이름은 민석이야")
    commit(store, pid, "book", "책 추천해줘", decision(reply="'도리언 그레이' 읽어봐."))
    for n in range(10):
        commit(store, pid, f"filler{n}")
    store.commit = original_commit
    payload = {**ids, "message": "책 이름이 뭐였지?", "client_turn_id": "recall"}
    r = client.post("/api/chat", json=payload)
    assert r.status_code == 200
    assert len(llm.calls[-1]["history"]) == 24
    assert {m["kind"] for m in llm.calls[-1]["memories"]} == {"profile", "episode"}
    assert client.post("/api/chat", json=payload).json() == r.json()
    assert len(llm.calls) == 1
