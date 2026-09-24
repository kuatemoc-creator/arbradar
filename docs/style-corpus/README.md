# Style corpus

Measured from the GAR daily briefings and IAReporter headline emails archived from the
inbox (thread ids in `index.json`; raw text stays local under `data/newsletters/`).
Regenerate with `python tools/newsletter_corpus.py`.

## GAR daily briefing

| measure | value |
|---|---|
| issues | 67 (2026-05-27 to 2026-09-23) |
| stories | 449 |
| stories per issue | median 7, p10 6, p90 8 |
| headline length | median 8 words (52 chars), p90 10 words |
| headlines naming an amount | 0.0% |
| headlines naming an institution or treaty | 16.5% |
| headlines with a colon | 2.4% |
| headlines in sentence case | 78.8% |
| standfirst length | median 32 words, p90 43 |
| standfirsts of one sentence | 97.8% |
| standfirsts naming an amount | 45.7% |
| standfirsts naming an institution or treaty | 49.2% |

Sections: Today's Headlines (301), Recent Highlights (148)

Headline verbs, most used: hires (17), wins (16), loses (14), joins (13), fails (13), launches (13), defeats (13), claims (13), seeks (12), threatens (9), pursues (9), rules (8), adds (8), liable (7), names (7), enforces (7), upholds (7), faces (7), takes (6), promotes (6), leaves (4), avoids (4), surfaces (4), launches claim (4), refuses (4)

Headline first words: US (15), Russian (13), Canadian (11), Mexico (8), Ukraine (6), Peter (6), New (6), UK (5), Hong (5), LISTEN: (5), Colombian (5), European (5), Chinese (5), Malaysian (4), Italy (4)

Standfirst openings: <Name> … (237), A (58), The (43), An <Adjective> tribunal (27), A <Adjective> court (25), An (16), The <Adjective> court (10), A <Adjective> judge (9), A <Adjective> company (6), A <Adjective> businessman (5), A <Adjective> investor (3), A <Adjective> consortium (2)

Standfirst phrases: has left (31), has asked (18), says it has (15), has upheld (14), has won (14), has launched (14), reportedly (13), has ruled (11), has joined (11), has refused (11), has ordered (11), has rejected (11), has threatened (10), has defeated (8), has dismissed (8), has found (8), has filed (7), has issued (6), has applied (5), is to (5), has opened (5), has agreed (4), has lost (4), has failed (4), has affirmed (4), has named (3), is facing (3), has granted (3), has declined (3), has enforced (3)

## IAReporter latest headlines

| measure | value |
|---|---|
| issues | 76 (2024-03-19 to 2024-07-29) |
| stories | 707 |
| stories per issue | median 9.0, p10 7, p90 11 |
| headline length | median 15 words (108 chars), p90 28 words |
| headlines naming an amount | 4.1% |
| headlines naming an institution or treaty | 42.0% |
| headlines with a colon | 7.4% |
| headlines in sentence case | 86.1% |

Sections: Latest Headlines (357), Previous Headlines (350)

Headline verbs, most used: claims (43), to hear (35), lodges (33), rules (33), dismisses (33), declines (30), files (25), upholds (24), liable (21), concludes (16), orders (12), announces (11), held (11), confirms (10), rejects (10), seeks (10), grants (9), faces (9), fails (8), sets aside (8), enforces (7), withdraws (6), refuses (5), found liable (4), ordered to pay (4)

Headline first words: ICSID (75), Tribunal (30), Three (24), In (20), UNCITRAL (19), Analysis: (15), ICC (14), US (13), European (10), Paris (10), Canadian (10), Dutch (10), South (10), Russian (9), Gazprom (9)

Headline labels: Updated (86), Analysis (71), Revealed (19), Updated with Award (18), Gazprom Round-Up (11), Looking Back (7), West Africa Round-Up (6), Uncovered (4), Investigation (4), Updated with Decision (4), Updated with decision (2), Romania Round-Up (2), UPDATED (2), Updated with Document (2), Balkans Round-Up (2), Updated with the Award (2), Libya Round-Up (2), Ecuador Round-Up (2), Updated with RfA (2), BREAKING (1)

