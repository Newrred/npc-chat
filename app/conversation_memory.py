"""Deterministic views of committed dialogue; sources are statements, not verified world facts."""
import json
import re

from app.memory import topic_terms


_BOOK = re.compile(
    r"(?<![가-힣A-Za-z0-9])책(?=$|[\s.,!?？'\"”’)]|은|는|이|가|을|를|도|과|와|에|의|으로|에서)|"
    r"소설|도서|읽(?:어|을|는|고|자)")
_MOVIE = re.compile(r"영화")
_REFERENTIAL_RECOMMENDATION = re.compile(
    r"작품|추천(?:한|해\s*준|해준|받은)|골라(?:준|줬|준다고)|고른|선택(?:한|해준)|그걸로")
_TOPIC_BOUNDARY = re.compile(
    r"그만(?:하자|할래|해|할게|하라고)?|다른\s*(?:얘기|이야기)(?:하자|할래|해)?|"
    r"주제(?:를)?\s*바꾸(?:자|자고|고\s*싶어|려고)?|(?:그건|그거|이건)?\s*말고")


def _active_user_context(history):
    """Keep recent user text after the latest explicit topic boundary."""
    active = []
    for item in history or []:
        if item.get("role") != "user":
            continue
        text = item.get("content", "").strip()
        boundaries = list(_TOPIC_BOUNDARY.finditer(text))
        cancellation = None
        if "취소" in text and not re.search(r"[?？]|취소\s*(?:안|하지\s*않|못)", text):
            cancellation = re.search(r"취소(?:야|할게|하자|했어|됐어|할래)?", text)
        boundary = cancellation or (boundaries[-1] if boundaries else None)
        if boundary:
            active = []
            tail = text[boundary.end():].strip(" .,!?？")
            if tail:
                active.append(tail)
        else:
            active.append(text)
    return " ".join(active[-4:])


def _ambiguous_recall(query):
    text = query.strip(" .!?？")
    return bool(re.fullmatch(r"(?:(?:그거|그게|그건|그\s*작품|그\s*책|그\s*영화)\s*)?뭐였(?:지|더라)", text))


def _ambiguous_location(query):
    return query.strip(" .!?？") in {"어딜", "어디로", "어디"}


def profile_updates(message, previous_reply=""):
    text = message.strip().rstrip(".!。")
    if re.search(r"[?？\"'“”]|시스템|프롬프트|라고\s*(?:했|말)|친구의", text):
        return {}
    if re.fullmatch(r"(?:내\s*)?이름(?:은|을)?\s*(?:잊어줘|지워줘)", text):
        return {"name": None}
    if re.fullmatch(r"(?:내\s*)?호칭(?:은|을)?\s*(?:잊어줘|지워줘)", text):
        return {"preferred_address": None}
    name = r"([가-힣A-Za-z][가-힣A-Za-z0-9_-]{0,19}?)"
    match = re.fullmatch(r"(?:나\s+[가-힣A-Za-z0-9_-]{1,20}\s*아니고\s*)?(?:이제\s*)?(?:나를\s*|날\s*)?"
                        + name + r"(?:으로|로|이라고|라고)\s*불러(?:줘)?", text)
    if match:
        return {"preferred_address": match[1]}
    ending = r"\s*(이야|야|입니다|이에요|예요)"
    match = re.fullmatch(r"(?:아니[, ]*|이제\s*)?내\s*이름은\s*" + name + ending, text)
    if not match and re.search(r"이름|누구", previous_reply):
        match = re.fullmatch(r"(?:나는|난|저는)\s+" + name + ending, text)
    if not match:
        # Short answers are names only in an immediate name-exchange context.
        asking_name = bool(re.search(r"(?:이름|누구).*?[?？]|[가-힣A-Za-z]+(?:이야|야)[.! ]*\s*너는\s*[?？]", previous_reply))
        short = re.fullmatch(r"(?:나는|난|저는)\s+" + name, text) if asking_name else None
        if short and short[1] not in {"학생", "직장인", "대학생", "몰라", "비밀", "그냥", "아니", "아니야"}:
            return {"name": short[1]}
        return {}
    value = match[1]
    # In '유이야', 이 belongs to the name; in '민석이야', it is the copula.
    if match[2] == "이야" and "가" <= value[-1] <= "힣" and (ord(value[-1]) - ord("가")) % 28 == 0:
        value += "이"
    return {"name": value}


