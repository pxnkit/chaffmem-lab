# Error taxonomy

## P1. Physical loss

The critical record no longer exists in the audited store.

## R1. Retrieval displacement

The target exists but falls below the fixed top-k budget.

## R2. Ranking instability

Equivalent inputs produce a different order because of nondeterministic or incomplete tie-breaking.

## B1. Behavioral non-use

The target is retrieved but the symbolic decision does not use it.

## T1. Temporal regression

Availability recovers or fails unexpectedly after an unrelated write because lifecycle state is inconsistent.

## D1. Defense false rejection

A legitimate write is rejected without satisfying the declared intervention rule.

## D2. Defense false acceptance

A write that satisfies the declared deterministic block rule is admitted.

## D3. Oracle leakage

A non-oracle defense uses gold target identity or outcome information.

## I1. Integrity failure

An event, snapshot, metric, or manifest hash does not verify.

## C1. Configuration mismatch

Artifacts from incompatible schema, fixture, policy, or embedding versions are combined.

## U1. Undefined metric

A metric has no valid denominator or comparison. The output must carry an explicit undefined reason instead of NaN or infinity.
