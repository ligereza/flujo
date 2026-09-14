# Ordering a chaos of files: one model's reasoning, and its errors

The operator asked for this document by name. Not the conclusions -- those are in
`context/LAST_HANDOFF.md` and in the commit log. What he asked for is the
reasoning and the mistakes, so that the record itself becomes a logic of what a
model actually does when it is handed 940 GB it has never seen, and of how it
gets to an order without opening every file.

It is written first-person because attributing the errors to "the system" would
destroy the only thing that makes it useful. Every error below is one I made in
this repository, most of them within a single week, several of them after being
warned.

The companion to this file is `data/ordering_features.json`, which turns Part B
into something code can consult before letting a feature decide anything.

---

## Part A -- the errors, grouped by class

A list of mistakes teaches nothing. The class is what generalises, so each error
sits under the class that produced it.

### Class 1 -- taking a name for the thing

This is the largest class by a wide margin, and it is the one that nearly did
real damage.

**`research/corpus/bf4453cd0709-18029801425410081.md`.** I read the filename --
a hash, a dash, an epoch-looking number -- and concluded: machine-generated
corpus, not authored proposals. I was one step from recommending the operator
dismiss 1599 rows in a single stroke. Opening ONE file showed a per-artwork
record of his own archive, with concepts, palette, technique, a research line and
a suggested code direction. The name was the cheapest feature available and I let
it make an expensive decision.

**`('Slice 1', 1920, 1080)`.** I built a rig signature from Resolume slice names
plus canvas size and got three false positives. That triple is Resolume's DEFAULT
name and DEFAULT canvas: it is what the file says when the operator has not said
anything. The feature carried no information at all and I weighted it as though
it did. The fix was not an exception list, it was classifying the name
(`NAME_TOOL_DEFAULT` / `LOW_ENTROPY` / `OPERATOR`) so the representation itself
knows when a name is silence.

**`LOGO ENTREGA`, `la ferrari`, `golden`.** I called roughly 8 of LYON's 24
subprojects "tool artifacts" from their names alone. Some of those calls were
right. `la ferrari` turned out to coincide with a downloaded 3D car model
(`uploads_files_2475145_la+ferrari`) -- so the conclusion survived, but for a
reason I had not established. Being right by luck is not being right.

**`MERECEDORA`, `CDR`, `Pajsaera`.** These sat in my open-questions list for
days. They are song titles: *La Merecedora* (Lyon la F ft. Nacho G Flow,
2025-12-04), *La Ciudad del Reggaeton* (track 01 of DrefQuila's *Despues del
Sol*, 2025-10-02), *Pasajero* (Lyon la F, 2025, and the folder name is
misspelled). `01 CDR.mov` -- 15.77 GB I had labelled "I do not know what this
is" -- was a track number followed by an initialism.

Put those last two items together and the real lesson appears. The folder name
was the *weakest* feature in three cases and the *strongest* in the fourth. A
name is not reliable or unreliable in general. **A name is only as strong as the
external authority that can refute it.** With a discography to check against, the
name is the best key on the disk. With nothing to check against, it is noise
wearing a label.

And the authority cost one web search. It was available the entire time.

### Class 2 -- taking the container for the content

**"Four bodies of work are bridged into Project IR."** Two were. I had counted
`reconstruction.json` files on disk and reported it as rows in the database.
`FELINA/LOGO` and `BAHPARTY/bah` had never been imported.

**I wrote a venue proposal into `data/venues/`** and broke `venue.py validar`
with eight schema errors, because `cargar_todos()` globs `*.json` in that
directory. I treated a folder as a namespace when it was a load path. Proposals
now live in `data/venues_propuestas/`.

**I called ScreenSetup output "the venue's projection topology."** Then I
measured `BERLIN 1.xml` against `berlin 2.xml`: the same room, 59 surfaces
against 9, canvas 3043x272 against 1920x1080, ZERO shared surfaces. The file is
named after a venue and describes a *dated deployment* -- what was rigged that
night. The container's name was not the thing's identity.

### Class 3 -- trusting my own derived output as if it were input

**I published derived artifacts generated from a dirty worktree.** CI went red on
`origin/main`. The artifact looked like a fact and was a shadow of an uncommitted
state.

