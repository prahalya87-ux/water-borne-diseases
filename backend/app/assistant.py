"""Rule-based WaterGuard Assistant. Works with no API key: answers come from a curated knowledge base.
It never diagnoses, never invents local conditions, and sends emergencies to emergency care first."""
import re

DISCLAIMER = ("WaterGuard Assistant gives general information and cannot diagnose illness. It does not replace a doctor, "
              "official advisories or laboratory testing.")
LINKS = {
    "report": {"label": "Report contaminated water", "to": "/report"}, "quality": {"label": "Water quality checker", "to": "/water-quality"},
    "map": {"label": "Find nearby hospitals", "to": "/map"}, "alerts": {"label": "View alerts", "to": "/alerts"},
    "track": {"label": "Track a report", "to": "/track"},
}
EMERGENCY_WORDS = ["blood in stool", "bloody stool", "bloody diarrh", "unconscious", "seizure", "convuls", "cannot keep", "can't keep",
                   "not drinking", "very sleepy", "sunken eyes", "no urine", "severe dehydration", "difficulty breathing",
                   "very little urine", "little to no urine", "unable to drink", "cannot drink", "can't drink",
                   "can't breathe", "cannot breathe", "chest pain", "fainted", "passed out", "yellow eyes and confus"]
EMERGENCY_ANSWER = ("This could be a medical emergency. Call your local emergency number (112 in India) or go to the nearest hospital now. "
                    "Do not wait for test results or for a report to be reviewed. Babies, young children, older adults and pregnant women "
                    "can become seriously dehydrated quickly. While arranging care, sip oral rehydration solution if the person is awake and able to drink.")

