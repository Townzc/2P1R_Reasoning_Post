# Constructive task review: multiplicity is feasible; strategy diversity is not automatic

**Prospective CPU design memo, 2026-09-09.** This review reads the required
project documents and the completed E010 report. It does not create a new
dataset, run a model, contact a server, inspect the reserved holdout, or change
the protocol. Proposed counts and thresholds below are design gates, not
measurements. A broad redesign merits Ultra-level review; this is a
recommendation, not a settings change. Publication and cumulative records are
the coordinating agent's responsibility.

**Decision:** provisionally select *finite-permutation relation transport* for
a bounded CPU falsification prototype. It guarantees alternative supporting
fact routes without rare arithmetic support filtering and admits strong
information-theoretic shortcut checks. It is suitable for the narrower question
of **within-question evidence-route diversity under a shared reasoning
algorithm**. It is not yet a replacement benchmark for diversity of semantic
strategies. If the original strategy-level claim must remain unchanged, none
of the candidates below has passed that requirement; do not quietly relabel
routes or edge orientations as strategies.

E010 motivates this distinction, not a new positive hypothesis selected from
model scores: the primary is 7/64 versus 5/64, complete traces 4/64 each, and
broader results 0/64 versus 2/64. Although both arms use the same 128 questions,
the population and dose differ from earlier pilots. The declines do not
identify an identity-removal effect. The remaining 1460 GPU seconds do not
authorize or reserve another current capped pair.

## Candidate comparison

| Family | How multiplicity is guaranteed | Main attraction | Fatal or unresolved objection |
|---|---|---|---|
| Arithmetic identity expansion | Generate an expression and several algebraically equivalent forms, such as a factored and expanded polynomial. | Genuine algebraic operations and independent exact-rational checking. | Commutative/associative rewrites often collapse to one equivalence class; distributive forms change operation count, repeated-input use, magnitudes and length. Padding with neutral arithmetic recreates the earlier nuisance. It is no longer the original use-each-input-once task. |
| Arithmetic planted equal solutions | Choose free inputs and solve constraints that make several expressions equal the same target. | Can preserve expression-construction format in selected cases. | Integer/divisibility constraints reintroduce support filtering. Permitting arbitrary rationals removes that filter but produces structured denominators and a changed population. Simple templates often expose a constant target or low-dimensional identity. No general full-support construction with four non-AC classes and equal cost is established here. |
| Plain graph reachability with four planted routes | Build four source-to-target branches. | Immediate full support; simple solver. | If every query asks whether the planted target is reachable, “yes” is perfect. Equal branches are mutually isomorphic; different fact IDs do not establish different structures or algorithms. Reject as the primary final-answer task. |
| **Permutation relation transport** | Consistent edge maps derived from latent node permutations; build four routes to a hidden, balanced terminal state. | Full support, noncommutative composition, fixed primitive costs, independent solver, balanced answers and exact local-information null. | All routes still instantiate one transport algorithm. Multiple routes measure alternative evidence use. Orientation differences are representation choices. Select for CPU audit only with that scope explicit. |
| AND/OR proof networks with transport and set intersection | Plant several different proof DAGs for one latent state using a declared rule library. | Could supply genuinely different dependency skeletons, not just alternate chains. | The easy branch may reveal the answer; AND arity, proof length, depth and information exposure are coupled. Completeness, matching and shortcut guarantees have not been established. A separate candidate, not an automatic fallback after the simpler task fails. |

Arithmetic is not rejected as a domain. The specific claim that arithmetic
identities immediately solve the old support and semantic-control problems is
rejected. Keeping the earlier arithmetic study as a documented boundary is
preferable to silently redefining its task until matching succeeds.

## Concrete provisional construction

Let the state alphabet be `A,B,C,D,E`. Each node has a hidden permutation
`h_v` of these five states. For an exposed directed edge `u -> v`, show the
complete five-entry lookup table for

`pi_uv = h_v composed with inverse(h_u)`.

The prompt supplies a source node `s`, its state `x`, and a target node `t`.
The answer is the state

`y = h_t(inverse(h_s)(x))`.

An edge can be traversed forward by lookup or backward by inverse lookup.
No hidden permutation, route index, generator seed, gold answer, construction
order or solver certificate appears in the input. Opaque node and edge names
and row order are independently randomized after the semantic instance is
constructed. Lookup tables must be actual permutations; arbitrary inconsistent
tables define a different task.

