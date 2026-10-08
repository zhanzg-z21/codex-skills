---
name: lvdan-research-reasoning
description: Evaluate biomedical basic and translational research questions, hypotheses, causal chains, existing results, experiment plans, and scientific stories using an evidence-weighted framework distilled from recurring patterns in Dan Lu's published work. Use when the user asks to assess mechanism study design, association versus causality, necessity or sufficiency, rescue logic, model fit, cell-cell or organ communication, omics-to-mechanism validation, highest-value next experiments, redundant work, novelty, or stopping points. Do not trigger for pure statistics, prediction-only clinical models, routine code, or language editing without a mechanism-design question.
---

# LvDan Research Reasoning

## Purpose and boundary

Apply a research reasoning framework distilled from recurring scientific patterns observed in Dan Lu's published work. Treat it as an evidence-weighted analytical lens, not a simulation of a person.

Never write that Dan Lu would think, say, choose, or require something. Use wording such as “按照该论文群中反复出现的证据标准” or “从蒸馏出的研究推理框架来看”. Do not imitate a person's voice.

Distinguish corpus-derived tendencies from general biomedical methodology. Do not label ordinary causal inference principles as unique to this corpus. Do not transfer molecules, diseases, technologies, or collaborator-specific platforms into unrelated topics.

## References to load

Always read [LvDan_Reasoning_Rules.md](references/LvDan_Reasoning_Rules.md) before a substantive analysis.

Read [LvDan_Research_Reasoning_Profile.md](references/LvDan_Research_Reasoning_Profile.md) when the request involves a full project, multiple models, cell-cell communication, organ interaction, omics, rescue design, novelty, or a stopping decision.

Read [LvDan_Paper_Evidence_Matrix.md](references/LvDan_Paper_Evidence_Matrix.md) when the user asks for provenance, when a rule seems ambiguous, or when the analysis risks relying on one paper, one topic, or a weak author role.

## Unified analysis workflow

### 1. Rewrite the actual question

State the central biological question in one falsifiable sentence. Separate the observation, proposed cause, intermediate mechanism, functional consequence, disease context, and intended claim.

If the input is incomplete, state the minimum assumptions needed to proceed. Ask for clarification only when different answers would materially change the recommended experiment or claim.

### 2. Set the current evidence ceiling

Label the current evidence as observation, temporal or spatial ordering, necessity, sufficiency, pathway specificity, integrated in vivo causality, or human relevance. These are nonmonotonic dimensions that can coexist. Necessity is not higher than sufficiency, and human relevance is not a higher causal grade than experimental in vivo causality.

Do not upgrade expression, correlation, pathway scores, CellChat, pseudotime, colocalization, co-immunoprecipitation, an inhibitor result, or a single overexpression result beyond what it directly supports.

Flag every conclusion that exceeds its evidence ceiling. Use precise wording, for example “supports association”, “supports necessity in this model”, or “does not yet establish that B mediates the effect of A”.

### 3. Draw the shortest causal chain

Represent the proposed mechanism as the fewest necessary arrows. For each arrow, record the evidence type, model, direction, main confounder, and whether the link is missing, indirect, or adequately supported.

Before pursuing molecular depth, locate the phenotype in the correct cell, compartment, time window, and biological process. Distinguish source from receiver, initiation from execution, intrinsic effects from host effects, and primary events from secondary consequences.

### 4. Find the weakest link and strongest alternative

Identify the single weakest causal connection. Then identify one or two plausible alternatives that could overturn the main interpretation.

Prefer branch-point experiments in which competing explanations predict different outcomes. Avoid broad control accumulation without a defined competing hypothesis.

### 5. Decide whether necessity, sufficiency, or rescue is needed

Choose perturbations by claim, not by checklist.

Use loss of function when the claim is that a molecule, cell population, receptor, or process is necessary. Use gain of function when the claim requires the candidate to be sufficient in a defined background. Use rescue, add back, epistasis, a functional mutant, or a site mutant when specificity or pathway order is the weak point. Use neutralization or transfer for extracellular mediators and communicating cell populations. Use pharmacology primarily for reversibility or translational feasibility unless independent evidence establishes target specificity.

Do not require every project to include knockout, overexpression, rescue, multiomics, a second animal model, and human samples. Recommend only what is needed for the intended claim.

### 6. Check model fit

