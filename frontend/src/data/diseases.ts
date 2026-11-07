export type Disease = {
  slug: string; name: string; tagline: string; cause: string; explanation: string; incubation: string;
  transmission: string[]; symptoms: string[]; seekCare: string[]; prevention: string[]; treatment: string; vaccine: string;
  references: { label: string; url: string }[]; lastReviewed: string;
};

const REVIEWED = "2026-11-01";
const NCDC = { label: "National Centre for Disease Control (India)", url: "https://ncdc.mohfw.gov.in" };

export const diseases: Disease[] = [
  {
    slug: "cholera", name: "Cholera", tagline: "Severe watery diarrhoea that can cause dangerous dehydration within hours.",
    cause: "Bacterium Vibrio cholerae",
    explanation: "Cholera is an acute intestinal infection. Many infected people have no or mild symptoms, but a minority develop severe watery diarrhoea that can be fatal within hours if it is not treated.",
    incubation: "12 hours to 5 days after swallowing contaminated food or water.",
    transmission: ["Drinking water or eating food contaminated with the faeces of an infected person.", "Poor sanitation, flooding and crowded places raise the risk.", "People with no symptoms can still pass the bacteria in their faeces for 1 to 10 days."],
    symptoms: ["Sudden, frequent, very watery diarrhoea (it can look like water that rice was washed in).", "Vomiting and leg cramps.", "Thirst, dry mouth, sunken eyes and very little urine (signs of dehydration).", "Children may also have fever, extreme drowsiness or convulsions."],
    seekCare: ["Go to a health facility immediately for severe watery diarrhoea, especially with vomiting.", "Sip oral rehydration solution (ORS) on the way.", "Treat any sign of dehydration as urgent, especially in babies, children, older adults and pregnant women."],
    prevention: ["Drink safe water: boil it (rolling boil for at least 1 minute) or use another safe source.", "Wash hands with soap after using the toilet and before handling food.", "Keep food covered and eat it freshly cooked.", "Use proper toilets and keep drains away from water sources.", "Oral cholera vaccines are an extra tool in high-risk areas, used together with safe water and sanitation, never instead of them."],
    treatment: "Most people recover with oral rehydration solution. Severe cases need intravenous fluids and antibiotics from health workers. Please do not self-medicate with antibiotics.",
    vaccine: "Oral cholera vaccines exist and are used in outbreak and high-risk settings alongside water and sanitation measures.",
    references: [{ label: "WHO: Cholera fact sheet", url: "https://www.who.int/news-room/fact-sheets/detail/cholera" }, NCDC], lastReviewed: REVIEWED,
  },
  {
    slug: "typhoid", name: "Typhoid fever", tagline: "A bacterial fever spread through contaminated food and water.",
    cause: "Bacterium Salmonella Typhi",
    explanation: "Typhoid is a serious infection of the intestines that can spread to the bloodstream. It is marked by a fever that lasts for days and needs medical diagnosis and treatment.",
    incubation: "Usually 1 to 2 weeks, with a range of about 3 to 30 days.",
    transmission: ["Eating or drinking food or water contaminated with the faeces or urine of an infected person.", "Some people carry the bacteria without symptoms and can spread them for a long time.", "Poor sanitation and unsafe street food or water increase the risk."],
    symptoms: ["Fever that rises over several days and stays high.", "Headache, weakness and tiredness.", "Stomach pain and loss of appetite.", "Constipation or diarrhoea; sometimes flat rose-coloured spots on the chest or abdomen."],
    seekCare: ["See a doctor for a fever that lasts several days, especially with stomach pain. Typhoid needs a medical test to confirm.", "Go to a hospital urgently for confusion, severe belly pain, black or bloody stools, or persistent vomiting."],
    prevention: ["Drink safe water and eat freshly cooked, covered food.", "Wash hands with soap after the toilet and before eating or preparing food.", "Use proper sanitation and keep sewage away from drinking water.", "Typhoid vaccines are available but are not 100% effective, so hygiene still matters.", "People recovering from typhoid should not prepare food for others until a doctor says it is safe."],
    treatment: "Typhoid is treated with antibiotics prescribed by a doctor. Resistance varies by area, so please do not self-medicate.",
    vaccine: "Typhoid vaccines exist; ask a doctor or local health centre which one is available and suitable.",
    references: [{ label: "WHO: Typhoid fact sheet", url: "https://www.who.int/news-room/fact-sheets/detail/typhoid" }, NCDC], lastReviewed: REVIEWED,
  },
  {
    slug: "hepatitis-a", name: "Hepatitis A", tagline: "A liver infection spread through contaminated food, water and close contact.",
    cause: "Hepatitis A virus",
    explanation: "Hepatitis A inflames the liver. It is usually short-lived and most people recover fully, though it can make people very unwell and occasionally becomes severe.",
    incubation: "Usually about 2 to 6 weeks (average around 4 weeks).",
    transmission: ["Eating or drinking food or water contaminated with infected faeces.", "Close contact with an infected person, for example in a household.", "Food handled by someone who is infected and has not washed their hands."],
    symptoms: ["Tiredness, fever, nausea and loss of appetite.", "Stomach pain.", "Dark urine and pale stools.", "Yellow skin or eyes (jaundice). Young children often have mild illness or no symptoms."],
    seekCare: ["See a doctor for yellow skin or eyes, dark urine, or pale stools.", "Go to a hospital urgently for confusion, extreme drowsiness, vomiting blood, bleeding, or severe belly pain."],
    prevention: ["Safe drinking water and good sanitation.", "Wash hands with soap after the toilet and before handling food.", "Hepatitis A vaccine is safe and effective; ask a doctor whether it is recommended.", "Avoid preparing food for others while ill."],
    treatment: "There is no specific medicine. Care is supportive (rest and fluids) under medical advice. Because the liver is affected, ask a doctor before taking any medicines or alcohol.",
    vaccine: "A safe and effective vaccine is available.",
    references: [{ label: "WHO: Hepatitis A fact sheet", url: "https://www.who.int/news-room/fact-sheets/detail/hepatitis-a" }, NCDC], lastReviewed: REVIEWED,
  },
  {
    slug: "hepatitis-e", name: "Hepatitis E", tagline: "A liver infection spread mainly through contaminated drinking water.",
    cause: "Hepatitis E virus",
    explanation: "Hepatitis E is usually mild and clears on its own, but it can cause acute liver failure. Pregnant women are at much higher risk of severe illness.",
    incubation: "2 to 10 weeks after exposure (average 5 to 6 weeks).",
    transmission: ["Mainly by drinking water contaminated with faeces, which is why outbreaks often follow sewage contamination or flooding.", "Poor sanitation and lack of safe water are the main risk factors."],
    symptoms: ["Tiredness, fever, nausea and loss of appetite.", "Stomach pain.", "Dark urine and pale stools.", "Yellow skin or eyes (jaundice)."],
    seekCare: ["Any pregnant woman with jaundice, fever or sudden tiredness should see a doctor urgently.", "Everyone else: see a doctor for yellow skin or eyes or dark urine.", "Go to a hospital urgently for confusion, severe drowsiness, bleeding, or constant vomiting."],
    prevention: ["Safe public water supplies and safe drinking water at home.", "Good sanitation and safe disposal of human waste.", "Hand washing with soap and safe water, especially before handling food.", "Pregnant women should be especially careful to drink only safe water and avoid unsafe ice."],
    treatment: "Most people recover with rest and fluids under medical supervision. Hospital care is needed for severe cases and should be considered for symptomatic pregnant women.",
    vaccine: "A hepatitis E vaccine exists but is not widely available; ask a doctor about local availability.",
    references: [{ label: "WHO: Hepatitis E fact sheet", url: "https://www.who.int/en/news-room/fact-sheets/detail/hepatitis-e" }, NCDC], lastReviewed: REVIEWED,
  },
  {
    slug: "diarrhoeal-diseases", name: "Diarrhoeal diseases", tagline: "Loose, watery stools from many germs; the main danger is dehydration.",
    cause: "Many bacteria, viruses and parasites",
    explanation: "Diarrhoea means three or more loose or liquid stools in a day. Most cases pass in a few days, but diarrhoea can cause dangerous dehydration, especially in young children.",
    incubation: "Varies by germ, from hours to a few days.",
    transmission: ["Drinking water or eating food contaminated with faeces.", "Unwashed hands and unclean utensils.", "Person-to-person spread within households."],
    symptoms: ["Loose or watery stools, often with stomach cramps.", "Nausea or vomiting; sometimes fever.", "Signs of dehydration: thirst, dry mouth, sunken eyes, very little urine, unusual sleepiness."],
    seekCare: ["Get medical care for blood in the stool, high fever, or if the person cannot drink.", "See a doctor if diarrhoea lasts more than 2 days (sooner for babies, young children, older adults and pregnant women).", "Go to a hospital urgently for signs of severe dehydration or confusion."],
    prevention: ["Safe drinking water and proper sanitation.", "Hand washing with soap after the toilet, after cleaning a child, and before food.", "Safe food handling and storage.", "Breastfeeding for young babies, and rotavirus vaccination where it is offered."],
    treatment: "Give oral rehydration solution (ORS) made exactly as the packet says, in small frequent sips, and keep feeding normally. For children, zinc may be advised by a health worker. Do not give antibiotics or anti-diarrhoea tablets unless a doctor advises it.",
    vaccine: "Rotavirus vaccine protects against a common cause in young children where it is part of the immunisation programme.",
    references: [{ label: "WHO: Diarrhoeal disease fact sheet", url: "https://www.who.int/news-room/fact-sheets/detail/diarrhoeal-disease" }, NCDC], lastReviewed: REVIEWED,
  },
];