Start with four internally vertex-disjoint `s`–`t` chains, each containing
`L=4` edges. Each supporting route then has exactly four required facts and
four state transitions. The four routes use disjoint edge sets. The clean IID
generator draws `x`, `h_s`, `h_t` and all other node permutations independently
and uniformly, then computes `y`. It has exactly uniform population answer
probabilities; a finite sample need not have equal class counts.

An equivalent single-query sampler draws `x` and `y` independently and uniformly,
draws `h_s` uniformly, and draws `h_t` uniformly from the `4!` permutations that
map `inverse(h_s)(x)` to `y`. Other node potentials remain IID uniform. Averaging
over the five possible `y` values restores the original uniform distribution
over all `5!` endpoint permutations. This is direct conditional sampling,
not rejection of solved problems.

For exact finite audit quotas, one can allocate equally many examples to each
of the 25 `(x,y)` pairs and independently sample from those conditional laws,
then randomly shuffle. A random single record has the same marginal law, but
the dataset's labels are **not jointly IID**: observing other labels can reveal
a remaining quota. The gauge statement below is a single-query distributional
property, not a claim conditional on an entire quota-balanced dataset. Keep
quota labels, index/stratum IDs and construction order private to the generator;
fix quotas separately inside each split. Prefer IID semantic draws for the main
scientific population unless a stratified estimand is explicitly registered.

For an initial representation stress test one could orient each route according
to `FFBB`, `FBFB`, `FBBF`, or `BFFB`; each has two forward and two inverse
lookups. These orientation words are **not semantic families**. Replacing an
edge table by its inverse and reversing its written direction preserves the
same relation. If robustness to this rewrite is desired, family labels must be
defined after quotienting out the rewrite, at which point these chains have
one structural family. Plain all-forward routes are an equally honest initial
route-diversity task. Freeze one convention before examining prototype probes.

Every response names the four used edge IDs and visited node/state pairs,
followed by the final state. The independent verifier accepts any legal
source-to-target certificate, including an unlisted route if later graph
extensions create one. It does not require an exact gold string or a stored
reference membership test. Enforce a simple route and exact declared length
for the narrow certificate endpoint; separately report unconstrained valid
certificates if a richer topology is introduced.

Do not remove identity permutations or state-preserving transitions after
generation. Their occurrence is a recorded property, not a failure of
support. In particular, forcing all five visited states to be distinct can
create a missing-symbol shortcut: after four states the fifth is determined
without reading the last edge. Removing neutral transitions would also change
the conditional information structure and invalidate the simple guarantee
below. The finite alphabet already bounds numerical complexity.

### Properties established analytically

1. **Four valid certificates exist for every generated query.** Multiplying
   consecutive maps telescopes to `h_t inverse(h_s)`, irrespective of the
   chosen branch. No search for a fortunate support intersection is required.
2. **The answer is unique on consistent inputs.** Any walk connecting the
   endpoints gives the same map; cycles compose to the identity. With uniform
   endpoint potentials, each terminal state has probability one fifth.
3. **A valid-answer guarantee does not reveal the answer.** An always-fixed
   state baseline has expected accuracy 20%, unlike an all-positive reachability
   task. This says nothing about the difficulty of finding a certificate.
4. **Disconnected edge observations carry no answer information.** For any
   fixed subset of exposed edges whose subgraph leaves `s` and `t` disconnected,
   the terminal state remains uniform conditional on those tables and `x`.
   Right-compose every latent permutation in the target's observed connected
   component with an arbitrary common permutation. All observed internal edge
   tables remain unchanged, while the endpoint state ranges uniformly over the
   alphabet. Thus fewer than `L` edge observations cannot reveal `y` in this
   topology. This assumes uniform unconstrained potentials and independent
   rendering; extra rejection or label-dependent topology can break it.
5. **Support diversity is real but algorithm diversity is absent.** The four
   certificates use disjoint facts and can disagree under interventions to
   individual routes. They nevertheless execute the same lookup-composition
   procedure. Noncommutative permutations prevent free reordering of operations;
   they do not create four distinct cognitive strategies.

These are properties of the specified mathematical generator, not proof that
an implementation or trained model obeys them.

## Independent solver and adversarial verification

Use two implementations with different representations. The generator stores
permutations and constructs edge tables. The solver sees only the serialized
question and performs reachability in the lifted state graph: each table entry
adds `(u,a) <-> (v,pi_uv(a))`. Starting from `(s,x)`, collect all reachable states
at `t`. Exactly one gives the promised-input answer, zero means undetermined,
and more than one means inconsistent evidence. This solver needs neither
latent potentials nor planted path metadata. An independent trace verifier
checks each table row or column directly, consecutive endpoints and final
state; it should not call the generator's permutation-composition helper.

