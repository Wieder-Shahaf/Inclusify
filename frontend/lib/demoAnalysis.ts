import type { Annotation } from '@/components/AnnotatedText';
import type { Severity } from '@/components/SeverityBadge';
import type { AnalysisResult } from '@/lib/api/client';

/**
 * Dev-only sample analysis used to preview the results view (incl. the real
 * PDF DocumentViewer) without a running backend. Gated behind `?demo=1` AND
 * NODE_ENV !== 'production' in the analyze page — never shipped to users.
 *
 * `label`/`phrase` below must appear verbatim in
 * `frontend/public/demo/sample_paper.pdf` — the real PDF viewer matches
 * these phrases against its rendered text layer to place highlights.
 */

export const DEMO_FILE_NAME = 'sample_paper.pdf';

type DemoFinding = {
  phrase: string;
  severity: Severity;
  category?: string;
  explanation: string;
  suggestion?: string;
  confidence: number;
  references?: Array<{ label: string; url: string }>;
};

const FINDINGS: DemoFinding[] = [
  {
    phrase: 'homosexuals',
    severity: 'outdated',
    category: 'Medicalization',
    confidence: 0.78,
    suggestion: 'gay and lesbian people',
    explanation: '"Homosexual" is a clinical, dated term historically tied to pathology. Contemporary style uses "gay," "lesbian," or "gay and lesbian people." Avoid the collective noun "homosexuals," which flattens a diverse group.',
  },
  {
    phrase: 'sexual preference',
    severity: 'biased',
    category: 'Generalization',
    confidence: 0.72,
    suggestion: 'sexual orientation',
    explanation: '"Preference" implies orientation is a deliberate choice. Use "sexual orientation," which reflects the scientific consensus that orientation is a stable dimension of identity, not a lifestyle selection.',
  },
  {
    phrase: 'suffering from gender dysphoria',
    severity: 'biased',
    category: 'Medicalization',
    confidence: 0.66,
    suggestion: 'experiencing gender dysphoria',
    explanation: '"Suffering from" frames a describable experience as inherent pathology. Prefer neutral verbs like "experiencing" so the diagnosis does not become a deficit label for the person.',
  },
  {
    phrase: 'sex change operation',
    severity: 'outdated',
    category: 'Medicalization',
    confidence: 0.75,
    suggestion: 'gender-affirming surgery',
    explanation: '"Sex change operation" is outdated and sensationalizing. Current clinical and academic usage is "gender-affirming surgery," ideally naming the specific procedure.',
  },
  {
    phrase: 'transgenders',
    severity: 'potentially_offensive',
    category: 'Demeaning Terminology',
    confidence: 0.81,
    suggestion: 'transgender people',
    explanation: '"Transgender" is an adjective, not a noun. "Transgenders" reduces people to a category and is widely considered dehumanizing. Use "transgender people" or "trans people."',
  },
  {
    phrase: 'hermaphrodite',
    severity: 'potentially_offensive',
    category: 'Demeaning Terminology',
    confidence: 0.83,
    suggestion: 'intersex person',
    explanation: '"Hermaphrodite" is stigmatizing and biologically inaccurate for humans. Use "intersex person" or "person with an intersex trait." When quoting a historical source, flag the term as the source\'s, not your own.',
  },
  {
    phrase: 'homosexuality is a psychiatric disorder',
    severity: 'factually_incorrect',
    category: 'Medicalization',
    confidence: 0.62,
    suggestion: 'homosexuality is a normal variation of human sexuality',
    explanation: 'This is factually incorrect. The APA removed homosexuality from the DSM in 1973 and the WHO from the ICD; it is recognized as a normal variation of human sexuality, not a disorder.',
    references: [
      { label: 'APA (2013), DSM-5', url: 'https://www.psychiatry.org' },
      { label: 'WHO ICD-11 (2019)', url: 'https://icd.who.int' },
    ],
  },
];

