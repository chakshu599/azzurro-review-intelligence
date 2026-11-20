from __future__ import annotations
import re

TOPICS = {
    "Cleanliness": ["dirty", "clean", "cleanliness", "spotless", "stain", "mould", "mold", "dust", "smell", "smelly", "bathroom", "towel"],
    "Check-in experience": ["check-in", "check in", "checkin", "arrival", "late", "delay", "waiting", "queue"],
    "Staff": ["staff", "reception", "receptionist", "friendly", "helpful", "rude", "unhelpful", "service"],
    "Noise": ["noise", "noisy", "loud", "sleep", "street", "traffic", "quiet"],
    "Facilities": ["lift", "elevator", "pool", "gym", "wifi", "internet", "air conditioning", "facilities", "parking"],
    "Location": ["location", "central", "walk", "walking", "transport", "train", "convenient", "near"],
    "Room condition": ["room", "bed", "linen", "broken", "maintenance", "dated", "small", "space", "shower"],
    "Value for money": ["price", "value", "expensive", "overpriced", "cost", "worth", "money"],
}
POSITIVE_HINTS = {"excellent","great","good","clean","spotless","friendly","helpful","comfortable","perfect","beautiful","convenient","quiet","amazing","wonderful","lovely","spacious","recommend"}
NEGATIVE_HINTS = {"dirty","bad","poor","terrible","awful","rude","unhelpful","noisy","loud","broken","dated","small","expensive","overpriced","slow","delay","dust","mould","smelly","disappointing","problem"}

def classify_topics(text: str | None) -> list[dict]:
    if not text:
        return []
    low = text.lower()
    words = set(re.findall(r"\b[\w'-]+\b", low))
    results=[]
    for topic, keywords in TOPICS.items():
        matched=[k for k in keywords if k in low]
        if matched:
            sentiment="neutral"
            if words & POSITIVE_HINTS: sentiment="positive"
            if words & NEGATIVE_HINTS: sentiment="negative"
            if any(k in low for k in ("not "+k for k in matched)): sentiment="negative"
            results.append({"topic":topic,"sentiment":sentiment,"keywords":matched[:5]})
    return results