Separately enumerate all simple source-to-target paths for the bounded graph,
count their lengths and edge-support sets, and quotient them by the declared
symmetries. Four stored references alone are insufficient to establish either
completeness or four non-equivalent structures. Use exact graph isomorphism
where needed; a hash or Weisfeiler–Lehman fingerprint alone is not a collision
proof. Verify inversions against a direct table scan, not the same inverse
routine used for generation.

Finite fixtures should include every five-state permutation and its inverse,
all source states, both edge directions, identity maps and noncommuting maps;
malformed tables, unknown edge IDs, repeated/cyclic certificates, skipped
endpoints and incorrect intermediate states must fail correctly. One solver
disagreement blocks the scientific dataset, even if a majority of cases pass.

## Controls that can falsify the construction

| Control | Expected answer/certificate behavior | What failure would reveal |
|---|---|---|
| Rename entities and edge IDs; independently shuffle facts | Answer unchanged; translated certificate valid. | ID/order/template leakage or brittle parsing. |
| Apply one common bijection to state symbols, including every table row/column and the source state | Answer and certificate states transform by the same bijection. | Dependence on fixed answer symbols rather than relations. |
| Reverse any written edge and replace its table by its inverse | Same answer and evidence relation. | Treating orientation as a semantic family; representation shortcut. |
| Change source state only | The terminal state changes according to the full endpoint permutation; distinct source states yield distinct outputs. | A generator that leaks a fixed target label or a solver that ignores the query state. |
| Change `h_t` to `rho composed with h_t`, updating **all** incident tables coherently | New answer is `rho(y)`; topology, degrees, route count and length stay fixed. | A baseline using topology, IDs or earlier route prefixes. A single altered edge is not this consistent counterfactual. |
| Remove one route and replace its facts with matched distractor facts | Answer unchanged if another route survives; the removed certificate is invalid. | Gold-list scoring, nonexistent evidence use, dependence on a preferred branch. This is a boundary diagnostic, not a same-K training example. |
| Query across two disconnected but otherwise matched components | Solver returns undetermined; no positive certificate exists. | An always-produce-a-state verifier or hidden access to generator labels. Match component count/size in positive controls too. |
| Corrupt one route so its endpoint differs from the other three | Solver detects inconsistent evidence; two conflicting certificates witness it. | Failure to distinguish a locally valid route from globally consistent input. |

Disconnected and inconsistent cases are required **CPU solver negative
controls**. They are not silently added to the main SFT distribution. Testing
models on contradiction detection requires an explicitly framed auxiliary task,
appropriate instructions and a common training/control policy: a model trained
to give one certificate on promised-consistent inputs has not been trained to
check every route. Do not change the primary endpoint to contradiction detection
after seeing outcomes.

For shallow probes, predeclare answer priors, source-state-only, node/edge IDs,
degrees, table histograms/bags, position features, terminal-incident facts,
source-incident facts, and bounded-radius neighborhoods. Include nearest
template retrieval, a shortest valid-route solver, and fixed-branch preference.
The first group tests leakage; a shortest-route solver is a legitimate task
solver and a simplicity diagnostic, not a cheating baseline. A table-bag probe
can observe all edges, so the disconnected-subgraph theorem does not cover it.

## Population, splits and matching

Assign the semantic base instance and its entire rename/reorder/inverse-edit/
counterfactual orbit to a split **before** rendering or path augmentation.
No relabeling of a training graph can count as an independent development
example. Check node-renaming isomorphism and state-alphabet conjugacy when
building orbit keys; store direct witnesses for suspected duplicates. Do not
inspect or repurpose the old reserved arithmetic holdout.

There is a severe limit: four length-four parallel chains form a single
unlabeled topology. Disjoint random tables are new instances of one algorithmic
template; a random IID split cannot be described as topology generalization.
Separate claims explicitly:

- IID: unseen semantic table assignments on the fixed topology, split by full
  instance orbit. This tests new compositions under an already known template.
- Controlled depth boundary: reserve selected longer chain lengths before data
  generation; report depth separately from route count and prompt length.
- Topology boundary: requires a new graph family with nontrivial rooted
  topology groups. Label-only renaming and direction rewrites do not provide it.
  The four-chain prototype cannot pass this gate by itself.

Keep `K=4` available routes and `L` fixed in the initial allocation comparison.
Both arms receive the **identical prompts** containing all four routes. Paths
receives each of four certificates; GCM receives one assigned certificate four
times. Any distractors are shared. Route count, solvability and graph difficulty
therefore do not differ between arms. Varying available K would be a separate
task-difficulty intervention, not the allocation effect.

