{
  "_comment": "Example config for a review comparing peer-led verbal vs. institutional print outreach for colorectal cancer screening. include_all requires BOTH the colorectal-screening concept AND the outreach/education concept; exclude_any drops animal, lab, and non-empirical records.",
  "include_all": [
    ["colorectal", "colon cancer", "colorectal cancer", "fit kit", "colonoscopy screening"],
    ["outreach", "education", "navigation", "navigator", "peer", "reminder", "brochure", "counseling", "mailer", "print"]
  ],
  "include_any": ["screening"],
  "exclude_any": ["murine", "mice", "editorial", "genomic biomarkers", "next-generation sequencing"]
}
