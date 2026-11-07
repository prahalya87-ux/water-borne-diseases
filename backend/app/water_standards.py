"""Drinking-water guideline checks. Pure Python (no DB/web deps) so it is easy to test.
Limits: BIS IS 10500:2012 (Second Revision), 'acceptable limit' and 'permissible limit in the absence of an
alternate source'; E. coli per BIS/WHO (not detectable in 100 mL). Always check bis.gov.in for newer editions.
This is a SCREENING aid. It never declares water 'safe': microbiological safety needs a laboratory test."""

BIS = "BIS IS 10500:2012 (Second Revision), Table 2/Table 1"
WHO = "WHO Guidelines for Drinking-water Quality"

STANDARDS = [
    {"parameter": "ph", "label": "pH", "unit": "pH units", "acceptable": "6.5 to 8.5", "permissible": "no relaxation",
     "source": BIS, "note": "pH alone says nothing about microbiological safety."},
    {"parameter": "turbidity_ntu", "label": "Turbidity", "unit": "NTU", "acceptable": "1", "permissible": "5",
     "source": BIS, "note": "WHO: ideally below 1 NTU so disinfection works well."},
    {"parameter": "tds_mg_l", "label": "Total dissolved solids", "unit": "mg/L", "acceptable": "500", "permissible": "2000",
     "source": BIS, "note": "WHO sets no health-based value for TDS (taste). A low TDS does NOT mean the water is safe."},
    {"parameter": "residual_chlorine_mg_l", "label": "Free residual chlorine", "unit": "mg/L", "acceptable": "0.2 (minimum)",
     "permissible": "1.0 (maximum)", "source": BIS + "; " + WHO + " (health-based value 5 mg/L)",
     "note": "Applies only to chlorinated supplies. Untreated borewell water normally has none."},
    {"parameter": "ecoli", "label": "E. coli / thermotolerant coliforms", "unit": "per 100 mL", "acceptable": "not detectable",
     "permissible": "no relaxation", "source": BIS + "; " + WHO, "note": "Needs a laboratory or validated test."},
]


def _r(parameter, label, value, unit, guideline, status, severity, message, source):
    return {"parameter": parameter, "label": label, "value": value, "unit": unit, "guideline": guideline,
            "status": status, "severity": severity, "message": message, "source": source}