KB = [
    {"id": "contaminated_source", "kw": ["contaminat", "unsafe water", "dirty water", "smell", "colour", "color", "cloudy", "precaution", "my water", "water source"],
     "answer": ("If your water source may be contaminated: (1) use another source known to be safe for drinking, cooking and brushing teeth; "
                "(2) if you have none, bring water to a rolling boil for at least 1 minute (3 minutes at altitudes above 2,000 m) and let it cool in a clean, covered container; "
                "(3) if the water is cloudy, let it settle and strain it through clean cloth before boiling; "
                "(4) keep treated water covered and take it out with a clean ladle or a tap, not by dipping hands. "
                "Boiling kills germs but does not remove chemicals. Looks and smell cannot prove water is safe or unsafe: only a laboratory test can. "
                "Please report it so staff can review."), "links": ["report", "quality"]},
    {"id": "interpret_report", "kw": ["interpret", "report mean", "test result", "lab report", "tds", "turbidity", "chlorine", "ph value", "e. coli", "ecoli", "water quality"],
     "answer": ("To read a water-quality report, compare each value with the guideline: Indian standard IS 10500:2012 lists pH 6.5 to 8.5, turbidity up to 1 NTU (5 NTU only if no better source), "
                "TDS up to 500 mg/L (2,000 only if no better source), free residual chlorine 0.2 to 1.0 mg/L for chlorinated supplies, and E. coli must not be detectable in 100 mL. "
                "Low TDS or a normal pH does not prove water is safe, because germs are not measured by those values. The checker on the Water Quality page compares your numbers for you."),
     "links": ["quality"]},
    {"id": "symptoms", "kw": ["symptom", "signs", "typhoid", "cholera", "hepatitis", "jaundice", "fever", "waterborne illness", "water borne illness", "sick from water"],
     "answer": ("Common signs of water-related illness include diarrhoea, vomiting, stomach cramps and fever. Cholera typically causes frequent, very watery diarrhoea; typhoid causes a fever that lasts for days; "
                "hepatitis A and E can cause tiredness, dark urine and yellow skin or eyes. I cannot tell which illness someone has: a doctor and tests are needed. "
                "See a doctor soon for diarrhoea lasting more than 2 days, fever, or any illness in babies, older adults or pregnant women. Go to a hospital urgently for blood in stool, "
                "constant vomiting, severe weakness, very little urine, or confusion."), "links": ["map"]},
    {"id": "cholera_prevention", "kw": ["cholera", "prevent", "prevention", "precaution", "avoid"],
     "answer": ("To reduce cholera risk, drink water from a safe source or boil it at a rolling boil for at least 1 minute; store it covered in a clean container. "
                "Wash hands with soap after using the toilet and before preparing or eating food, eat freshly cooked food, and use safe water for washing produce and making ice. "
                "If you have sudden frequent watery diarrhoea, start packet ORS mixed exactly as directed and seek urgent medical care; symptoms cannot confirm cholera. "
                "Follow local health-authority advice during an outbreak, and do not self-start antibiotics."), "links": ["alerts", "map"]},
    {"id": "typhoid_prevention", "kw": ["typhoid", "prevent", "prevention", "precaution", "avoid"],
     "answer": ("To reduce typhoid risk, drink safe or boiled water, eat freshly cooked food, avoid unsafe ice and raw food washed with unsafe water, and wash hands with soap after using the toilet and before eating or preparing food. "
                "Typhoid vaccination may be appropriate; ask a clinician or local health centre. A fever lasting several days needs medical assessment and testing. "
                "Do not self-medicate with antibiotics, because resistance varies."), "links": ["map"]},
    {"id": "hepatitis_prevention", "kw": ["hepatitis", "prevent", "prevention", "precaution", "avoid"],
     "answer": ("To reduce hepatitis A and E risk, use safe drinking water, wash hands with soap after using the toilet and before handling food, and eat food that is freshly cooked and safely handled. "
                "Hepatitis A vaccination is available; ask a clinician whether it is suitable. Hepatitis E can be more severe during pregnancy, so seek prompt medical advice for jaundice or dark urine, especially if pregnant. "
                "Yellow eyes, dark urine or pale stools need medical assessment; symptoms alone cannot identify the cause."), "links": ["map"]},
    {"id": "diarrhoea_care", "kw": ["diarrhoea", "diarrhea", "loose motion", "loose stool", "ors", "dehydrat", "vomit", "stomach upset"],
     "answer": ("For diarrhoea, the main danger is dehydration. Give oral rehydration solution (ORS) made exactly as the packet says, in small frequent sips, and keep feeding normally. "
                "Use safe, boiled-and-cooled water to mix ORS. Do not give medicines such as antibiotics or anti-diarrhoea tablets unless a doctor advises it. "
                "Get medical care early for children, older adults and pregnant women, or if there is blood in the stool, high fever, or the person cannot drink."), "links": ["map"]},
    {"id": "report_how", "kw": ["how do i report", "how to report", "report contaminated", "submit report", "complain", "report water"],
     "answer": ("Open the Report page, choose the problem (colour, smell, visible contamination, or several people sick), the water source, and where it is (area, PIN code or your location). "
                "You can add a photo. You will get a report ID to track it. Reports start as Unverified until authorised staff review them."), "links": ["report", "track"]},
    {"id": "hospitals", "kw": ["hospital", "clinic", "doctor", "health centre", "health center", "nearby care", "where can i get treated"],
     "answer": ("The Map page can show hospitals and clinics near a place you search or your location (only if you allow it), with distance and a directions link. "
                "Contact details are shown only when available, so please phone ahead when you can."), "links": ["map"]},
    {"id": "advisory", "kw": ["advisory", "boil water notice", "local alert", "official alert", "what should i do during"],
     "answer": ("During a local water-safety advisory: follow the instructions in the advisory itself, avoid using the affected water for drinking, brushing teeth, ice or washing food until authorities say it is safe, "
                "boil or use safe water, and check the Alerts page and your local water authority for updates."), "links": ["alerts"]},
    {"id": "handwashing", "kw": ["hand wash", "handwash", "wash hands", "hygiene", "sanitation"],
     "answer": ("Wash hands with soap and clean water for about 20 seconds after using the toilet, after cleaning a child, and before preparing or eating food. "
                "Keep drinking water covered, and keep toilets and drains away from water sources."), "links": []},
    {"id": "flood", "kw": ["flood", "rain", "monsoon", "waterlogging"],
     "answer": ("After floods: treat all water as unsafe until authorities say otherwise. Boil drinking water, throw away food that touched floodwater, clean and disinfect storage containers, "
                "and avoid wading through floodwater with cuts. Rain or floods alone do not prove a particular well or tap is contaminated, but they raise the risk, so testing helps."), "links": ["alerts", "quality"]},
    {"id": "treatment", "kw": ["purify", "treat water", "filter", "chlorine tablet", "uv", "household treatment", "make water safe"],
     "answer": ("Household options: boiling is the most reliable for germs. Chlorine tablets or drops work if used exactly as the product label says and the water is clear first. "
                "Some filters and UV devices remove germs but not all do, so check what the product is certified for. None of these remove every chemical, and home methods do not replace laboratory testing."), "links": ["quality"]},
    {"id": "vulnerable", "kw": ["baby", "infant", "child", "pregnan", "elderly", "old people", "vulnerable"],
     "answer": ("Babies, young children, older adults, pregnant women and people with weak immunity can become seriously ill faster. Use safe water for formula and food, wash hands, "
                "and seek medical care early for diarrhoea, vomiting or fever in these groups."), "links": ["map"]},
]
FALLBACK = ("I don't have a specific answer for that. I can help with: what to do if your water may be contaminated, how to read a water-quality report, "
            "signs of water-related illness, how to report a problem, finding nearby hospitals, and what to do during an advisory. "
            "For health worries, please talk to a doctor.")

