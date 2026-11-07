export const APP_NAME = "WaterGuard AI";

export type Incident = {
  id: string; title: string; locality: string; state: string; disease: string;
  severity: "high" | "moderate" | "low"; status: string; date: string; cases: number | null; casesNote: string;
  waterSource: string; suspectedCause: string; summary: string; timeline: { date: string; event: string }[];
  precautions: string[]; source: string; sourceUrl?: string; caveat: string;
};

const GENERAL = [
  "Drink only boiled (rolling boil, at least 1 minute) or otherwise known-safe water until authorities say the supply is safe.",
  "Wash hands with soap after toilet use and before handling food.",
  "Give oral rehydration solution for diarrhoea and seek medical care early for children, older adults and pregnant women.",
  "Go to a health facility urgently for blood in stool, persistent vomiting, high fever or signs of dehydration.",
];

export const incidents: Incident[] = [
  {
    id: "REAL-INDORE-2025", title: "Contaminated drinking water outbreak, Bhagirathpura", locality: "Bhagirathpura, Indore",
    state: "Madhya Pradesh", disease: "Acute diarrhoeal disease (vomiting and diarrhoea)", severity: "high",
    status: "Reported by media and officials; not independently verified by WaterGuard", date: "2025-12-29", cases: 436,
    casesNote: "436 patients admitted to hospitals since 29 Dec 2025 (as reported 14 Jan 2026). These are admissions, not lab-confirmed cases.",
    waterSource: "Municipal piped supply", suspectedCause: "Contamination of the water supply; residents and media reports point to leakage or sewage mixing.",
    summary: "A vomiting and diarrhoea outbreak was linked by officials to contaminated drinking water in the Bhagirathpura area of Indore, leading to mass hospitalisation.",
    timeline: [
      { date: "29 Dec 2025", event: "Outbreak begins; first hospital admissions reported." },
      { date: "14 Jan 2026", event: "An audit report suggested 15 of 21 deaths may be linked to the outbreak; 436 patients reported admitted in total." },
    ],
    precautions: GENERAL, source: "ETV Bharat / PTI, 14 Jan 2026",
    sourceUrl: "https://www.etvbharat.com/amp/en/bharat/indore-water-contamination-death-audit-suggests-15-died-due-to-diarrhoea-outbreak-enn26011401203",
    caveat: "Death figures differ by source: the administration confirmed 6, an audit suggested 15 of 21 may be linked, residents claimed 23. Map position is city-level (approximate).",
  },
  {
    id: "REAL-BLR-2026", title: "Diarrhoea and stomach infections, KSFC Layout", locality: "KSFC Layout, Lingarajapuram, Bengaluru",
    state: "Karnataka", disease: "Acute diarrhoeal disease", severity: "moderate",
    status: "Reported by media; not independently verified by WaterGuard", date: "2026-01-04", cases: null,
    casesNote: "At least 30 households reported illness. An individual case count was not given.",
    waterSource: "Tap water (piped supply)", suspectedCause: "Reported link to contaminated tap water; cause not confirmed in the source.",
    summary: "Residents of KSFC Layout reported diarrhoea and stomach infections, which was included in a national review of contaminated tap-water incidents.",
    timeline: [{ date: "4 Jan 2026", event: "At least 30 households reported diarrhoea and stomach infections." }],
    precautions: GENERAL, source: "Down To Earth (Kiran Pandey)",
    sourceUrl: "https://www.downtoearth.org.in/amp/story/water/unsafe-water-year-round-over-5500-fell-sick-34-died-due-to-contaminated-tap-water-across-india-in-last-12-months",
    caveat: "Map position is city-level (approximate).",
  },
];

export const nationalContext = {
  text: "At least 5,500 people fell ill and 34 died from contaminated tap water across 26 Indian cities between January 2025 and 7 January 2026.",
  source: "Down To Earth analysis",
  url: "https://www.downtoearth.org.in/amp/story/water/unsafe-water-year-round-over-5500-fell-sick-34-died-due-to-contaminated-tap-water-across-india-in-last-12-months",
};
