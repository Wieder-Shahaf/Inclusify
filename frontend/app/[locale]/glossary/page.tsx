import { getTranslations, setRequestLocale } from 'next-intl/server';
import { type GlossaryTerm } from '@/components/glossary/GlossaryClient';
import dynamic from 'next/dynamic';

const GlossaryClient = dynamic(() => import('@/components/glossary/GlossaryClient'));

// English glossary terms with accurate definitions from authoritative sources
// Sources: HRC, PFLAG, The Trevor Project, GLAAD
const glossaryTermsEN: GlossaryTerm[] = [
  // Gender Identity Terms
  {
    term: 'Gender Identity',
    definition: "One's innermost concept of self as male, female, a blend of both, or neither – how individuals perceive themselves and what they call themselves. One's gender identity can be the same or different from their sex assigned at birth.",
    category: 'identity',
    related: ['Cisgender', 'Transgender', 'Non-binary'],
  },
  {
    term: 'Transgender',
    definition: 'An umbrella term for people whose gender identity and/or expression is different from cultural expectations based on the sex they were assigned at birth. Being transgender does not imply any specific sexual orientation.',
    category: 'identity',
    note: 'Always use as an adjective, not a noun. Say "transgender person" not "a transgender."',
    related: ['Cisgender', 'Gender Identity', 'Transitioning'],
  },
  {
    term: 'Cisgender',
    definition: 'An adjective describing a person whose gender identity aligns with the sex they were assigned at birth. The prefix "cis-" means "on the same side as."',
    category: 'identity',
    related: ['Transgender', 'Gender Identity'],
  },
  {
    term: 'Non-binary',
    definition: 'An adjective describing a person who does not identify exclusively as a man or a woman. Non-binary people may identify as being both, somewhere in between, or as falling completely outside these categories.',
    category: 'identity',
    related: ['Genderqueer', 'Gender-fluid', 'Agender'],
  },
  {
    term: 'Genderqueer',
    definition: 'A term used by individuals who reject notions of static categories of gender and embrace a fluidity of gender identity.',
    category: 'identity',
    related: ['Non-binary', 'Gender-fluid'],
  },
  {
    term: 'Gender-fluid',
    definition: 'A person who does not identify with a single fixed gender or has a fluid or unfixed gender identity. Their gender identity may shift over time or depending on the situation.',
    category: 'identity',
    related: ['Non-binary', 'Genderqueer'],
  },
  {
    term: 'Agender',
    definition: 'A person who does not identify with or experience any gender. Agender individuals may describe themselves as having no gender identity.',
    category: 'identity',
    related: ['Non-binary', 'Gender Identity'],
  },
  {
    term: 'Intersex',
    definition: 'Intersex people are born with a variety of differences in their sex traits and reproductive anatomy, including variations in chromosomes, hormones, genitalia, and other sex characteristics.',
    category: 'identity',
    note: 'Being intersex is about biological sex characteristics, not gender identity or sexual orientation.',
  },
  // Sexual Orientation Terms
  {
    term: 'Sexual Orientation',
    definition: 'An inherent or immutable enduring emotional, romantic, or sexual attraction to other people. Sexual orientation is distinct from gender identity and gender expression.',
    category: 'orientation',
    related: ['Gender Identity'],
  },
  {
    term: 'Gay',
    definition: 'A person who is emotionally, romantically, or sexually attracted to members of the same gender. While often used to describe men, the term can apply to people of any gender identity.',
    category: 'orientation',
    related: ['Lesbian', 'Sexual Orientation'],
  },
  {
    term: 'Lesbian',
    definition: 'A woman who is emotionally, romantically, or sexually attracted to other women. Some non-binary people may also identify with this term.',
    category: 'orientation',
    related: ['Gay', 'Sexual Orientation'],
  },
  {
    term: 'Bisexual',
    definition: 'A person who has the potential to be emotionally, romantically, or sexually attracted to people of more than one gender. Sometimes shortened to "bi."',
    category: 'orientation',
    related: ['Pansexual', 'Sexual Orientation'],
  },
  {
    term: 'Pansexual',
    definition: 'A person who has the potential for emotional, romantic, or sexual attraction to people of any gender. Sometimes used interchangeably with bisexual.',
    category: 'orientation',
    related: ['Bisexual', 'Sexual Orientation'],
  },
  {
    term: 'Asexual',
    definition: 'A person who experiences little or no sexual attraction to others. Asexuality exists on a spectrum, and asexual people may experience other forms of attraction.',
    category: 'orientation',
    note: 'Asexuality is distinct from celibacy, which is a choice to abstain from sexual activity.',
  },
  {
    term: 'Queer',
    definition: 'A term people often use to express a spectrum of identities and orientations that are counter to the mainstream. Reclaimed by many as a term of empowerment.',
    category: 'orientation',
    note: 'Some people still find this term offensive due to its historical use as a slur.',
    related: ['LGBTQ+', 'Sexual Orientation'],
  },
  // Gender Expression Terms
  {
    term: 'Gender Expression',
    definition: "The external appearance of one's gender identity, usually expressed through behavior, clothing, body characteristics, hairstyle, or voice.",
    category: 'expression',
    related: ['Gender Identity'],
  },
  {
    term: 'Pronouns',
    definition: "The words used to refer to a person other than their name. Common pronouns include she/her, he/him, and they/them. Respecting someone's pronouns is a basic way to show respect for their identity.",
    category: 'expression',
    note: "When unsure of someone's pronouns, it's appropriate to ask or use they/them until you know.",
  },
  {
    term: 'Transitioning',
    definition: 'A series of processes that some transgender people may undergo to live more fully as their true gender. This may include social, legal, and/or medical transition.',
    category: 'expression',
    related: ['Transgender', 'Gender Identity'],
  },
  // Concepts
  {
    term: 'LGBTQ+',
    definition: 'An acronym for "lesbian, gay, bisexual, transgender, and queer" with a "+" sign to recognize the limitless sexual orientations and gender identities.',
    category: 'concepts',
    related: ['Queer', 'Sexual Orientation', 'Gender Identity'],
  },
  {
    term: 'Ally',
    definition: 'A term used to describe someone who is actively supportive of LGBTQ+ people. Being an ally requires action, not just identification.',
    category: 'concepts',
  },
  {
    term: 'Coming Out',
    definition: 'The process in which a person first acknowledges, accepts, and appreciates their sexual orientation or gender identity and begins to share that with others.',
    category: 'concepts',
    note: 'Never "out" someone without their explicit permission.',
  },
  {
    term: 'Deadnaming',
    definition: 'Referring to a transgender or non-binary person by a name they used before transitioning. Deadnaming can be harmful and disrespectful.',
    category: 'concepts',
    note: "Always use a person's current chosen name, even when referring to them in the past.",
  },
  {
    term: 'Inclusive Language',
    definition: 'Language that acknowledges diversity, conveys respect, and is sensitive to differences. It avoids biases or expressions that discriminate against groups of people.',
    category: 'concepts',
    related: ['Ally', 'LGBTQ+'],
  },
];