SYMPTOM_PROFILES = [
    {
        "id": "possible_cholera",
        "primary": ["watery diarrhoea", "watery diarrhea", "rice-water stool", "rice water stool", "very watery stool"],
        "support": ["vomit", "thirst", "dry mouth", "sunken eyes", "little urine", "leg cramp"],
        "answer": ("Sudden frequent, very watery diarrhoea with vomiting or dehydration can be seen with cholera, but it can also have other causes and symptoms cannot confirm it. "
                   "Start packet ORS mixed exactly as directed, use safe water, and seek urgent medical care now; severe dehydration can worsen quickly. "
                   "Call emergency services for confusion, fainting, inability to drink, or very little/no urine."),
    },
    {
        "id": "possible_typhoid",
        "primary": ["fever for days", "fever lasting", "fever for a week", "fever for several days", "fever since"],
        "support": ["stomach pain", "abdominal pain", "headache", "weakness", "loss of appetite"],
        "answer": ("A fever lasting several days together with stomach pain, headache or marked weakness can be seen with typhoid, but many illnesses cause these symptoms. "
                   "Symptoms cannot confirm typhoid; a clinician must assess and test to identify the cause. Arrange medical care promptly, drink safe fluids, and do not take antibiotics unless prescribed."),
    },
    {
        "id": "possible_hepatitis",
        "primary": ["yellow eyes", "eyes are yellow", "eyes look yellow", "yellow skin", "skin is yellow", "jaundice", "dark urine", "pale stool", "pale stools"],
        "support": ["tired", "fatigue", "nausea", "loss of appetite", "stomach pain", "fever"],
        "answer": ("Yellow eyes or skin, dark urine or pale stools can be signs of liver inflammation, including hepatitis A or E, but other causes are possible. "
                   "Symptoms alone cannot identify the cause. "
                   "Please get medical assessment promptly and avoid alcohol and unprescribed medicines until advised. Seek urgent care for confusion, severe drowsiness, bleeding or constant vomiting. "
                   "If pregnant, seek medical advice urgently."),
    },
]


def _symptom_guidance(text: str) -> dict | None:
    for profile in SYMPTOM_PROFILES:
        primary_matches = sum(term in text for term in profile["primary"])
        if profile["id"] == "possible_typhoid" and re.search(r"\bfever(?:\s+for)?\s+(?:[3-9]|\d{2,})\s+days?\b", text):
            primary_matches += 1
        has_support = any(term in text for term in profile["support"])
        if primary_matches >= 2 or (primary_matches and has_support):
            return {
                "answer": profile["answer"],
                "emergency": False,
                "topic": profile["id"],
                "links": [LINKS["map"]],
            }
    return None


def reply(message: str) -> dict:
    text = re.sub(r"\s+", " ", message.lower())
    if any(w in text for w in EMERGENCY_WORDS):
        return {"answer": EMERGENCY_ANSWER, "emergency": True, "topic": "emergency", "links": [LINKS["map"]]}
    symptom_answer = _symptom_guidance(text)
    if symptom_answer:
        return symptom_answer
    best, best_score = None, 0
    for e in KB:
        s = sum(1 for k in e["kw"] if k in text)
        if s > best_score:
            best, best_score = e, s
    if not best:
        return {"answer": FALLBACK, "emergency": False, "topic": "fallback", "links": []}
    return {"answer": best["answer"], "emergency": False, "topic": best["id"], "links": [LINKS[k] for k in best["links"]]}