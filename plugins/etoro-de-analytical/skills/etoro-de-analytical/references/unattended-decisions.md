# Resolving semantic forks unattended

Dark-factory assumption: **nobody is going to answer you.** A fork you can't close is a PR that never opens. This is the procedure for closing one honestly.

## 1. The precedence ladder

Work down until the fork closes. Stop at the first rung that gives a defensible answer, and record which rung you used.

1. **Live data.** Does the ambiguous population even exist? A value with zero rows all-time is a dictionary entry, not a semantic. Count before theorising — many forks evaporate here.
2. **The object's own source.** Read the whole proc/view, not the matched line. Inline comments next to a predicate are first-party intent and outrank any external doc.
3. **Nearest domain doc.** The skill/wiki for the domain that *owns the object being changed* wins over a doc from a neighbouring domain describing its own convention. Two domains legitimately differing is not a contradiction to escalate — it's two domains.
4. **Structural analogy.** Find the closest already-solved case in the same estate and follow it, including its stated rationale. If the rationale doesn't transfer, the analogy doesn't either — say so.
5. **Conservatism ordering.** Prefer the option that is reversible, that narrows rather than widens silently, and that leaves a wrong number *visible* rather than plausible.

## 2. Standing rules that close common forks

- **A bare literal duplicating a semantic flag is latent debt, not intentional narrowing.** If a filter carries both a semantic column and a hardcoded value that currently means the same thing, the flag governs and the literal should go — *unless* it carries a comment stating the narrow intent, in which case it is deliberate and stays. This single rule resolves both directions; apply it mechanically and cite the presence or absence of the comment as your evidence.
- **A naming coincidence is not a dependency.** Two columns sharing a value or a word are unrelated until a join or predicate connects them. Prove the link before treating an object as in-scope.
- **A shared name across domains is usually polysemy, not drift.** When two objects implement a similarly-named concept by different mechanisms, the default reading is that they are **two different concepts wearing one bad name** — not one concept that has drifted and needs reconciling. Business vocabulary is overloaded: the same phrase routinely means different things to the payments team, the trading team and finance, and each is correct in its own context. Before reporting a "divergence", establish that the two really are meant to be the same measure — ask what question each one answers, and check whether the mechanisms even observe the same events. If they answer different questions, there is nothing to fix and nothing to document beyond what the owning domain already knows. Raising it anyway is noise, and it erodes trust in the findings that matter.
- **A correlation is not a mechanism.** "These are 99% the same today" justifies a check, never a code change. Find the causal path or leave it alone.
- **A sentinel is a statement.** A hardcoded `-1`/`0`/literal in a landing path usually means "this concept does not apply here," not "this is a bug." Read the surrounding comment and the population it selects before you fix it.
- **Generated trees are evidence, not surfaces.** If a path is dominated by bot commits, it is an export. Changing it ships nothing and may be deleted on the next run. Find the authoring path or report that there isn't one in-repo.
- **A forward-looking value costs nothing.** Wiring a not-yet-existing ID into a CASE or join is safe and self-activating. Don't block a change on an upstream dictionary row that a predicate doesn't need.

## 3. Writing the decision into the PR

Every fork you closed by judgment gets a block in the PR body. This is what replaces asking:

```
### Decision: <the fork, in one line>
**Called:** <what you did>
**Rejected:** <the alternative, stated fairly>
**Basis:** <rung of the ladder + the actual evidence — query output, file:line, doc quote>
**Blast radius:** <whose number moves, by how much, measured not guessed>
**To reverse:** <the specific edit that undoes it>
**Confirm:** @<owning team//codeowner>
```

Tag the owning team as reviewer for any fork touching their numbers. A reviewer who disagrees now has a one-line diff to request, not a design argument. That is the whole point: **the cost of a wrong call must be lower than the cost of blocking.**

## 4. When to actually stop

Only three reasons, and name which one:
- **Irreversible** — data loss, an external side effect, something that can't be undone by a follow-up commit.
- **Unbounded** — you cannot measure the blast radius, so you cannot state it honestly in the PR.
- **Unresolvable** — the ladder ran out: no data, no source, no doc, no analogy. Genuinely absent information, not merely uncomfortable inference.

Anything else: decide, document, open the PR, let the reviewer veto.
