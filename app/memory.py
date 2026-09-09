"""Conservative, source-backed memory. No extra model call and no embedding service."""
import hashlib
import re
import unicodedata

from app.decision import MemoryCandidate


def normalize(text):
    return " ".join(unicodedata.normalize("NFKC", text).split()).casefold()


def preference_statement(content):
    """Recognize one direct Korean preference, not arbitrary facts or reported speech."""
    value = normalize(content)
    if re.search(r"[?？\"'“”‘’]|(?:친구|엄마|아빠|동생|언니|오빠|누나|형|너|네가|유이)(?:는|가|도|의)?\s", value):
        return None
    value = re.sub(r"^(?:나는|난|저는|내가)\s+", "", value)
    value = re.sub(r"^(?:이제는|이제|지금은|사실은|사실)\s+", "", value)
    matched = re.fullmatch(
        r"([\w가-힣]{1,30}(?:\s+[\w가-힣]{1,20}){0,2}?)(?:을|를|이|가|은|는)\s*"
        r"(?:(이제는|이제|지금은)\s+)?(안\s*좋아해(?:요)?|좋아하지\s*않아(?:요)?|좋아해(?:요)?|싫어해(?:요)?|좋아|싫어)[.!]?",
        value)
    if not matched:
        # Common particle-free short form: "커피 싫어해".
        matched = re.fullmatch(
            r"([\w가-힣]{1,30})\s+(?:(이제는|이제|지금은)\s+)?"
            r"(안\s*좋아해(?:요)?|좋아하지\s*않아(?:요)?|좋아해(?:요)?|싫어해(?:요)?|좋아|싫어)[.!]?", value)
    if not matched:
        return None
    subject = matched.group(1).strip()
    if re.search(r"\S+(?:은|는|가)\s|^(?:너|나|그거|이거|걔)$", subject):
        return None
    stance = "negative" if re.search(r"안|않|싫", matched.group(3)) else "positive"
    return subject, stance


def memory_subject(kind, content):
    parsed = preference_statement(content) if kind == "preference" else None
    return parsed[0] if parsed else None


def contradicts_preference(content, current):
    old = preference_statement(content)
    new = preference_statement(current)
    return bool(old and new and old[0] == new[0] and old[1] != new[1])


def accepted_candidates(candidates, user_message, audit=None):
    source = normalize(user_message)
    accepted = {}
    candidates = list(candidates)
    def record(candidate, origin, reason, key=None):
        if audit is not None:
            audit.append({"candidate": candidate.model_dump(), "origin": origin, "reason": reason, "key": key})
    # Score claims and prompt instructions are not durable user facts.
    if re.search(r"호감도|관계\s*(?:수치|점수)|시스템|프롬프트|이전\s*지시|하라는|무조건|말해\s*줘|[?？]|^(?:너는|네가)", source):
        for candidate in candidates:
            record(candidate, "model", "입력이 질문·지시·점수 주장 등 보수적 제외 규칙에 해당")
        return []
    model_count = len(candidates)
    # A narrow first-person preference is directly supported even when the model paraphrases it.
    direct_preference = preference_statement(source)
    if direct_preference and len(user_message.strip()) <= 120:
        candidates.append(MemoryCandidate(kind="preference", content=user_message.strip(), importance=2))
    for index, candidate in enumerate(candidates):
        origin = "model" if index < model_count else "server_preference_rule"
        if direct_preference and preference_statement(candidate.content) == direct_preference:
            candidate = candidate.model_copy(update={"kind": "preference"})
        if candidate.kind == "preference" and (
                not direct_preference or preference_statement(candidate.content) != direct_preference):
            record(candidate, origin, "현재 사용자 발언에서 같은 취향을 명시적으로 확인하지 못함")
            continue
        if candidate.kind == "promise" and not re.search(r"할게|갈게|할\s*거야|갈\s*거야|가기?로|가자|만나자|약속", source):
            record(candidate, origin, "현재 사용자 발언에 약속 표현이 없음")
            continue
        content = normalize(candidate.content)
        # Only verbatim evidence is accepted in v1; paraphrases/guesses are not durable facts.
        if len(content) < 4 or content not in source:
            record(candidate, origin, "정규화한 내용이 4자 미만이거나 현재 사용자 발언의 원문에 없음")
            continue
        subject = memory_subject(candidate.kind, content)
        identity = "subject:" + subject if subject else content
        key = hashlib.sha256((candidate.kind + ":" + identity).encode()).hexdigest()
        accepted[key] = {"key": key, "kind": candidate.kind, "content": candidate.content.strip(),
                         "importance": candidate.importance, "confidence": 1.0}
        record(candidate, origin, "현재 사용자 발언의 원문 근거와 종류별 규칙 통과", key)
    if audit is not None:
        keys = list(accepted)[:2]
        for i, item in enumerate(audit):
            item["accepted"] = item["key"] in keys
            if item["key"] and any(x["key"] == item["key"] for x in audit[i+1:]):
                item["accepted"] = False
                item["reason"] = "같은 기억 키의 뒤 후보와 병합됨"
            elif item["key"] and item["key"] not in keys:
                item["reason"] = "한 번에 최대 2개 저장 한도에서 제외"
    return list(accepted.values())[:2]


def rolling_summary(previous, evicted):
    snippets = previous.splitlines() if previous else []
    snippets.extend("사용자 발화: " + turn["content"][:120] for turn in evicted if turn["role"] == "user")
    snippets = snippets[-6:]
    while len("\n".join(snippets)) > 400:
        snippets.pop(0)
    return "\n".join(snippets)