Assign each model a job. Cell and biochemical systems should answer how the mechanism works. Animal models should test integrated disease or tissue function. Human samples should establish occurrence, stratification, or relevance unless the design itself permits causal inference.

Evaluate only the models supplied by the user or required by the intended claim. Do not aim to complete a cell, animal, and human triad.

For human-specific isoforms, species-restricted biology, developmental effects, or whole-body knockouts, state the exact external-validity limit. Do not treat a second similar model as a substitute for a missing causal perturbation.

For cell-cell or organ-interaction claims, inspect the chain as source cell, transferable mediator, receiver or sensor, receiver response, and organ-level consequence. Require direct perturbation of the most important links, not database prediction alone.

### 7. Apply a feasibility gate and rank experiments

Before ranking information gain, check whether the required tool exists, whether the perturbation can be selective enough to answer the question, whether the model preserves the relevant biology, and whether time and cost are proportionate to the current decision. Label a theoretically ideal but unavailable design as conditional. Offer the nearest executable branch-point experiment instead of ranking an infeasible design as the immediate priority.

Classify every proposed or existing experiment as decisive, mechanism strengthening, supporting, redundant, or low information gain.

An experiment is decisive when it changes the supported claim, supplies a missing evidence dimension, closes the weakest arrow, or excludes the strongest alternative. A mechanism-strengthening experiment improves directness or specificity. A supporting experiment improves robustness without changing the claim ceiling. A redundant experiment repeats the same inference with the same error structure. A low-information experiment is unlikely to change the conclusion or next decision regardless of result.

Count one experiment as one independent main perturbation in one model system. A new animal line, a new delivery system, an independent target-specific drug validation, and an independent cell reconstruction each count separately. Necessary controls do not count separately unless they introduce another mechanistic branch.

Recommend one experiment to start now. List at most two additional experiments as conditional next steps whose initiation depends on the preceding result. Never combine several new perturbation systems under one heading to evade this limit. For each recommendation, state the link tested, minimal design, essential controls, the interpretation of a positive result, the interpretation of a negative result, and why it outranks the alternatives.

When reviewing a clearly overexpanded plan, identify work that can be removed and use about one-third only as an upper reference for initial pruning. Do not delete experiments to satisfy a quota when the plan is already compact. Protect required controls, safety checks, and feasibility checks even when they do not strengthen mechanism.

### 8. Judge novelty and stopping point

Classify the main novelty as a new molecule, regulatory relationship, pathway, cell relationship, disease context, intervention, or biological principle. Explain whether the evidence reaches that novelty level.

Recommend stopping when the central claim is falsifiable and supported at the intended level, the key arrows have direct or perturbative evidence, the weakest link has adequate specificity, the strongest alternative has been addressed, and at least one model supplies the required functional endpoint.

For a claim limited to necessity, a credible claim-matched loss of function with perturbation-quality checks, baseline-state controls, and a functional endpoint can satisfy the stopping rule without a classic rescue. Require rescue, epistasis, or a functional mutant when the claim includes pathway order, catalytic activity, a critical site, a direct mediator, or a specific receptor.

If further work would only add markers, repeat omics, duplicate models, expand noncentral candidates, or chase structural detail that will not change the claim or intervention, say explicitly that it should not be done.

If the project is already sufficient for a properly limited conclusion, say so. Do not invent extra work to make the framework appear active.

## Output contract

Use a professional, direct, restrained peer-research tone and match the user's language. Prefer compact prose and small tables only when they materially improve comparison.

A full analysis should cover the relevant elements below. Combine sections and omit nonapplicable items when the question is simple. Treat this as a coverage checklist, not a mandatory ten-section template.

1. Central biological question and the proposed claim.

2. Current strongest evidence and evidence ceiling.

3. Short causal chain, with the weakest link and any overclaim.

4. One or two strongest alternative explanations.

5. Experiment triage, including decisive, strengthening, supporting, redundant, and low-information items where present.

6. One immediate next experiment and, only when useful, up to two conditional next experiments, each with decision-changing outcomes.

7. Experiments to remove or postpone. Use the one-third reference only for a clearly bloated plan, never as a quota.

8. Model-fit and human-relevance limits.

9. Main novelty type and the evidence needed to support that level.

10. A concrete stopping point, including “stop now” when warranted.

Do not list papers in every response. Cite corpus provenance only when requested or when it helps explain a disputed rule. Preserve the distinction between high-weight author-role evidence, collaborative support, and general methodology.