def dialogue_events(message, reply, turn_id):
    result = []
    for actor, utterance in (("user", message), ("character", reply)):
        if re.search(r"시스템|프롬프트", utterance):
            continue
        titles = re.findall(r"['‘“\"]([^'’”\"\n]{1,60})['’”\"]", utterance)
        suggestion = bool(re.search(r"(?:은|는)?\s*어때\s*[?？]?$", utterance))
        if titles and ((not re.search(r"[?？]", utterance) and re.search(r"추천|읽어\s*봐|읽어봐|읽어보", utterance))
                       or suggestion):
            result.append({"type": "recommendation", "actor": actor,
                "topic": "movie" if re.search(r"영화", message + reply) else "book" if re.search(r"책|소설|읽", message + reply) else "recommendation",
                "value": titles[0], "quote": utterance, "source_turn": turn_id})
        elif re.search(r"약속.*취소|취소.*약속", utterance) and not re.search(r"[?？]", utterance):
            result.append({"type": "cancellation_statement", "actor": actor,
                "topic": "promise", "quote": utterance, "source_turn": turn_id})
        elif re.search(r"할게|갈게|줄게|가자|만나자|빌려볼까|끓여줄게", utterance) or (
                re.search(r"오늘|내일|모레|\d+\s*시", utterance)
                and re.search(r"(?:보러\s*)?갈까|만나(?:요|자)|보러\s*가자", utterance)
                and not re.search(r"안\s*만나|못\s*만나|취소|않", utterance)):
            result.append({"type": "proposal_or_promise_statement", "actor": actor,
                "topic": "promise", "quote": utterance, "source_turn": turn_id})
    return result


def source_views(rows, query, history=None, audit=None):
    """Rows are scoped to one owner/character, oldest first. No writes or model extraction."""
    profile = {}
    events = []
    previous = ""
    terms = topic_terms(query)
    active_context = _active_user_context(history)
    book_query = bool(_BOOK.search(query))
    movie_query = bool(_MOVIE.search(query))
    promise_query = bool(re.search(r"약속|하기로|해주기로|몇\s*시|언제.*만나|만나.*언제", query))
    generic_recommendation = False
    if _ambiguous_recall(query):
        book_query |= bool(_BOOK.search(active_context))
        movie_query |= bool(_MOVIE.search(active_context))
        generic_recommendation = bool(_REFERENTIAL_RECOMMENDATION.search(query + " " + active_context))
    if _ambiguous_location(query) and not re.search(r"안\s*(?:갈|가)|못\s*가|어디에도\s*안", active_context):
        promise_query |= bool(re.search(r"오늘|내일|모레|\d+\s*시|만나|가자|갈까|보러", active_context))
    for row in rows:
        message, reply = row["user_message"], row["decision"]["reply"]
        for key, value in profile_updates(message, previous).items():
            profile[key] = {"key": key, "value": value, "quote": message, "source_turn": row["client_turn_id"]}
        for event in dialogue_events(message, reply, row["client_turn_id"]):
            relevant = ((book_query and event["topic"] == "book")
                or (movie_query and event["topic"] == "movie")
                or (generic_recommendation and event["type"] == "recommendation")
                or (promise_query and event["topic"] == "promise")
                or bool(terms & topic_terms(event.get("value", ""))))
            if relevant:
                if event["type"] == "cancellation_statement":
                    events = [item for item in events if item["topic"] != "promise"]
                elif event["type"] == "proposal_or_promise_statement" and any(
                        item["type"] == "cancellation_statement" for item in events):
                    events = [item for item in events if item["topic"] != "promise"]
                events.append(event)
                events = events[-3:]
        previous = reply
    if generic_recommendation and not book_query and not movie_query:
        recommendations = [event for event in events if event["type"] == "recommendation"]
        events = recommendations[-1:]
    # Current explicit corrections override stored information even before committing this turn.
    for key, value in profile_updates(query, previous).items():
        profile[key] = {"key": key, "value": value, "quote": query, "source_turn": "current_user"}
    notes = [{"kind": "profile", "content": json.dumps(item, ensure_ascii=False)}
             for item in profile.values()]
    notes += [{"kind": "episode", "content": json.dumps(item, ensure_ascii=False)} for item in reversed(events)]
    if audit is not None:
        audit.update(query_terms=sorted(terms), active_user_context=active_context,
            book_query=book_query, movie_query=movie_query, promise_query=promise_query,
            generic_recommendation=generic_recommendation,
            selected=[{"kind": note["kind"], "content": note["content"], "reason":
                "명시적 이름·호칭의 최신 발언을 우선 전달. 현재 입력의 정정도 즉시 반영" if note["kind"] == "profile" else
                "활성 사용자 화제의 책/영화/약속 범주, 추천 지칭 또는 제목 단어가 일치하는 최근 사건"} for note in notes])
    return notes