def evaluate(ph=None, turbidity_ntu=None, tds_mg_l=None, residual_chlorine_mg_l=None, ecoli=None) -> dict:
    out = []
    g = "6.5 to 8.5 (no relaxation)"
    if ph is None:
        out.append(_r("ph", "pH", None, "", g, "not_provided", "unknown", "Not provided.", BIS))
    elif 6.5 <= ph <= 8.5:
        out.append(_r("ph", "pH", ph, "", g, "within_guideline", "ok", "Within the guideline range.", BIS))
    else:
        out.append(_r("ph", "pH", ph, "", g, "exceeds_limit", "caution",
                      "Outside 6.5-8.5. BIS allows no relaxation; can indicate acidic/alkaline contamination or corrosion.", BIS))

    g = "1 NTU acceptable, 5 NTU permissible"
    t = turbidity_ntu
    if t is None:
        out.append(_r("turbidity_ntu", "Turbidity", None, "NTU", g, "not_provided", "unknown", "Not provided.", BIS))
    elif t <= 1:
        out.append(_r("turbidity_ntu", "Turbidity", t, "NTU", g, "within_guideline", "ok", "Within the acceptable limit.", BIS))
    elif t <= 5:
        out.append(_r("turbidity_ntu", "Turbidity", t, "NTU", g, "above_acceptable_within_permissible", "caution",
                      "Above 1 NTU. Tolerable only if no better source exists; cloudy water makes disinfection less effective.", BIS))
    else:
        out.append(_r("turbidity_ntu", "Turbidity", t, "NTU", g, "exceeds_limit", "caution",
                      "Above the 5 NTU permissible limit. Water is too cloudy; find another source or filter and disinfect, then test.", BIS))

    g = "500 mg/L acceptable, 2000 mg/L permissible"
    v = tds_mg_l
    if v is None:
        out.append(_r("tds_mg_l", "TDS", None, "mg/L", g, "not_provided", "unknown", "Not provided.", BIS))
    elif v <= 500:
        out.append(_r("tds_mg_l", "TDS", v, "mg/L", g, "within_guideline", "ok",
                      "Within the acceptable limit. This does not show the water is microbiologically safe.", BIS))
    elif v <= 2000:
        out.append(_r("tds_mg_l", "TDS", v, "mg/L", g, "above_acceptable_within_permissible", "caution",
                      "Above 500 mg/L. Tolerable only if no better source exists (taste/mineral content).", BIS))
    else:
        out.append(_r("tds_mg_l", "TDS", v, "mg/L", g, "exceeds_limit", "caution",
                      "Above the 2000 mg/L permissible limit. A laboratory test can identify which dissolved substances are high.", BIS))

    g = "0.2 mg/L minimum, 1.0 mg/L maximum (chlorinated supplies)"
    c = residual_chlorine_mg_l
    src = BIS + "; " + WHO
    if c is None:
        out.append(_r("residual_chlorine_mg_l", "Residual chlorine", None, "mg/L", g, "not_provided", "unknown", "Not provided.", src))
    elif c < 0.2:
        out.append(_r("residual_chlorine_mg_l", "Residual chlorine", c, "mg/L", g, "below_recommended_minimum", "caution",
                      "Below 0.2 mg/L. Expected for untreated borewell water, but for a chlorinated supply it means little "
                      "disinfectant protection.", src))
    elif c <= 1.0:
        out.append(_r("residual_chlorine_mg_l", "Residual chlorine", c, "mg/L", g, "within_guideline", "ok",
                      "Within the guideline range.", src))
    elif c <= 5:
        out.append(_r("residual_chlorine_mg_l", "Residual chlorine", c, "mg/L", g, "exceeds_limit", "caution",
                      "Above the BIS 1.0 mg/L limit (taste/odour). Below the WHO health-based value of 5 mg/L.", src))
    else:
        out.append(_r("residual_chlorine_mg_l", "Residual chlorine", c, "mg/L", g, "exceeds_limit", "action_required",
                      "Above 5 mg/L, the WHO health-based guideline value. Do not drink; report to the water supplier.", src))

    g = "not detectable in 100 mL"
    e = ecoli if ecoli in ("absent", "present") else None
    if e == "present":
        out.append(_r("ecoli", "E. coli", "present", "per 100 mL", g, "detected", "action_required",
                      "E. coli detected: indicates faecal contamination. No relaxation applies.", BIS + "; " + WHO))
    elif e == "absent":
        out.append(_r("ecoli", "E. coli", "absent", "per 100 mL", g, "within_guideline", "ok",
                      "Not detected in the tested sample (result applies only to that sample and time).", BIS + "; " + WHO))
    else:
        out.append(_r("ecoli", "E. coli", None, "per 100 mL", g, "not_provided", "unknown",
                      "No E. coli result. Microbiological safety cannot be judged without it.", BIS + "; " + WHO))

    sev = {r["severity"] for r in out}
    provided = [r for r in out if r["status"] != "not_provided"]
    exceeded = [r["label"] for r in out if r["severity"] in ("caution", "action_required")]
    if "action_required" in sev:
        overall = "action_required"
    elif "caution" in sev:
        overall = "caution"
    elif not provided:
        overall = "insufficient_data"
    else:
        overall = "no_exceedance_found"

    reasons = []
    ecoli_state = out[4]["status"]
    if not provided:
        reasons.append("No values were entered.")
    if ecoli_state == "not_provided":
        reasons.append("No E. coli result: pH, TDS, turbidity and chlorine cannot show that water is free of disease-causing microbes.")
    if ecoli_state == "detected":
        reasons.append("Confirm with an accredited laboratory and tell the local water authority or health department.")
    if exceeded and ecoli_state != "detected":
        reasons.append("Readings outside the limits (" + ", ".join(exceeded) + ") should be confirmed by a laboratory.")
    if provided and not reasons:
        reasons.append("Home kits and handheld meters are screening tools; keep testing periodically because results apply only to the sample tested.")
    lab_needed = bool(not provided or ecoli_state in ("not_provided", "detected") or exceeded)

    advice = []
    if overall == "action_required":
        advice.append("Until the water is tested, use a source known to be safe, or boil it (rolling boil for at least 1 minute) before drinking. "
                      "Boiling does not remove chemical contaminants.")
        advice.append("Seek medical care promptly for severe diarrhoea, repeated vomiting, blood in stool, high fever, or signs of dehydration, "
                      "especially in children, older adults and pregnant women.")
    return {"overall": overall, "parameters": out, "lab_test_recommended": lab_needed, "lab_test_reasons": reasons,
            "advice": advice, "standard_sources": [BIS, WHO],
            "disclaimer": "Screening estimate only. It does not replace laboratory testing, official advisories or medical advice, "
                          "and it never means water is 'safe'."}


OVERALL_TEXT = {
    "action_required": "ACTION REQUIRED - at least one result needs urgent attention.",
    "caution": "CAUTION - one or more values are outside the guideline.",
    "no_exceedance_found": "No limit exceeded in the values entered (this is not a guarantee of safety).",
    "insufficient_data": "Not enough data to assess.",
}


def build_report_text(result: dict, source_type: str | None = None, lab_result: bool = False) -> str:
    lines = ["WATERGUARD AI - WATER QUALITY SCREENING REPORT", "=" * 48,
             f"Overall: {OVERALL_TEXT[result['overall']]}",
             f"Values entered by user ({'stated to be from a laboratory report' if lab_result else 'self-reported, not verified'})."]
    if source_type:
        lines.append(f"Water source: {source_type}")
    lines += ["", "Parameter results:"]
    for p in result["parameters"]:
        val = "not provided" if p["value"] is None else f"{p['value']:g} {p['unit']}".strip() if not isinstance(p["value"], str) else p["value"]
        flag = {"ok": "OK", "caution": "CHECK", "action_required": "ACTION", "unknown": "-"}[p["severity"]]
        lines.append(f"- [{flag}] {p['label']}: {val} (guideline: {p['guideline']})")
        lines.append(f"    {p['message']}")
    lines += ["", f"Laboratory test recommended: {'YES' if result['lab_test_recommended'] else 'Not urgently'}"]
    lines += [f"  * {r}" for r in result["lab_test_reasons"]]
    if result["advice"]:
        lines += ["", "What to do now:"] + [f"  * {a}" for a in result["advice"]]
    lines += ["", "Sources: " + "; ".join(result["standard_sources"]), result["disclaimer"]]
    return "\n".join(lines)


def classify_test(t) -> dict:
    """Classify a stored WaterQualityTest row-like object."""
    return evaluate(t.ph, t.turbidity_ntu, t.tds_mg_l, t.residual_chlorine_mg_l,
                    t.ecoli_result if t.ecoli_result in ("absent", "present") else None)