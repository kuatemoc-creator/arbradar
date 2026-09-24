# Style corpus

Measured from the GAR daily briefings and IAReporter headline emails archived from the
inbox (thread ids in `index.json`; raw text stays local under `data/newsletters/`).
Regenerate with `python tools/newsletter_corpus.py`.

## GAR daily briefing

| measure | value |
|---|---|
| issues | 223 (2025-10-17 to 2026-09-23) |
| stories | 1490 |
| stories per issue | median 7, p10 5, p90 8 |
| headline length | median 8.0 words (50.0 chars), p90 10 words |
| headlines naming an amount | 0.6% |
| headlines naming an institution or treaty | 18.9% |
| headlines with a colon | 2.1% |
| headlines in sentence case | 76.0% |
| standfirst length | median 32.0 words, p90 43 |
| standfirsts of one sentence | 98.3% |
| standfirsts naming an amount | 38.4% |
| standfirsts naming an institution or treaty | 45.4% |

Sections: Today's Headlines (1070), Recent Highlights (420)

Headline verbs, most used: hires (75), wins (46), promotes (43), launches (39), claims (38), joins (37), threatens (37), fails (36), defeats (36), loses (34), faces (32), brings (26), seeks (23), upholds (23), takes (23), rules (22), settles (21), enforces (18), pursues (17), adds (17), beats (15), leaves (13), refuses (13), files (12), launches claim (12)

Headline first words: US (42), UK (27), Russian (25), Canadian (22), New (22), ICSID (18), Chinese (18), Singapore (17), French (17), ICC (15), Indian (15), German (14), Dutch (14), Russia (12), Panel (12)

Standfirst openings: <Name> … (873), A (156), The (135), A <Adjective> court (99), An <Adjective> tribunal (70), The <Adjective> court (43), An (34), A <Adjective> judge (17), A <Adjective> company (14), A <Adjective> businessman (12), A <Adjective> tribunal (6), A <Adjective> investor (6)

Standfirst phrases: has left (121), says it has (56), has rejected (49), reportedly (48), has upheld (46), has filed (45), has asked (43), has ordered (38), has refused (36), has threatened (33), has defeated (32), has launched (31), has joined (30), has ruled (29), has won (27), has dismissed (27), is to (26), has opened (15), has agreed (14), has affirmed (14), has applied (11), has found (11), has failed (11), is facing (11), has hired (10), has declined (10), has annulled (10), has brought (9), has issued (8), has named (8)

## IAReporter latest headlines

| measure | value |
|---|---|
| issues | 188 (2023-10-18 to 2024-07-29) |
| stories | 1636 |
| stories per issue | median 9.0, p10 6, p90 11 |
| headline length | median 15.0 words (105.5 chars), p90 28 words |
| headlines naming an amount | 4.2% |
| headlines naming an institution or treaty | 42.7% |
| headlines with a colon | 4.9% |
| headlines in sentence case | 85.7% |

Sections: Latest Headlines (828), Previous Headlines (808)

Headline verbs, most used: claims (126), dismisses (100), to hear (98), lodges (68), declines (61), rules (53), upholds (52), files (44), concludes (44), rejects (39), liable (29), grants (28), announces (26), orders (26), confirms (21), seeks (21), held (20), refuses (16), sets aside (16), fails (12), enforces (12), denies (10), faces (10), threatens (10), wins (9)

Headline first words: ICSID (187), Tribunal (72), Three (63), In (51), UNCITRAL (44), UK (34), Canadian (27), Analysis: (25), ICC (24), US (22), European (21), Paris (21), Dutch (20), Arbitrators (18), Russian (17)

Headline labels: Analysis (195), Updated (173), Revealed (41), Updated with Award (37), Looking Back (19), Uncovered (14), West Africa Round-Up (12), Gazprom Round-Up (12), CIS Round-Up (9), Updated with Decision (8), Libya Round-Up (6), Investigation (4), Ecuador Round-Up (4), Updated with Tribunal (3), Updated with decision (2), Romania Round-Up (2), UPDATED (2), Updated with Document (2), CIS-Round Up (2), Balkans Round-Up (2)