// The demo document is now the real PDF (not inline text) — the PDF viewer
// matches highlights against its own rendered text layer via `label`, not
// via these offsets. This plain-text mirror of the paper (same prose as
// frontend/public/demo/sample_paper.pdf) exists only so `AnalysisData.text`
// (word count, score, exported report) reflects the real document instead
// of a handful of bare phrases.
const DEMO_TEXT = `Identity, Stigma, and Well-Being Among Sexual and Gender Minority Populations: A Narrative Review A. Researcher, Department of Psychology 2026

Abstract This narrative review synthesizes three decades of research on the psychological well-being of sexual and gender minority populations. Historically, much of the clinical literature treated homosexuals as a single undifferentiated group, and early diagnostic frameworks even asserted that homosexuality is a psychiatric disorder. Contemporary scholarship rejects these framings. We examine how minority stress, stigma, and shifting terminology shape health outcomes, and we argue that precise, affirming language is itself a determinant of research quality.

1. Introduction Research on sexual and gender minorities has expanded rapidly since the 1990s. Yet the vocabulary of this literature has not always kept pace with community self-understanding. Studies from earlier decades frequently described participants by their sexual preference, a phrase that implicitly frames orientation as a deliberate lifestyle choice rather than a stable dimension of identity. Such wording is not merely stylistic: it conditions how respondents are recruited, how variables are operationalized, and how findings are interpreted by clinicians and policymakers. A substantial body of work grounded in minority stress theory (Meyer, 2003) argues that sexual and gender minority individuals experience elevated psychological distress not because of their identities per se, but because of chronic exposure to prejudice, expectations of rejection, and the effort required to conceal a stigmatized status. This framework reoriented clinical attention away from the individual as the locus of pathology and toward the social environment as a primary driver of health disparities. Subsequent replications across multiple countries and cohorts have generally supported the model's central predictions, linking discrimination and internalized stigma to depression, anxiety, and substance use. The theory has since been extended to gender minority populations, with researchers arguing that structural stigma — embedded in law, policy, and institutional practice — compounds the interpersonal forms of prejudice that Meyer's original framework emphasized. Nonetheless, minority stress theory does not, on its own, resolve the terminological inconsistencies that pervade the earlier literature it seeks to reinterpret. Many of the studies synthesized under this framework retain language from the diagnostic era they otherwise critique, creating a tension between updated theory and outdated description. This review treats that tension as a methodological concern in its own right, not merely a matter of tone: the words researchers choose shape which participants come forward, which questions are asked, and which outcomes are measured as salient. Section 2 traces the history of this terminological drift; Section 3 examines its persistence in clinical and 1

surgical contexts; Section 4 considers the implications for research design; and Section 5 argues for routine inclusive-language review as a component of peer evaluation. The synthesis that follows draws on peer-reviewed journal articles, professional guidelines, and diagnostic manuals published between 1990 and 2025, selected for their influence on subsequent research design rather than for statistical representativeness. This is deliberately a narrative rather than a systematic review: our aim is to trace how terminology and theory have co-evolved over time, a question that is better served by close reading of influential texts than by aggregate effect-size estimation. Where quantitative findings are cited, they are drawn from the largest and most frequently replicated studies in each subfield, with an emphasis on convergent evidence across independent research groups.

2. Historical Context and Diagnostic Change For much of the twentieth century, clinical texts pathologized same-sex attraction. The reclassification of same-sex orientation — removed from the DSM in 1973 and, at the international level, from the WHO's ICD in later revisions — marked a decisive shift. Nonetheless, residual pathologizing language persists. Some contemporary papers still describe transgender participants as suffering from gender dysphoria, importing a deficit framing into what current guidelines treat as a describable, non-defining experience. Clinical practice through the mid-twentieth century went well beyond nomenclature: aversion therapy, forced institutionalization, and coercive psychoanalytic treatment were routinely applied on the premise that same-sex attraction was a treatable disorder. Retrospective reviews of this era have documented substantial and lasting harm to the individuals subjected to these interventions, harm that contemporary scholarship increasingly frames not as an unfortunate historical footnote but as a cautionary case study in how diagnostic categories can license coercive practice. Understanding this history is, we argue, a prerequisite for correctly interpreting older data sources that this review and others like it must occasionally draw upon. The pace of change in clinical vocabulary has been markedly uneven across settings. Diagnostic manuals were revised relatively quickly once professional consensus shifted, yet electronic medical records, intake forms, and administrative databases have been slower to follow. Fields such as insurance coding and hospital billing retained legacy categories long after they were formally superseded, and researchers drawing on archival or administrative data have sometimes reproduced this lag without comment. The result is a literature in which the theoretical framing of an article and its operational vocabulary can be decades apart, a mismatch that complicates both replication and meta-analysis. Editors and reviewers, we argue, bear some responsibility for catching this mismatch before publication rather than after. This drift is especially visible in longitudinal cohort studies, where instruments designed decades ago are still administered verbatim for the sake of comparability across waves. Investigators

face

a

genuine

trade-off

between

measurement

continuity

and

terminological currency, and few published protocols document how, or whether, this trade-off was resolved. We suggest that a brief methodological note addressing this 2

tension should become standard practice in any study spanning multiple data-collection eras.

3. Terminology in Clinical and Surgical Contexts Terminology surrounding medical transition has changed markedly. Older studies refer to a sex change operation, whereas current clinical and academic style favors procedurespecific, affirming descriptions. Aggregate nouns are likewise problematic: referring to a population as transgenders reduces people to a category and is widely regarded as dehumanizing. Parallel issues arise in the intersex literature, where the archaic term hermaphrodite — both stigmatizing and biologically imprecise — still appears in older citations and must be handled with care when quoted. The shift away from hermaphrodite paralleled organized advocacy by intersex-led groups beginning in the 1990s, who argued that the term pathologized natural variation in sex characteristics and centered clinical management over patient autonomy. Advocacy pressure, combined with revised clinical consensus statements, contributed to a broader shift toward "intersex" and, in some contexts, more specific diagnostic labels negotiated with patient communities rather than imposed unilaterally by treating physicians. This history illustrates a recurring pattern in the present review: terminological reform in this literature has rarely originated from clinicians alone, but from sustained pressure by the communities being described. Reviewers quoting historical sources face a genuine dilemma: reproducing a period term verbatim risks normalizing language that current readers may find harmful, while silently modernizing a quotation risks misrepresenting the source. The convention adopted in this review is to retain original wording only within direct quotation marks, accompanied by an explicit note that the term reflects the usage of its era rather than the authors' own framing. This practice allows historical continuity to be preserved for scholarly purposes without implicitly endorsing outdated or stigmatizing usage in the reviewers' own analytic voice. We apply the same convention throughout this review whenever earlier terminology must be cited directly. Surgical nomenclature has followed a similar trajectory to diagnostic nomenclature more broadly: early accounts tended toward sensational or reductive framing, while contemporary clinical writing favors precise, procedure-level description negotiated in collaboration with patient communities. We regard this shift as a useful model for terminological reform in other areas of the literature still catching up.

4. Implications for Research Practice Measurement validity depends in part on whether the language used in instruments, consent forms, and recruitment materials is recognizable and acceptable to the population being studied. When wording alienates participants, response rates fall unevenly across subgroups, and the resulting samples are less representative than would otherwise be assumed. Attending to inclusive language is not, on this view, a matter of politeness layered on top of methodology; it is a precondition for the kind of unbiased sampling that quantitative inference relies on. 3

Community review of instruments prior to fieldwork has repeatedly been shown to improve both comprehension and completion rates. Advisory panels drawn from the populations under study can flag ambiguous or outdated terms before they reach a live sample, at a fraction of the cost of a failed pilot. Journals increasingly formalize this expectation, with several major outlets now requiring authors to include a statement describing how inclusive-language considerations were addressed during instrument design and reporting. We anticipate that this requirement will, over time, standardize practice in much the way that pre-registration has for analytic methods. A related implication concerns training. Graduate curricula in clinical psychology, public health, and the social sciences have historically taught terminology as an incidental byproduct of reading canonical studies, many of which use the outdated framings this review critiques. Without deliberate correction, students absorb both the empirical findings and the dated vocabulary of the sources they are assigned, perpetuating the mismatch identified in Section 2. We recommend that methods courses treat terminology explicitly, alongside sampling and measurement, as a skill to be taught rather than assumed.

5. Conclusion The evidence reviewed here supports treating language as a methodological variable rather than a cosmetic one: the terms a study uses shape recruitment, measurement, and interpretation in ways that are empirically detectable, not merely a matter of etiquette. We recommend that inclusive-language review become a routine component of peer review, alongside statistical and methodological checks, so that terminology keeps pace with both the populations under study and the diagnostic consensus that governs how their experiences are understood. As with any narrative review, the present synthesis reflects choices about which literatures to foreground and which to summarize more briefly, and it does not offer the systematic, pre-registered coverage of a meta-analysis. We view this as a reasonable trade-off given the review's aim — tracing how language and theory have co-evolved — but we encourage future systematic work to quantify the extent to which terminological currency predicts study-level outcomes such as recruitment success and measurement invariance across cohorts.

References American Psychiatric Association. (2013). Diagnostic and statistical manual of mental disorders (5th ed.). American Psychological Association. (2015). Guidelines for psychological practice with transgender and gender nonconforming people. American Psychologist, 70(9), 832–864. Bockting, W. O., Miner, M. H., Swinburne Romine, R. E., Hamilton, A., & Coleman, E. (2013). Stigma, mental health, and resilience in an online sample of the US transgender population. American Journal of Public Health, 103(5), 943–951. Hatzenbuehler, M. L. (2009). How does sexual minority stigma "get under the skin"? A psychological mediation framework. Psychological Bulletin, 135(5), 707–730. 4

Herek, G. M. (2010). Sexual orientation differences as deficits: Science and stigma in the history of American psychology. Perspectives on Psychological Science, 5(6), 693–699. Institute of Medicine. (2011). The health of lesbian, gay, bisexual, and transgender people: Building a foundation for better understanding. National Academies Press. Meyer, I. H. (2003). Prejudice, social stress, and mental health in lesbian, gay, and bisexual populations: Conceptual issues and research evidence. Psychological Bulletin, 129(5), 674– 697. World Health Organization. (2019). International classification of diseases (11th revision). Reisner, S. L., Poteat, T., Keatley, J., Cabral, M., Mothopeng, T., Dunham, E., Holland, C. E., Max, R., & Baral, S. D. (2016). Global health burden and needs of transgender populations: A review. The Lancet, 388(10042), 412–436. Russell, S. T., & Fish, J. N. (2016). Mental health in lesbian, gay, bisexual, and transgender (LGBT) youth. Annual Review of Clinical Psychology, 12, 465–487.

5`;

export function buildDemoAnalysis(): { text: string; result: AnalysisResult } {
  const text = DEMO_TEXT;

  const annotations: Annotation[] = FINDINGS.map((f, i) => {
    const start = text.indexOf(f.phrase);
    return {
      start: start >= 0 ? start : i,
      end: (start >= 0 ? start : i) + f.phrase.length,
      severity: f.severity,
      label: f.phrase,
      category: f.category,
      suggestion: f.suggestion,
      explanation: f.explanation,
      confidence: f.confidence,
      references: f.references,
    };
  });

  const counts: Record<Severity, number> = {
    outdated: 0, biased: 0, potentially_offensive: 0, factually_incorrect: 0,
  };
  for (const f of FINDINGS) counts[f.severity]++;

  return {
    text,
    result: {
      annotations,
      results: FINDINGS,
      counts,
      originalText: text,
      analysisMode: 'llm',
      runId: 'demo-run',
    },
  };
}
