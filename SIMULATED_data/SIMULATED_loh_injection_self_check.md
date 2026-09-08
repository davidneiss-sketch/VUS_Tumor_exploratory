SIMULATED DATA — NOT A SCIENTIFIC RESULT

# LOH injection self-check

SIMULATED: Re-classifying every generated sample's tumor/normal read counts with PROTOCOL.md §5.1/§5.2's own binomial-test logic (direction only -- PROTOCOL's model has no concept of copy-neutral vs deletion mechanism, so CN_NEUTRAL_LOH_WT_LOSS and WT_LOSS are both collapsed to LOH_SECOND_HIT for this comparison) recovered the expected direction label for 9743/11088 samples (87.9%). AMBIGUOUS is expected to sometimes resolve to a definite direction by chance at its deliberately low, near-floor depth (that is what "ambiguous" means under a noisy binomial draw); NOT_EVALUABLE is expected to match 100% (depth alone determines it).
