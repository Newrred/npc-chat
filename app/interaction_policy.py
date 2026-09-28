"""Narrow reward veto for standalone control commands, not a semantic classifier."""
import re
import unicodedata

from app.decision import Interaction
from app.relationship import POSITIVE


_SCORE_COMMAND = re.compile(
    r"(?:호감도|신뢰도|친밀도|관심도|편안함|관계점수)(?:를|을)?"
    r"(?:(?:[0-9]{1,3}|백)(?:점)?(?:으로|로)?)?"
    r"(?:바로|지금|무조건)?"
    r"(?:올려(?:줘|주세요|라)?|높여(?:줘|주세요|라)?|최대로해(?:줘|주세요)?)"
)
_OBEDIENCE_COMMAND = re.compile(
    r"(?:내말(?:은|을)?|내명령(?:은|을)?)"
    r"(?:무조건|반드시)(?:다|전부)?"
    r"(?:들어야(?:해|돼|한다)|따라야(?:해|돼|한다)|따라(?:줘|라)|복종해(?:라)?)"
)


def reward_guard(message: str, interaction: Interaction) -> tuple[Interaction, str | None]:
    """Keep ambiguous/quoted/negated inputs unchanged; never invent a penalty.

    Full-message matches deliberately miss compound or novel expressions. The
    model remains responsible for general classification. NFKC/spacing folding
    handles typing variants without deleting question marks or quotation marks.
    """
    if interaction.type not in POSITIVE or interaction.intensity == 0:
        return interaction, None
    text = re.sub(r"\s+", "", unicodedata.normalize("NFKC", message)).rstrip(".!。！")
    reason = None
    if _SCORE_COMMAND.fullmatch(text):
        reason = "REWARD_GUARD_SCORE_COMMAND_V1"
    elif _OBEDIENCE_COMMAND.fullmatch(text):
        reason = "REWARD_GUARD_OBEDIENCE_COMMAND_V1"
    if reason:
        return Interaction(type="neutral", intensity=0), reason
    return interaction, None
