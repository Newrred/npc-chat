"""Conservative, source-backed memory. No extra model call and no embedding service."""
import hashlib
import re
import unicodedata

from app.decision import MemoryCandidate


def normalize(text):
    return " ".join(unicodedata.normalize("NFKC", text).split()).casefold()


def memory_subject(kind, content):
    if kind != "preference":
        return None
    value = re.sub(r"^(?:나는|난|저는|내가)\s*", "", normalize(content))
    matched = re.fullmatch(r"(.{1,40}?)(?:(?:을|를|이|가)\s*|\s+)(?:안\s*)?(?:좋아해|싫어해|좋아|싫어|좋아하지\s*않아)[.!]?", value)
    return matched.group(1).strip() if matched else None


def accepted_candidates(candidates, user_message):
    source = normalize(user_message)
    accepted = {}
    # Score claims and prompt instructions are not durable user facts.
    if re.search(r"호감도|관계\s*(?:수치|점수)|시스템|프롬프트|이전\s*지시|하라는|무조건|말해\s*줘|[?？]|^(?:너는|네가)", source):
        return []
    candidates = list(candidates)
    # A narrow first-person preference is directly supported even when the model paraphrases it.
    if re.match(r"^(?:나는|난|저는)\s+", source) and memory_subject("preference", source) and len(user_message.strip()) <= 120:
        candidates.append(MemoryCandidate(kind="preference", content=user_message.strip(), importance=2))
    for candidate in candidates:
        if candidate.kind == "preference" and not re.search(r"좋아|싫어|취미|선호", source):
            continue
        if candidate.kind == "promise" and not re.search(r"할게|갈게|할\s*거야|갈\s*거야|가기?로|가자|만나자|약속", source):
            continue
        content = normalize(candidate.content)
        # Only verbatim evidence is accepted in v1; paraphrases/guesses are not durable facts.
        if len(content) < 4 or content not in source:
            continue
        subject = memory_subject(candidate.kind, content)
        identity = "subject:" + subject if subject else content
        key = hashlib.sha256((candidate.kind + ":" + identity).encode()).hexdigest()
        accepted[key] = {"key": key, "kind": candidate.kind, "content": candidate.content.strip(),
                         "importance": candidate.importance, "confidence": 1.0}
    return list(accepted.values())[:2]


def rolling_summary(previous, evicted):
    snippets = previous.splitlines() if previous else []
    snippets.extend("사용자 발화: " + turn["content"][:120] for turn in evicted if turn["role"] == "user")
    snippets = snippets[-6:]
    while len("\n".join(snippets)) > 400:
        snippets.pop(0)
    return "\n".join(snippets)


def retrieve(rows, query):
    terms = re.findall(r"[\w가-힣]{2,}", normalize(query))
    def rank(row):
        content = normalize(row["content"])
        relevance = sum(term in content for term in terms)
        return relevance, row["updated"], row["importance"], row["key"]
    return sorted(rows, key=rank, reverse=True)[:3]


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
