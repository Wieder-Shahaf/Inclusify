"""
LGBTQ+ Inclusive Language Rules
================================
Rule-based detection dictionary used as the high-precision fallback when the
LLM is unavailable or as a complement to LLM output.

Each rule is a dict with:
    term        – the exact phrase to match (case-insensitive, substring)
    severity    – one of: "outdated" | "biased" | "potentially_offensive" | "factually_incorrect"
    type        – short category label shown in the UI
    description – explanation shown to the user
    suggestion  – inclusive replacement (optional)

To add a new rule, append a dict to INCLUSIVE_LANGUAGE_RULES below.
Both English and Hebrew terms are supported — the matcher is language-agnostic.
"""

INCLUSIVE_LANGUAGE_RULES = [
    # -------------------------------------------------------------------------
    # English — Outdated Terminology
    # -------------------------------------------------------------------------
    {
        "term": "homosexual",
        "severity": "outdated",
        "type": "Outdated Terminology",
        "description": "The term 'homosexual' is considered clinical and outdated. It has historically been used in pathologizing contexts.",
        "suggestion": "Use 'gay' or 'lesbian' depending on context, or 'LGBTQ+ person'",
    },
    {
        "term": "transsexual",
        "severity": "outdated",
        "type": "Outdated Terminology",
        "description": "The term 'transsexual' is outdated and often perceived as medicalizing. It focuses on medical transition rather than identity.",
        "suggestion": "Use 'transgender person' or 'trans person'",
    },
    {
        "term": "sex change",
        "severity": "outdated",
        "type": "Outdated Terminology",
        "description": "The term 'sex change' is outdated and focuses narrowly on surgery.",
        "suggestion": "Use 'gender-affirming surgery' or 'transition' depending on context",
    },

    # -------------------------------------------------------------------------
    # English — Biased / Stereotyping Language
    # -------------------------------------------------------------------------
    {
        "term": "normal people",
        "severity": "biased",
        "type": "Biased Language",
        "description": "Using 'normal' to describe non-LGBTQ+ people implies that LGBTQ+ people are abnormal.",
        "suggestion": "Use 'cisgender' or 'heterosexual' if referring to those specific groups, or be more specific",
    },
    {
        "term": "the gays",
        "severity": "biased",
        "type": "Dehumanizing Language",
        "description": "Using 'the gays' as a noun can be dehumanizing and othering.",
        "suggestion": "Use 'gay people' or 'gay individuals'",
    },
    {
        "term": "gay lifestyle",
        "severity": "biased",
        "type": "Stereotyping",
        "description": "There is no single 'gay lifestyle.' This term promotes stereotypes and reduces diverse experiences to a monolith.",
        "suggestion": "Be specific about what you mean, or remove the phrase entirely",
    },
    {
        "term": "admitted to being gay",
        "severity": "biased",
        "type": "Stigmatizing Language",
        "description": "Using 'admitted' implies that being gay is something shameful to confess.",
        "suggestion": "Use 'came out as gay' or 'shared that they are gay'",
    },

    # -------------------------------------------------------------------------
    # English — Factually Incorrect
    # -------------------------------------------------------------------------
    {
        "term": "sexual preference",
        "severity": "factually_incorrect",
        "type": "Incorrect Terminology",
        "description": "Sexual orientation is not a choice or preference. Using 'preference' implies it can be changed.",
        "suggestion": "Use 'sexual orientation'",
    },
    {
        "term": "lifestyle choice",
        "severity": "factually_incorrect",
        "type": "Incorrect Framing",
        "description": "Being LGBTQ+ is not a lifestyle choice. This framing is often used to delegitimize LGBTQ+ identities.",
        "suggestion": "Remove or rephrase; sexual orientation and gender identity are not choices",
    },
    {
        "term": "transgendered",
        "severity": "factually_incorrect",
        "type": "Incorrect Grammar",
        "description": "'Transgendered' is grammatically incorrect. Transgender is an adjective, not a verb.",
        "suggestion": "Use 'transgender' (e.g., 'transgender person')",
    },

    # -------------------------------------------------------------------------
    # English — Potentially Offensive / Invalidating Language
    # -------------------------------------------------------------------------
    {
        "term": "born a man",
        "severity": "potentially_offensive",
        "type": "Invalidating Language",
        "description": "This phrase invalidates a person's gender identity and implies that assigned sex determines gender.",
        "suggestion": "Use 'assigned male at birth (AMAB)' if medically relevant",
    },
    {
        "term": "born a woman",
        "severity": "potentially_offensive",
        "type": "Invalidating Language",
        "description": "This phrase invalidates a person's gender identity and implies that assigned sex determines gender.",
        "suggestion": "Use 'assigned female at birth (AFAB)' if medically relevant",
    },
    {
        "term": "transgenders",
        "severity": "potentially_offensive",
        "type": "Grammatically Incorrect",
        "description": "Using 'transgender' as a noun is grammatically incorrect and dehumanizing.",
        "suggestion": "Use 'transgender people' or 'transgender individuals'",
    },

    # -------------------------------------------------------------------------
    # Hebrew — מונחים מיושנים (Outdated)
    # -------------------------------------------------------------------------
    {
        "term": "הומוסקסואל",
        "severity": "outdated",
        "type": "מונח מיושן",
        "description": "המונח 'הומוסקסואל' נחשב קליני ומיושן. היסטורית שימש בהקשרים פתולוגיים.",
        "suggestion": "השתמשו ב'גיי', 'לסבית', או 'אדם מקהילת הלהט\"ב'",
    },
    {
        "term": "טרנסקסואל",
        "severity": "outdated",
        "type": "מונח מיושן",
        "description": "המונח 'טרנסקסואל' מיושן ונתפס כממדיקל. הוא מתמקד במעבר רפואי ולא בזהות.",
        "suggestion": "השתמשו ב'אדם טרנסג'נדר' או 'אדם טרנס'",
    },

    # -------------------------------------------------------------------------
    # Hebrew — שגויים עובדתית (Factually Incorrect)
    # -------------------------------------------------------------------------
    {
        "term": "העדפה מינית",
        "severity": "factually_incorrect",
        "type": "מונח שגוי",
        "description": "נטייה מינית אינה בחירה או העדפה. שימוש ב'העדפה' מרמז שניתן לשנות אותה.",
        "suggestion": "השתמשו ב'נטייה מינית'",
    },

    # -------------------------------------------------------------------------
    # Hebrew — שפה פוגענית (Potentially Offensive)
    # -------------------------------------------------------------------------
    {
        "term": "נולד גבר",
        "severity": "potentially_offensive",
        "type": "שפה פוגענית",
        "description": "ביטוי זה פוגע בזהות המגדרית של האדם ומרמז שהמין שהוקצה בלידה קובע את המגדר.",
        "suggestion": "השתמשו ב'הוקצה זכר בלידה' אם רלוונטי רפואית",
    },
    {
        "term": "נולדה אישה",
        "severity": "potentially_offensive",
        "type": "שפה פוגענית",
        "description": "ביטוי זה פוגע בזהות המגדרית של האדם ומרמז שהמין שהוקצה בלידה קובע את המגדר.",
        "suggestion": "השתמשו ב'הוקצתה נקבה בלידה' אם רלוונטי רפואית",
    },

    # -------------------------------------------------------------------------
    # Hebrew — שפה מוטה (Biased)
    # -------------------------------------------------------------------------
    {
        "term": "אנשים נורמליים",
        "severity": "biased",
        "type": "שפה מוטה",
        "description": "שימוש ב'נורמלי' לתיאור אנשים שאינם מקהילת הלהט\"ב מרמז שאנשים מהקהילה אינם נורמליים.",
        "suggestion": "השתמשו ב'סיסג'נדר' או 'הטרוסקסואל' אם מתכוונים לקבוצות אלו",
    },
]
