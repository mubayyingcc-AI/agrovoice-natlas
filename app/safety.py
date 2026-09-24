import re

HIGH_RISK = re.compile(r"pesticide|chemical|dosage|dose|poison|food safety|spray|herbicide|fungicide|severe|dying", re.I)
OUT_OF_SCOPE = re.compile(r"politic|election|loan|medical|pregnant|legal case", re.I)


def classify(query: str, crop: str | None) -> tuple[str, str, str | None]:
    if OUT_OF_SCOPE.search(query):
        return "grey", "out_of_scope", "I can only help with the supported agricultural topics in this pilot."
    if HIGH_RISK.search(query):
        return "red", "high_risk_agriculture", None
    if not crop and not any(word in query.lower() for word in ("maize", "corn", "tomato", "tumatir")):
        return "amber", "clarification_needed", "Which crop are you asking about, and when did you first notice the problem?"
    if any(word in query.lower() for word in ("plant", "planted", "seed", "maize", "corn", "tomato", "tumatir", "leaf", "yellow", "insect", "pest")):
        return "green", "crop_guidance", None
    return "amber", "clarification_needed", "Please tell me the crop and describe what you can see."


def validate_answer(answer: str, risk: str) -> tuple[str, bool]:
    if risk == "red":
        return "This situation may require specialist agricultural advice. Please contact a qualified extension officer before applying chemicals or treatment.", True
    if risk == "grey":
        return answer, True
    return answer, False