// Hebrew glossary terms
const glossaryTermsHE: GlossaryTerm[] = [
  // מונחי זהות מגדרית
  {
    term: 'זהות מגדרית',
    definition: 'התפיסה הפנימית העמוקה ביותר של אדם את עצמו כגבר, אישה, שילוב של שניהם, או אף אחד מהם. זהות מגדרית יכולה להיות זהה או שונה מהמין שהוקצה בלידה.',
    category: 'identity',
    related: ['סיסג׳נדר', 'טרנסג׳נדר', 'נון-בינארי'],
  },
  {
    term: 'טרנסג׳נדר',
    definition: 'מונח כולל לאנשים שזהותם המגדרית ו/או הביטוי המגדרי שלהם שונים מהציפיות התרבותיות המבוססות על המין שהוקצה להם בלידה. להיות טרנסג׳נדר אינו מרמז על נטייה מינית ספציפית.',
    category: 'identity',
    note: 'יש להשתמש תמיד כתואר, לא כשם עצם. אמרו "אדם טרנסג׳נדר" ולא "טרנסג׳נדר".',
    related: ['סיסג׳נדר', 'זהות מגדרית', 'מעבר מגדרי'],
  },
  {
    term: 'סיסג׳נדר',
    definition: 'תואר המתאר אדם שזהותו המגדרית תואמת את המין שהוקצה לו בלידה. הקידומת "סיס-" פירושה "באותו צד".',
    category: 'identity',
    related: ['טרנסג׳נדר', 'זהות מגדרית'],
  },
  {
    term: 'נון-בינארי',
    definition: 'תואר המתאר אדם שאינו מזדהה באופן בלעדי כגבר או כאישה. אנשים נון-בינאריים עשויים להזדהות כשניהם, במקום כלשהו ביניהם, או מחוץ לקטגוריות אלה.',
    category: 'identity',
    related: ['ג׳נדרקוויר', 'ג׳נדר פלואיד', 'אג׳נדר'],
  },
  {
    term: 'ג׳נדרקוויר',
    definition: 'מונח המשמש אנשים הדוחים תפיסות של קטגוריות מגדר סטטיות ומאמצים נזילות של זהות מגדרית.',
    category: 'identity',
    related: ['נון-בינארי', 'ג׳נדר פלואיד'],
  },
  {
    term: 'ג׳נדר פלואיד',
    definition: 'אדם שאינו מזדהה עם מגדר יחיד קבוע או שזהותו המגדרית נזילה ומשתנה. זהותם עשויה להשתנות לאורך זמן או בהתאם למצב.',
    category: 'identity',
    related: ['נון-בינארי', 'ג׳נדרקוויר'],
  },
  {
    term: 'אג׳נדר',
    definition: 'אדם שאינו מזדהה עם מגדר כלשהו או אינו חווה מגדר. אנשים אג׳נדר עשויים לתאר עצמם כחסרי זהות מגדרית.',
    category: 'identity',
    related: ['נון-בינארי', 'זהות מגדרית'],
  },
  {
    term: 'אינטרסקס',
    definition: 'אנשים אינטרסקס נולדים עם מגוון הבדלים במאפייני המין והאנטומיה הרבייתית שלהם, כולל וריאציות בכרומוזומים, הורמונים, איברי מין ומאפייני מין אחרים.',
    category: 'identity',
    note: 'להיות אינטרסקס נוגע למאפייני מין ביולוגיים, לא לזהות מגדרית או נטייה מינית.',
  },
  // מונחי נטייה מינית
  {
    term: 'נטייה מינית',
    definition: 'משיכה רגשית, רומנטית או מינית מתמשכת וטבועה לאנשים אחרים. נטייה מינית נבדלת מזהות מגדרית וביטוי מגדרי.',
    category: 'orientation',
    related: ['זהות מגדרית'],
  },
  {
    term: 'גיי',
    definition: 'אדם הנמשך רגשית, רומנטית או מינית לבני אותו המגדר. בעוד שהמונח משמש לעתים קרובות לתיאור גברים, הוא יכול להתייחס לאנשים מכל זהות מגדרית.',
    category: 'orientation',
    related: ['לסבית', 'נטייה מינית'],
  },
  {
    term: 'לסבית',
    definition: 'אישה הנמשכת רגשית, רומנטית או מינית לנשים אחרות. חלק מאנשים נון-בינאריים עשויים גם להזדהות עם מונח זה.',
    category: 'orientation',
    related: ['גיי', 'נטייה מינית'],
  },
  {
    term: 'ביסקסואל',
    definition: 'אדם בעל פוטנציאל להימשך רגשית, רומנטית או מינית לאנשים מיותר ממגדר אחד. לעתים מקוצר ל"בי".',
    category: 'orientation',
    related: ['פאנסקסואל', 'נטייה מינית'],
  },
  {
    term: 'פאנסקסואל',
    definition: 'אדם בעל פוטנציאל למשיכה רגשית, רומנטית או מינית לאנשים מכל מגדר. לעתים משמש לסירוגין עם ביסקסואל.',
    category: 'orientation',
    related: ['ביסקסואל', 'נטייה מינית'],
  },
  {
    term: 'אסקסואל',
    definition: 'אדם החווה משיכה מינית מועטה או לא חווה כלל משיכה מינית לאחרים. אסקסואליות קיימת על ספקטרום, ואנשים אסקסואלים עשויים לחוות צורות אחרות של משיכה.',
    category: 'orientation',
    note: 'אסקסואליות נבדלת מצליבת, שהיא בחירה להימנע מפעילות מינית.',
  },
  {
    term: 'קוויר',
    definition: 'מונח שאנשים משתמשים בו לעתים קרובות לביטוי ספקטרום של זהויות ונטיות שאינן מיינסטרים. הושב על ידי רבים כמונח של העצמה.',
    category: 'orientation',
    note: 'חלק מהאנשים עדיין מוצאים מונח זה פוגעני בשל השימוש ההיסטורי בו כעלבון.',
    related: ['להט"ב+', 'נטייה מינית'],
  },
  // מונחי ביטוי מגדרי
  {
    term: 'ביטוי מגדרי',
    definition: 'המראה החיצוני של זהות מגדרית, המתבטא בדרך כלל באמצעות התנהגות, לבוש, מאפייני גוף, תסרוקת או קול.',
    category: 'expression',
    related: ['זהות מגדרית'],
  },
  {
    term: 'כינויי גוף',
    definition: 'המילים המשמשות להתייחסות לאדם מלבד שמו. כינויים נפוצים כוללים היא/שלה, הוא/שלו, והם/שלהם. כיבוד כינויי הגוף של מישהו הוא דרך בסיסית להראות כבוד לזהותו.',
    category: 'expression',
    note: 'כשלא בטוחים בכינויי הגוף של מישהו, מתאים לשאול או להשתמש בהם/שלהם עד שתדעו.',
  },
  {
    term: 'מעבר מגדרי',
    definition: 'סדרה של תהליכים שחלק מאנשים טרנסג׳נדרים עשויים לעבור כדי לחיות באופן מלא יותר כמגדרם האמיתי. זה עשוי לכלול מעבר חברתי, משפטי ו/או רפואי.',
    category: 'expression',
    related: ['טרנסג׳נדר', 'זהות מגדרית'],
  },
  // מושגים
  {
    term: 'להט"ב+',
    definition: 'ראשי תיבות של "לסביות, הומואים, טרנסג׳נדרים, ביסקסואלים" עם סימן "+" לציון מגוון הנטיות המיניות והזהויות המגדריות.',
    category: 'concepts',
    related: ['קוויר', 'נטייה מינית', 'זהות מגדרית'],
  },
  {
    term: 'בעל/ת ברית (אליי)',
    definition: 'מונח המתאר מישהו שתומך באופן פעיל באנשי להט"ב+. להיות בעל ברית דורש פעולה, לא רק הזדהות.',
    category: 'concepts',
  },
  {
    term: 'יציאה מהארון',
    definition: 'התהליך שבו אדם מכיר לראשונה, מקבל ומעריך את הנטייה המינית או הזהות המגדרית שלו ומתחיל לשתף זאת עם אחרים.',
    category: 'concepts',
    note: 'לעולם אל תחשפו את מישהו ללא הסכמתו המפורשת.',
  },
  {
    term: 'דדנייםינג',
    definition: 'התייחסות לאדם טרנסג׳נדר או נון-בינארי בשם שהשתמש בו לפני המעבר. דדנייםינג יכול להיות מזיק ולא מכבד.',
    category: 'concepts',
    note: 'תמיד השתמשו בשם הנוכחי שאדם בחר, גם כשמתייחסים אליו בעבר.',
  },
  {
    term: 'שפה מכלילה',
    definition: 'שפה המכירה במגוון, מעבירה כבוד ורגישה להבדלים. היא נמנעת מהטיות או ביטויים המפלים קבוצות אנשים על בסיס זהותם.',
    category: 'concepts',
    related: ['בעל/ת ברית', 'להט"ב+'],
  },
];

type Props = {
  params: Promise<{ locale: string }>;
};

export default async function GlossaryPage({ params }: Props) {
  const { locale } = await params;
  setRequestLocale(locale);

  const t = await getTranslations();
  const isHebrew = locale === 'he';

  const translations = {
    title: t('glossary.title'),
    subtitle: t('glossary.subtitle'),
    searchPlaceholder: t('glossary.searchPlaceholder'),
    badge: t('glossary.badge'),
    categories: {
      all: t('glossary.categories.all'),
      identity: t('glossary.categories.identity'),
      orientation: t('glossary.categories.orientation'),
      expression: t('glossary.categories.expression'),
      concepts: t('glossary.categories.concepts'),
    },
    sourcesTitle: t('glossary.sourcesTitle'),
    sourcesDesc: t('glossary.sourcesDesc'),
    noResults: t('glossary.noResults'),
    relatedTerms: t('glossary.relatedTerms'),
  };

  const terms = isHebrew ? glossaryTermsHE : glossaryTermsEN;

  return <GlossaryClient terms={terms} translations={translations} isHebrew={isHebrew} />;
}
