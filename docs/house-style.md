# ArbRadar house style

Measured, not guessed: the numbers come from the GAR daily briefings and the
IAReporter headline emails archived from the inbox (`docs/style-corpus/README.md`
has the full measurement; `python tools/newsletter_corpus.py` regenerates it).
Rules marked (rule) are applied by the build itself; the rest guide the
editorial model when it is switched on.

## What the trade press actually does

GAR sends one email a day with a median of 7 stories: four to six new ones and
two or three "recent highlights" from earlier days. Every story is a headline,
one sentence, and nothing else. IAReporter sends a median of 9 headlines a day,
each a full sentence of about 15 words, and lists the documents behind them.

| measure | GAR | IAReporter |
|---|---|---|
| stories per issue (median) | 7 | 9 |
| headline length (median) | 8 words, 52 characters | 15 words, 106 characters |
| headlines naming a forum or treaty | 17% | 44% |
| headlines with a colon | 2.5% | 6% (labels: Analysis, Updated, Revealed) |
| headlines naming an amount | under 1% | 4% |
| standfirst length (median, p90) | 32 words, 44 | none |
| standfirsts of one sentence | 98% | – |
| standfirsts naming an amount | 44% | – |
| standfirsts naming a forum or treaty | 48% | – |

GAR's headline verbs, in order of use: hires, wins, loses, claims, joins,
threatens, fails, seeks, launches, defeats, rules, faces, adds, enforces,
pursues, liable, names, upholds, promotes, takes, opens, refuses, leaves,
avoids. Four of the top five are about people: moves are news, not a sidebar.

GAR's standfirsts open with the actor by name (54%) or by nationality and kind
("A Spanish construction company", "An ICSID tribunal", "A Delhi court", "A UK
judge") and carry the verb in the present perfect: has ruled, has ordered, has
upheld, has rejected, has won, has threatened, has launched, has left, has
joined. "Says it has" and "reportedly" mark what is the party's own claim or a
press report rather than a document the writer has seen.

## The rules

**Structure.** One typeface, one headline size, one text size. Stories first,
then In brief, then the record lists (ICSID docket, company disclosures, the
courts, people). Nothing gets a label, a tag or an eyebrow. Six to eight
stories on a normal day; a thin day is thin, not padded. (rule)

**Headlines.** Actor, verb, object. Sentence case: only names keep their
capitals, and a common noun that belongs to a name keeps its capital (Delhi
High Court, Court of Appeal, Central Bank of Nigeria). Present tense. Six to
ten words, never more than twelve. No colon, no BREAKING or UPDATE, no outlet
name, no question, no amount. Name the State and the kind of party ("Chinese
steelmaker", "Malaysian investor", "Libyan state entity"); the forum by its
acronym when it is the point (ICSID, ICC, LCIA, SIAC); the instrument when it
is the point (ECT, NAFTA, BIT). (rule for case, prefixes and suffixes; the
model rewrites the rest)

**Explanations.** One sentence of 25 to 45 words, never cut inside a
sentence; a second sentence only when the first is short. Open with the actor
by name, or by nationality and kind, or with the tribunal or court. Then the
act, the forum, the amount with its currency ("US$235 million", "€86
million"), and one clause of context: what the dispute is about. "Says it
has won" and "reportedly" where the fact is the party's claim or a press
report. Never "significant", "landmark", "notably", "why it matters", or a
sentence about the story's importance. (rule for whole sentences and length;
the model writes the sentence)

**Sources.** The outlet name and the date after the explanation, as a link:
"— GAR, 21 September". Prefer the trade press copy of a story, then a wire,
then a major paper; other copies hang off it as "also". (rule)

**People.** A hire, a departure, a new practice head or an appointment from
the trade press is a headline like any other ("Reid leaves Debevoise for
3VB", "Willkie names two new practice heads"). The People list carries what
does not make the stories. (rule)

**Records.** A docket entry, a court judgment or a company disclosure is
printed as a record line, not as a story, unless the trade press has written
it up. (rule)

**Language.** British spelling. The vocabulary of the trade: a party is
instructed or retained; a firm acts for or appears for; the respondent is the
State; an award is rendered, upheld, set aside or annulled; a challenge
succeeds or fails; a claim is lodged, brought or threatened. Amounts as
"US$350 million", dates as "4 September 2026". Firms as they style themselves.

## Examples from the corpus

Headline and standfirst pairs from GAR's briefing, as the pattern to match:

- *Ghana liable in desalination plant dispute* — A Spanish construction
  company says it has won US$235 million in an ICC dispute with Ghana and a
  state utility over a desalination plant in Accra.
- *Italy seeks to annul Veolia award* — Italy has applied to annul an Energy
  Charter Treaty award that required it to pay €86 million to French
  environmental services group Veolia for breaching two waste treatment
  concessions.
- *Emergency arbitrator rules in Albanian airport dispute* — An ICC emergency
  arbitrator has issued an interim order in a dispute over Albania's
  termination of an airport concession, which is also the subject of a
  threatened ICSID claim.
- *Reid leaves Debevoise for 3VB* — Natalie Reid has left Debevoise &
  Plimpton, where she was co-chair of the firm's public international law
  group, to join 3 Verulam Buildings.
- *Nigeria beats Burford-backed hydropower claim* — Nigeria says it has
  defeated an ICC claim worth more than US$680 million brought by a power
  company funded by Burford Capital.
- *Romania avoids damages in wind farm dispute* — An ICSID tribunal has ruled
  that a Cypriot investor should receive no damages for changes to Romania's
  renewable energy incentives.

IAReporter headlines, which carry the whole story in the headline:

- Mining investor lodges ICSID claim against Armenia
- UK High Court enforces treaty award against commercial real estate owned by
  Nigeria in Liverpool
- French Cour de cassation confirms set-aside of award based on ties between
  tribunal chair and counsel
- Swiss Federal Tribunal upholds intra-EU renewable energy award against Czech
  Republic