**My own gate mutated the repository.** Invoking tools marked VIVO with no
arguments -- to check that they run -- regenerated a protected SVG asset and
degraded a gitignored 1.79 MB index down to 11 KB, breaking four tests. I built a
checker that changed the thing it was checking. The gate now asks `--help` only.

**I validated a "clean clone" with `git archive`,** which produces a tree with no
`.git`, and got seven spurious failures from gates that need git. My harness was
measuring my harness.

### Class 4 -- fixing an instance and calling it a class

**The entry gate enumerated only tracked files,** so a brand-new file passed the
local check unseen and failed in CI once it was already committed. What makes
this a Class 4 error rather than a bug: `test_higiene_docs.py` had documented
that exact failure in its own docstring weeks earlier ("cuatro README
vendorizados pasaron el pytest local y tumbaron el CI") and resolved it with a
manual workaround -- remember to `git add` first. A workaround that lives in
someone's memory fails again. I nearly fixed only the second instance.

**`shared_resource` meant two different things** in one vocabulary: a symmetric
claim about two container roots, and a directed claim about an owner and its
resource folder. I could have written an inference to recover the direction from
the path shape. Defining the vocabulary instead (`shares_library_with` for the
symmetric one) was the right move, and the operator had already told me why:
"es mas facil definir que esperar que un codigo sea perfecto."

### Class 5 -- over-correcting

**After being wrong that the corpus was junk, I swung to calling it "material de
postulacion de primera linea."** Also wrong. Those files carry `percibido` -- a
model's reading of an image -- and of 1818 such entries, ZERO carry `resumen`,
the author's own sentence. A correction that overshoots is a second error, not a
repair. The truthful statement is narrow: the corpus is an excellent *index into*
the registro and carries no authorship.

**I called two of three lead proposals "garbage,"** then went back and found the
draft already showed the sponsor handles and already said "PR humano, NO escribir
directo". I had criticised my own correct output. Self-correction is not free;
performed reflexively it destroys accurate work.

### Class 6 -- answering a compound question as if it were simple

**8273 rows, four question templates, zero answers, and the reason was in the
question.** "python implementation requires purpose and consumer classification"
bundles two questions whose natural units differ. Purpose is a function of
content; consumer is a function of position. The proof is in the data: 44 of the
queued files are ZERO-byte `__init__.py` -- byte-identical, so identical purpose,
sitting in 5 different trees, so different consumers. Bundled, the cheap half is
held hostage by the expensive half 8273 times. And I spent my first effort on
*how many answers are needed* before asking *what is being asked*.

**I fitted the operator's taxonomy into one tree.** It is five independent axes
(what it is / dimension / for whom / web destination / entity type), and a single
Instagram carousel breaks any tree: image 1 is the work, 2..n may be exercises or
backstage, and one concept crosses all of them. A post is not a class. It is a
container holding several.

---

## Part B -- the logic that falls out

### B.1 A feature is defined by its cost and its refutability, not by its accuracy

Accuracy is not a property a feature has on its own. Cost and refutability are,
and they are what a system can reason about before committing.

| feature | cost | refutable by | may decide | may NOT decide |
|---|---|---|---|---|
| filename | free | an external authority, if one exists | nothing on its own | anything, alone |
| path / container | free | the load path, the schema | provenance | meaning |
| byte-identical hash | cheap | nothing, it is proof | identity | purpose, consumer |
| structural anchor (`.blend`, `.aep`, `.svg`) | cheap | the file's own existence | technique, dimension | authorship |
| declared marker (`pyvenv.cfg`) | cheap | the spec that requires it | provenance class | value |
| geometry (SVG paths, `.blend` objects) | medium | comparison against another work | relation between works | intent |
| vision description of pixels | expensive | nothing | nothing above a low confidence | anything, alone |
| human attestation | most expensive | the human | authorship, publication, value | -- |

Two rows in that table carry most of the weight of this whole document.

**`pyvenv.cfg` is cheap AND provable.** PEP 405 requires the interpreter to write
it at an environment root; `sys.prefix` is derived from it. Testing for that one
file settled 1463 queue rows -- 17.7% of the entire queue -- that a hand-written
list of directory names had missed, because the real directory was called `env`
in a Windows layout nobody had thought of. A definition beats a list, always, and
it costs one `stat`.

**Pixels plus a model's description is expensive AND unrefutable.** This is why
the operator's instinct about SVG is the deepest thing in the design. A JPEG
holds pixels and whatever a model *claims* to see in them. An SVG holds named
paths and geometry; a `.blend` holds objects, materials and collections. Those
are structured features, comparable *between works with no model in the middle*.
Geometry can be checked. A description cannot, and must therefore never carry the
same confidence as a match.

### B.2 The rule that would have prevented most of Part A

**Never let a free feature make a decision that an authority could refute,
without first consulting the authority.**

Both authorities I eventually used were available from the first hour:

- a discography lookup, one web request, turns `MERECEDORA` from "unknown" into
  a title with a release date;
- a `pyvenv.cfg` test, one `stat`, turns 1463 rows from "needs a person" into
  "installed by a package manager".

Neither required intelligence. Both required asking whether something outside my
own reasoning could say I was wrong.

### B.3 How to order thousands without reviewing one by one

Four moves, cheapest first. Each exists because a specific error in Part A taught
it, and each is falsifiable.

**1. Subtract what is not a question.** Of 8273 rows, 4029 carried a repeatable
check: 1463 inside a proven virtual environment, 2566 byte-identical to a file
already in the live repository. Ranking anything before this subtraction wastes
the ranking on rows that never needed it.

**2. Fold by the equivalence relation that is valid for THIS half of the
question.** Content identity is valid for purpose and invalid for consumer.
Directory is valid for project and invalid for route. Release date is valid for
chronology and says nothing about technique. Folding by the wrong relation
produces a confident wrong answer at scale, which is worse than no answer.

**3. Order by what one answer settles, and name which answer pays.** Containment
gives real leverage -- 36 pending project records collapse to 8 root questions --
but only for a REJECTION. A folder that is an After Effects Auto-Save cannot hold
a delivered work, so rejecting the container settles its contents. A real work
holds working material, so accepting it settles nothing below. Calling that
"leverage" instead of `rejection_leverage` promises a saving that only one of the
two answers delivers.

**4. Attach an external authority wherever one exists.** This is the only move
that turns a name into knowledge, and it is the one I missed longest. It also
produces the join between the two orders on this disk: the SSD records *how a
work was made* (940.7 GB, 45,536 assets, keyed by client), Instagram records
*that it was shown* (5.83 GB, 7,321 files, keyed by date and surface), and the
track's release date is the key that binds them. Neither contains the other.

### B.4 What must never be automated, and why the numbers say so

- **Authorship.** Of 2034 pieces in the iskvw archive, 216 carry a human title
  and only 8 carry both a date and the author's own sentence. 1818 carry a
  machine's `percibido` and nothing else. No quantity of perception manufactures
  the missing 2026 statements of intent.
- **Publication.** Every post and reel is a work; whether it goes on the web is
  the operator's decision, and the portfolio interface exists for exactly that.
- **Strengthening a weak concept.** Relating a weak concept to strong ones can
  *fabricate* a concept that was never there. If the concepts are drawn from
  `percibido`, the result is interpretation stacked on interpretation and cannot
  be falsified. A concept lattice needs a seed of author-declared concepts, or it
  is a rumour engine with good typography.

### B.5 The one measurement that says whether MAK learned anything

Not accuracy on decisions it has already seen. That number always looks good.

**Hold out the operator's own decisions and measure whether the system predicts
them.** Report the abstention rate alongside it: a system that abstains on half
the queue and is right on the rest is more useful than one that answers
everything at 70%, because the first can be trusted where it speaks.

If it cannot predict held-out decisions, it has not learned, and saying so is the
result. Every single error in Part A was available to be caught by exactly this
discipline -- a prediction checked against something outside itself.

---

## How to use this file

It is append-only. A new error goes under its class, or opens a new class if it
genuinely does not fit; rewriting an old entry to look better destroys the only
value here. When an error turns out to have been a correct call for the wrong
reason, that gets recorded too -- `la ferrari` is in Class 1 for exactly that.

The machine-readable half is `data/ordering_features.json`. Code that is about to
let a feature decide something should consult it and abstain when the feature's
declared authority is absent.
