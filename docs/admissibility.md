# Admissibility: making "which source may support which claim" a check

Stage record. Written after the changes, including what they retroactively
invalidated in yesterday's numbers.

## The bug, named

Three measurements in a row were retracted for the same reason: a signal was used
for a claim it could not bear. The hygiene already in place did not catch any of
them, because every claim recorded its source and its coverage, and the PAIRING
of source to claim was never itself constrained. It was a discipline somebody had
to remember, and it was not remembered.

The precise logical form: existential instantiation without a uniqueness proof.
We had `exists x. P(x)` over a set of size k and treated it as a definite
description. In type-theory terms, `choice` was used where only `unique_choice`
was licensed.

## The reframe that mattered

The first diagnosis was that the discriminator is whether a claim quantifies over
a class or over an individual. That is a symptom, and as a rule it over-rejects.

The cause is **invariance**. A lookup by surface attribute is invariant under
permuting the objects that share that attribute, so a claim is derivable from it
only if the claim's truth value is invariant under the same permutation group --
only if it factors through the quotient.

The counterexample that killed the first rule, and which is now a test:

> An individuating claim about an object whose collision class has size 1 is
> perfectly admissible from the same source.

And the apparent inversion is one number in two roles, not a paradox:

| role of k | what it is | direction |
| --- | --- | --- |
| evidence for a class claim | a sample size | strength grows with k |
| evidence for an individuating claim | an anonymity-set size | exactly log2(k) bits are missing |

Both grow. For an n-ary claim the requirement is the product structure, so the
deficit is `n * log2(k)`: arity enters MULTIPLICATIVELY, not as a category. That
is why indexing admissibility by `(source, claim kind)` is not merely coarse, it
is mistyped -- admissibility depends on the k observed in the instance.

## What was built

**A resolution that carries its cardinality.** `src/flujo/substrate/resolution.py`:
`Unique | Many | Absent`. `Many` deliberately exposes no attribute that yields a
single value, because accidentally reading one candidate out of many IS the bug.
`require_unique` is the one unsound step in the system turned into a term the
caller has to supply; its error names k and the deficit in bits. `class_strength`
is exposed alongside, so the type does not forbid the legitimate class-level use.

**The resolver stopped lying.** `Substrate.resolve_external_id` ended in
`LIMIT 1` and returned `row[0] if row else None`, over a query matching
`document_id` -- which is SHARED BY DESIGN, since a shared DocumentID is what a
lineage IS. Measured: 120 DocumentIDs in this corpus are carried by more than one
state, group sizes 2 to 8, the largest being 8 reference images exported in one
batch. It now returns every match.

Both existing callers only tested presence, which is a class-level use and was
always sound. What was wrong was the SIGNATURE: it promised a single state_id, so
the first caller to actually USE the id would have built an individuating claim
on a lookup that could not individuate. `is_present` exists because a frozen
dataclass is truthy, so `if resolve(...)` would have read `Absent` as success.

**The cardinality is persisted.** `Evidence.candidate_count`, with
`individuating_deficit_bits` beside it. An edge whose object matched 8 candidates
used to look identical to one that matched exactly 1.

**The pairing is checked.** `ADMISSIBLE_PREDICATES` declares which predicates each
authority may assert, validated in `Evidence.__post_init__` and validated as a
TABLE at import time, so a bad row stops the module loading instead of waiting
for the one record that hits it. Every pair the code writes today was already
admissible, so nothing broke; the point is that the NEXT pair has to be declared.

The rule with teeth: an authority whose measurement is SYMMETRIC may never orient
an edge. A digest proves two objects are equal and equality has no direction. A
graded overlap score is the first thing that would violate this, because the
temptation with a partial-content measure is to read it as "B came from A". The
operator is the single exception -- a human orienting an edge from judgement is
the one audited downgrade, and it is visible as such.

**A completeness verdict must carry a proof.** `negative_is_evidence` rested on a
hand-written table entry, which is a closed-world assumption presented as a
measurement. Verdicts now distinguish ASSERTED from YES, and a `Witness` requires
both a normative spec citation and an adversarial check with the file count it
covered. Nothing in the table has one yet, and each entry names the check that
would earn it.

## What this invalidated in yesterday's report

Yesterday: "23367 of 24478 files (95.5%) vocabulary-complete, so only those zeros
are evidence."

Today, honestly: **zero of them**, because no format carries a witness. No
negative result from the XMP scan is evidence of absence, for any format. The
95.5% was an assertion propagated as a measurement.

Confirmed on real data, not only in the type: a fresh scan of 9000 files reports
`vocabulary_yes = 0` and `negative_is_evidence = 0` in every extension bucket,
including the 7948 PNGs whose specification really does define exactly one place
for the packet. A spec citation is half a witness; nobody has run the other half.

That is the third time this instrument has refuted its author, and the largest.
It should not be re-graded back to restore the number.

## Honest limits of what was fixed

The ambiguity guard is **preventive, not a repair of an active bug**, and this is
now measured rather than assumed. Over a real scan of 9000 files producing 8918
states and 18808 edges:

| | |
| --- | --- |
| edges with an ambiguous referent (k > 1) | **0** |
| instanceIDs carried by more than one state | **0** |
| instanceID equal to another state's documentID | **0** |
| instanceID equal to another state's originalDocumentID | **0** |
| documentIDs carried by more than one state | present, as expected: that is what a lineage IS |

So the guard cannot fire in the current pipeline, and the reason is exact:
instanceIDs are globally unique in this corpus, the ambiguity lives entirely in
documentID matching, and no edge resolves against a documentID. It goes live the
moment an edge points at a state selected by a shared documentID -- which is
precisely what a "same lineage as that state" edge would do.

## The general form, so the series stops

The asymmetry rediscovered five separate times is not a theorem about this
codebase. Observable propositions form a frame, not a Boolean algebra: verifiable
is open, refutable is closed, and the opens are closed under finite conjunction
and arbitrary disjunction but NOT under negation. Rejection propagates because
each rejection is an independent finite witness and their union stays sound;
acceptance would need conjunction over an unbounded set.

Consequences that are now knowable in advance rather than after measuring:

- A cheap test can only accelerate the side that has witnesses. The deleted
  64 KiB tail stage was built to accelerate ACCEPTANCE, which has none, so it was
  doomed by construction -- and indeed it resolved 0 distinctions over 4104
  assets for 197 MB of reads.
- Any test reading `o(n)` bits can only reject objects that are FAR apart.
  Near-duplicates are provably invisible to it, and near-duplicates are exactly
  what a shared weak hash selects for.
- The inversion in the first section is polarity: an over-approximation of S is an
  under-approximation of not-S. It is a fact about the sign of the predicate, not
  about the source.
- Combining sources is a product experiment and is SUPER-additive. Two sources
  that individuate nothing alone can individuate perfectly together, so a rule
  that takes the meet of resolutions is sound but will forbid legitimate joint
  individuation. No such rule was added here for that reason.

## Still unknown

- PNG witness work must cover both observed containers: iTXt and legacy tEXt
  keyed `XML:com.adobe.xmp`. Extension-named sidecars that are not PNG data and
  malformed PNGs remain outside the valid-file count; neither is silently
  treated as a clean negative. The 2026-08-24 full pass found 0 markers outside
  those containers in 14.327 readable files, but 17 sidecars and 1 truncated
  PNG kept the full 14.345-candidate witness ineligible.
- Whether the class-level use of basename evidence should carry its k on the
  record the way an edge now does. It is sound, but its strength is unrecorded.
