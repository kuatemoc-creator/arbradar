# Style corpus

Measured from the GAR daily briefings and IAReporter headline emails archived from the
inbox (thread ids in `index.json`; raw text stays local under `data/newsletters/`).
Regenerate with `python tools/newsletter_corpus.py`.

## GAR daily briefing

| measure | value |
|---|---|
| issues | 239 (2025-10-09 to 2026-09-23) |
| stories | 1595 |
| stories per issue | median 7, p10 5, p90 8 |
| headline length | median 7 words (50 chars), p90 10 words |
| headlines naming an amount | 0.7% |
| headlines naming an institution or treaty | 19.0% |
| headlines with a colon | 2.3% |
| headlines in sentence case | 76.3% |
| standfirst length | median 32 words, p90 43 |
| standfirsts of one sentence | 98.3% |
| standfirsts naming an amount | 38.2% |
| standfirsts naming an institution or treaty | 46.3% |

Sections: Today's Headlines (1140), Recent Highlights (455)

Headline verbs, most used: hires (75), wins (53), launches (44), promotes (43), fails (41), joins (39), claims (39), threatens (38), loses (36), defeats (36), faces (34), seeks (28), brings (26), upholds (24), rules (23), settles (23), takes (23), enforces (20), pursues (17), adds (17), beats (15), refuses (14), leaves (13), files (12), opens (12)

Headline first words: US (42), UK (33), Russian (25), New (24), Canadian (23), Chinese (22), Singapore (19), ICSID (19), French (17), Russia (16), Dutch (16), ICC (15), Indian (15), German (14), Hong (13)

Standfirst openings: <Name> … (930), A (170), The (144), A <Adjective> court (100), An <Adjective> tribunal (79), The <Adjective> court (53), An (34), A <Adjective> judge (20), A <Adjective> company (14), A <Adjective> businessman (12), A <Adjective> tribunal (6), A <Adjective> investor (6)

Standfirst phrases: has left (125), says it has (59), has upheld (54), has rejected (53), reportedly (49), has asked (46), has filed (45), has ordered (38), has refused (37), has ruled (35), has threatened (34), has launched (33), has joined (32), has defeated (32), has won (29), has dismissed (28), is to (27), has opened (17), has affirmed (16), has agreed (15), has failed (13), has hired (12), has applied (11), has found (11), is facing (11), has declined (10), has annulled (10), has brought (9), has issued (8), has named (8)

## IAReporter latest headlines

| measure | value |
|---|---|
| issues | 190 (2023-10-18 to 2024-07-29) |
| stories | 1650 |
| stories per issue | median 9.0, p10 6, p90 11 |
| headline length | median 15.0 words (105.5 chars), p90 28 words |
| headlines naming an amount | 4.3% |
| headlines naming an institution or treaty | 42.7% |
| headlines with a colon | 4.8% |
| headlines in sentence case | 85.8% |

Sections: Latest Headlines (834), Previous Headlines (816)

Headline verbs, most used: claims (126), dismisses (102), to hear (98), lodges (68), declines (63), rules (53), upholds (52), concludes (46), files (44), rejects (39), grants (29), liable (29), announces (26), orders (26), confirms (23), seeks (22), held (20), refuses (16), sets aside (16), fails (12), enforces (12), denies (10), faces (10), threatens (10), wins (9)

Headline first words: ICSID (187), Tribunal (72), Three (63), In (54), UNCITRAL (44), UK (34), Canadian (27), Analysis: (25), ICC (24), US (23), European (21), Paris (21), Dutch (20), Arbitrators (18), Russian (17)

Headline labels: Analysis (198), Updated (173), Revealed (41), Updated with Award (37), Looking Back (20), Uncovered (14), West Africa Round-Up (12), Gazprom Round-Up (12), CIS Round-Up (9), Updated with Decision (8), Libya Round-Up (6), Investigation (4), Ecuador Round-Up (4), Updated with Tribunal (3), Updated with decision (2), Romania Round-Up (2), UPDATED (2), Updated with Document (2), CIS-Round Up (2), Balkans Round-Up (2)

