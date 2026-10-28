"""Simulation harness (Phase 5): synthetic donations and organisations, run through the
real scoring, policy and lifecycle modules to produce synthetic offer outcomes.

Nothing here scores or transitions anything itself. `sim.engine` calls
app.domain.scoring.rank, app.domain.policy and app.domain.lifecycle, and a test checks
that it does (tests/unit/test_sim.py).

The outcomes come from a hidden "true" acceptance model (sim.truth). It is an assumption,
not evidence: a fit recovering it shows the pipeline works, and says nothing about how
real organisations behave. Synthetic outcomes are stored apart from real history
(app.services.training), and never activate a fit.
"""
