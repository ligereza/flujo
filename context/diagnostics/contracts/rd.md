# RD diagnostic contract

Use this packet for RD packs, quotes, riders, plano, venues, productoras,
logos and RD database reads.

Read only the routed RD modules, the relevant web panel and the named fixture.
Prefer GET-only or pure render checks. Do not upload, mutate SQLite, call live
providers or expose RD media while diagnosing.

Suggested branch: `rd/<short-slug>`.
