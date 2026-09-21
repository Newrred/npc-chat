from fastapi.testclient import TestClient

from app.character_config import load_character_config
from app.main import create_app
from tests.fakes import FakeLLM, FakeStore


class CharacterRecordingLLM(FakeLLM):
    def __init__(self):
        super().__init__()
        self.character = load_character_config("default")
        self.character_calls = []

    def decide(self, **kwargs):
        self.character_calls.append(self.character.character_id)
        return super().decide(**kwargs)


def test_two_characters_use_separate_state_and_selected_prompt():
    store = FakeStore()
    llm = CharacterRecordingLLM()
    with TestClient(create_app(repository=store, llm_service=llm)) as client:
        yui = client.post("/api/session", json={}).json()
        yui_turn = {**yui, "message": "유이 안녕", "client_turn_id": "yui-1"}
        assert client.post("/api/chat", json=yui_turn).status_code == 200

        cartethyia = client.post("/api/session", json={
            "profile_id": yui["profile_id"], "character_id": "cartethyia",
        }).json()
        cartethyia_turn = {**cartethyia, "character_id": "cartethyia",
                           "message": "띳띠 안녕", "client_turn_id": "cartethyia-1"}
        assert client.post("/api/chat", json=cartethyia_turn).status_code == 200

        assert llm.character_calls == ["default", "cartethyia"]
        assert store.load(yui["profile_id"], "default").history[0]["content"] == "유이 안녕"
        assert store.load(yui["profile_id"], "cartethyia").history[0]["content"] == "띳띠 안녕"

        wrong_room = client.get("/api/conversation", params={
            **yui, "character_id": "cartethyia",
        })
        assert wrong_room.status_code == 409

        reset = client.post("/api/conversation/reset", json={
            **cartethyia, "character_id": "cartethyia",
        })
        assert reset.status_code == 200
        assert store.load(yui["profile_id"], "default").turn_count == 1
        assert store.load(yui["profile_id"], "cartethyia").turn_count == 0


def test_character_selection_rejects_unknown_and_invalid_ids():
    store = FakeStore()
    with TestClient(create_app(repository=store, llm_service=FakeLLM())) as client:
        unknown = client.post("/api/session", json={"character_id": "unknown"})
        invalid = client.post("/api/session", json={"character_id": "../default"})
        assert unknown.status_code == 404
        assert unknown.json()["error"]["code"] == "CHARACTER_NOT_FOUND"
        assert invalid.status_code == 422


def test_cartethyia_prompt_has_distinct_identity_and_dialogue_rules():
    yui = load_character_config("default")
    cartethyia = load_character_config("cartethyia")
    assert cartethyia.display_name == "띳띠"
    assert "리나시타" in cartethyia.system_prompt
    assert "유랑" not in yui.system_prompt
    assert "자연스러운 해요체" in cartethyia.dialogue_prompt
    assert "본명은 카르티시아" in cartethyia.identity_prompt
    assert "별명은 띳띠" in cartethyia.identity_prompt
    assert "특별한 호칭 없이" in cartethyia.dialogue_prompt
    assert "사용자가 먼저 꺼내지 않았다면" in cartethyia.dialogue_prompt
    assert "한 가지 구체적인 선택" in cartethyia.dialogue_prompt
    assert "배경 설정" in cartethyia.identity_prompt
    assert "설정어·비유를 끼워 넣지 마" in cartethyia.dialogue_prompt
    assert "검 대신" not in cartethyia.system_prompt
    assert "기사담" not in cartethyia.system_prompt
    assert yui.grounded_recall_template.endswith("라고 했어.")
    assert cartethyia.grounded_recall_template.endswith("라고 했어요.")
