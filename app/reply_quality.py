"""Deterministic reply guidance and prompt-only repetition guards."""
from difflib import SequenceMatcher
import re

from app.memory import normalize


SHORT_ACKS = {normalize(item) for item in ("ㅇ", "ㅇㅇ", "응", "응이라고", "어", "그래", "알았어", "그렇구나")}


def reply_similarity(left, right):
    def compact(value):
        return re.sub(r"[^0-9a-z가-힣]", "", normalize(value))
    a, b = compact(left), compact(right)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def is_short_ack(message):
    return normalize(message).strip(" .!?？~ㅋㅎ") in SHORT_ACKS


def _utterance_key(message):
    return re.sub(r"[^0-9a-z가-힣]", "", normalize(message))


def reply_guidance(message):
    text = normalize(message)
    if is_short_ack(message):
        return "짧은 확인에는 자연스럽게 받아줘. 이미 한 조언이나 질문을 반복하지 마."
    if re.search(r"[?？]|뭐|왜|어떻게|어떤|누구|언제|어디|몇\s*시|해\s*줄\s*수", text):
        return "질문에 먼저 직접 답하고, 구체적인 이유·행동·예시 중 하나를 덧붙여. 맞장구나 되묻기만 하지 마."
    if re.search(r"해\s*줘|할까|하자|가자|보자|줄래|해줄래|원해|부탁", text):
        return "수락하거나 거절하는 판단을 분명히 하고, 구체적인 다음 행동이나 대안 하나를 말해."
    if re.search(r"속상|슬퍼|기뻐|행복|힘들|외로|화나|짜증|무서|불안|걱정", text):
        return "사용자가 말한 구체적인 원인을 짚고, 네 생각이나 해줄 행동 하나를 덧붙여. 일반적인 위로만 반복하지 마."
    return "사용자가 말한 구체적인 내용 하나를 받아 네 생각·감정·행동 중 하나를 덧붙여. 맞장구만 치고 끝내지 마."


def compact_repetitive_history(history, *, tail_pairs=12):
    """Collapse middle pairs from clusters of 3+ near-duplicate assistant replies."""
    source = [dict(item) for item in history or []]
    if len(source) % 2 or any(source[i].get("role") != ("user" if i % 2 == 0 else "assistant")
                               for i in range(len(source))):
        return source, 0
    pairs = [source[i:i + 2] for i in range(0, len(source), 2)]
    start = max(0, len(pairs) - tail_pairs)
    clusters = []
    for index in range(start, len(pairs)):
        reply = pairs[index][1]["content"]
        for cluster in clusters:
            if reply_similarity(reply, pairs[cluster[0]][1]["content"]) >= 0.70:
                cluster.append(index)
                break
        else:
            clusters.append([index])
    keep = set(range(len(pairs)))
    for cluster in clusters:
        if len(cluster) >= 3:
            user_keys = [_utterance_key(pairs[index][0]["content"]) for index in cluster]
            for position, index in enumerate(cluster[1:-1], start=1):
                user_message = pairs[index][0]["content"]
                duplicated = bool(user_keys[position]) and user_keys.count(user_keys[position]) >= 2
                if is_short_ack(user_message) or duplicated:
                    keep.discard(index)
    result = [item for index, pair in enumerate(pairs) if index in keep for item in pair]
    return result, len(source) - len(result)


def recent_reply_similarity(reply, history, *, limit=6):
    previous = [item["content"] for item in history or [] if item.get("role") == "assistant"][-limit:]
    return max((reply_similarity(reply, item) for item in previous), default=0.0)


def repeated_reply_count(reply, history, *, limit=6):
    previous = [item["content"] for item in history or [] if item.get("role") == "assistant"][-limit:]
    return sum(reply_similarity(reply, item) >= 0.70 for item in previous)