STOP_WORDS = frozenset("""나는 내가 저는 나 저 너 네가 너는 유이 사용자 사용자는
    오늘 요즘 어제 내일 지금 이제 이제는 사실 사실은 때문에 진짜 정말 너무 많이 조금
    좋아 좋아해 좋아해요 싫어 싫어해 싫어해요 좋아하지 않아 안 못 뭐 뭘 어떤 어떻게 왜
    기억 기억해 기억나 취향 취미 선호 다시 그거 그것 이거 이것 걔 얘 그애 그 그건 그게
    그럼 그러면 응 어 ㅇ ㅇㅇ 그래 그렇구나 잤어 잤어요 했어 했지 했어요 있어 없어
    알려줘 말해줘 때문 얘기 이야기 좋아하는 뭐였지 뭐였어
""".split())
PARTICLES = ("에게서", "한테서", "에서는", "으로는", "이라서", "때문에", "에서", "에게", "한테",
             "으로", "까지", "부터", "처럼", "하고", "이랑", "에는", "은", "는", "을", "를", "가", "도", "에", "랑")


def topic_terms(content):
    """Exact word/stem matches only; no substring match or semantic inference."""
    terms = set()
    for word in re.findall(r"[\w가-힣]+", normalize(content)):
        if word in STOP_WORDS:
            continue
        for suffix in PARTICLES:
            if word.endswith(suffix) and len(word) - len(suffix) >= 2:
                word = word[:-len(suffix)]
                break
        if len(word) >= 2 and word not in STOP_WORDS:
            terms.add(word)
    return terms


def retrieve(rows, query, history=None, audit=None):
    # Contradictory preferences are suppressed before generation, not just on commit.
    eligible = [row for row in rows if not contradicts_preference(row["content"], query)]
    terms = topic_terms(query)
    method = "현재 메시지 단어 일치"
    search_terms = terms
    def finish(selected, reason=""):
        if audit is not None:
            keys = {row["key"] for row in selected}
            audit.update(method=method, query_terms=sorted(terms), search_terms=sorted(search_terms), reason=reason,
                ranking="일치 단어 수 → 최근 갱신 → 중요도 → 키 순, 최대 3개",
                considered=[{"kind": row["kind"], "content": row["content"], "selected": row["key"] in keys,
                    "matched_terms": sorted(search_terms & topic_terms(row["content"])),
                    "contradicted": contradicts_preference(row["content"], query)} for row in rows])
        return selected
    def matching(search):
        return [(row, search & topic_terms(row["content"])) for row in eligible
                if search & topic_terms(row["content"])]
    matches = matching(terms)
    # An explicit category recall is relevant to that category, even without a noun.
    if not matches and not terms and re.search(r"내(?:가)?\s.*(?:취향|좋아|싫어)", normalize(query)):
        method = "사용자가 자신의 취향을 묻는 명시적 범주 검색"
        matches = [(row, {"preference"}) for row in eligible
                   if row["kind"] == "preference" and preference_statement(row["content"])]
    if not matches:
        # Only explicit continuations may borrow context. New topics never fall back
        # to an unrelated recent memory. Assistant-generated claims are not evidence.
        continuation = bool(re.search(r"(?:^|\s)(?:걔|얘|그거|그것|그애|그건|그게)(?:[가-힣]*)(?:\s|[?.!]|$)", normalize(query)))
        continuation |= normalize(query).strip(".!? ") in {"왜", "왜 그래", "ㅇㅇ", "응", "그랬구나", "그렇구나"}
        shifted = bool(re.search(r"그런데|근데|다른\s*(?:얘기|이야기)|말고", normalize(query)))
        if not continuation or shifted:
            return finish([], "일치 기억 없음. 이어지는 질문이 아니거나 화제 전환이어서 과거 문맥을 빌리지 않음")
        users = [item["content"] for item in (history or [])[-4:] if item["role"] == "user"]
        if not users:
            return finish([], "참고할 직전 사용자 발언 없음")
        # The nearest user utterance is the only fallback topic anchor in v1.
        method = "이어지는 질문이어서 가장 가까운 사용자 발언의 단어로 검색"
        search_terms = topic_terms(users[-1])
        matches = matching(search_terms)
        anchors = set().union(*(overlap for _, overlap in matches))
        if not matches or (len(matches) > 1 and len(anchors) != 1):
            return finish([], "이전 발언과 일치하지 않거나 대상이 모호함")
    matches.sort(key=lambda item: (len(item[1]), item[0]["updated"], item[0]["importance"], item[0]["key"]), reverse=True)
    return finish([row for row, _ in matches[:3]])


def grounded_preference_reply(query, memories):
    """Quote known user preferences for explicit recall questions, without inventing a paraphrase."""
    if not re.search(r"좋아|싫어|취향|기억", query) or not re.search(r"내가|나는|내\s|기억|했지|였지|였어", query):
        return None
    if not re.search(r"[?？]|뭐였|기억나|했지|였지|였어", query):
        return None
    choices = [item for item in memories or [] if memory_subject(item["kind"], item["content"])]
    named = [item for item in choices if memory_subject(item["kind"], item["content"]) in normalize(query)]
    if not named and not re.search(r"뭐|뭘|어떤|취향", query):
        return None
    choices = named or choices
    quotes = []
    for item in choices[:2]:
        quoted = item["content"].strip().rstrip(".")
        candidate = "네가 '" + " / ".join([*quotes, quoted]) + "'라고 했어."
        if len(candidate) <= 80:
            quotes.append(quoted)
    return "네가 '" + " / ".join(quotes) + "'라고 했어." if quotes else None
