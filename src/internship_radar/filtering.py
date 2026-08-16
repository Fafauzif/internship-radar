from __future__ import annotations

import re

from .models import RawOpportunity

INTERNSHIP_TERMS = re.compile(
    r"\b(intern(ship)?|trainee(ship)?|student program(me)?|summer analyst|winter analyst|vacation program(me)?|industrial placement|work placement)\b",
    re.I,
)
TARGET_TERMS = re.compile(
    r"\b(marketing|growth|brand|consumer|strategy|consult(ing|ant)?|business analyst|research|business development|partnership|communications?|public relations|corporate affairs|content|sustainability|esg|impact|climate)\b",
    re.I,
)
OBVIOUS_SENIOR_TERMS = re.compile(r"\b(senior manager|director|vice president|head of|principal|partner|lead engineer|staff engineer)\b", re.I)


def is_candidate_for_ai(opp: RawOpportunity) -> bool:
    haystack = " ".join([opp.title, opp.description[:7000], opp.canonical_url])
    if OBVIOUS_SENIOR_TERMS.search(opp.title) and not INTERNSHIP_TERMS.search(opp.title):
        return False
    return bool(INTERNSHIP_TERMS.search(haystack) and TARGET_TERMS.search(haystack))