All routes have the same algorithmic structure. For this narrowed task,
global structural coverage is already identical; any exact orientation
histogram control is only a rendering/primitive-position control. If orientation
templates are retained, assign GCM paths with a seeded Latin permutation over
four-question blocks and use the corresponding Paths Latin rounds. Hold
question order, number of presentations, updates, microbatches and tokenizer
fixed. Randomize GCM route assignment independently of labels and template
group, with paired seeds planned before model outcomes.

Exact token equality must be demonstrated on the pinned tokenizer's full
serialization, including EOS. Equal character count and fixed-width IDs are
not evidence of equal token counts. Preselect a finite, context-verified symbol
and identifier codebook; do not solve token mismatches by removing hard
questions, adding meaningless proof steps, or truncating. Context-dependent
tokenization may still defeat this scheme. If so, record failure and review
block-total matching or a new serialization as a changed design. Match and
report path-level forward/inverse operations and neutral transitions; the
latter can remain unequal per question under fixed-single-route allocation,
so do not claim all trajectory features are held fixed.

## Bounded CPU acceptance and rejection gates

The following is a proposed, prospective audit budget, not permission to train.
Freeze one generator version and audit seed list before running it. A useful
finite target is 10,000 sandbox instances, covering at least 100 independent
semantic seeds and balanced states, plus the exhaustive small fixtures above.
These are disposable construction-audit cases, not the scientific train/dev/
test population. Any cap or deadline failure remains an incomplete attempt.

1. **Support and correctness:** require 100% of valid draws to have the promised
   unique answer and four certified edge-disjoint length-L routes; zero
   generator/solver/verifier disagreements; 100% correct metamorphic and
   corrupted-input fixture outcomes. Report every rejected draw and its cause.
   Any semantic filtering to obtain support fails the proposed full-support
   design. Serialization errors should fail the generator, not become hidden
   population filtering.
2. **Symmetry honesty:** enumerate the small topology's equivalence classes
   under entity renaming and inverse-edge rewriting. Accept one algorithmic
   template for the narrowed route estimand; reject any claim of four semantic
   strategies if only one remains. Reject a topology-OOD claim on this prototype.
3. **Leakage:** require exact planned answer balance, no cross-split orbit
   collisions, and observed metadata/prohibited-information probes near their
   20% chance baseline. A predeclared operational tripwire is an upper 95%
   binomial confidence bound above 25% on an independent 10,000-case probe test
   set for a supposedly uninformative probe. Use multiple-comparison accounting
   and disclose all probes. Passing this finite tripwire is not proof that all
   shortcuts are absent. The theoretical conditional-independence property
   must also survive the actual sampler and renderer.
4. **Causal sensitivity:** all coherent endpoint and source-state edits must
   change the independent gold answer as specified; all pure re-renderings
   must preserve it. Broken-route references must be rejected while surviving
   certificates remain valid. Fail on any accidental direct edge or shorter
   route below the declared depth.
5. **Budget feasibility:** establish exact response/update/exposure matching
   and report prompt, padding and forward-pass costs from the pinned tokenizer.
   Require full retention of the semantic audit population. A convenient
   equal-token subset is a failure of the proposed construction, not a pass.
6. **Scientific scope:** CPU success qualifies only the sampler/controls.
   It does not establish learnability, useful difficulty, an effect, novelty,
   statistical power or ICLR readiness. A separately reviewed model-capability
   calibration and an adequately powered independent-pool/seed design are
   prerequisites for a scientific comparison. Do not use old development
   outcomes to select alphabet, depth, templates or the final endpoint.

The proposed probe threshold is an engineering screen, not a publishable
equivalence margin or power calculation. The 10,000-case budgets and confidence
procedure must be finalized consistently before implementation; the same cases
must not be used both to fit probes and to report their generalization.

## What would change the decision

Proceed with the relation-transport CPU prototype if the owner accepts the
narrow evidence-route estimand. Reject it as an unchanged semantic-strategy
experiment even if every engineering gate passes. If a richer rule-DAG family
is pursued, first prove that its alternatives survive renaming, inverse
rewriting, associativity, shared-premise and proof-order equivalences; that
every required source fact matters under controlled edits; and that exact
exposure matching does not depend on a rare subset. These are new obligations,
not benefits inherited from having several planted proofs.

The most useful next result may be that a proposed construction fails one of
these gates. Preserving that result is preferable to another small model pair
whose favorable endpoint cannot distinguish evidence allocation, template
learning and population selection.
