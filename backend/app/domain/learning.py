"""Learned ranking weights: a bounded, prior-regularised logistic fit. Pure (no database).

Model: P(accept | offer) = sigmoid(intercept + sum_f beta_f * value_f), over the five
ScoreFactor values an offer was made against. Each beta is bounded to [0, MODEL_COEF_MAX]
and pulled toward the prior (SCORE_WEIGHTS) by MODEL_PRIOR_PENALTY, so a small sample
moves the weights only as far as the data insists.

The ranking weights are the betas normalised to sum to 1. Two consequences, both stated
on purpose:

* Dividing by a positive constant keeps the order of candidates within one donation,
  because the intercept is shared by every candidate of a donation. The ranking is the
  same as ranking by the fitted probability.
* The normalised weights are an index, not a probability. Only the fitted betas and the
  intercept give probabilities, and those are not calibrated until enough real outcomes
  exist. Nothing downstream may label a score P(accept).

scipy does the constrained fit: scikit-learn's LogisticRegression cannot bound a
coefficient or shrink toward a non-zero prior. scikit-learn is used for diagnostics: an
unconstrained comparison fit (to show where the bounds bind) and the held-out metrics.
"""

import hashlib
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score

from app.constants import (
    MODEL_BOOTSTRAP_RESAMPLES,
    MODEL_BOOTSTRAP_SEED,
    MODEL_COEF_MAX,
    MODEL_HOLDOUT_FRACTION,
    MODEL_INTERVAL_PERCENTILES,
    MODEL_MIN_REAL_OUTCOMES,
    MODEL_MIN_REAL_PER_CLASS,
    MODEL_PRIOR_PENALTY,
    SCORE_WEIGHTS,
    ScoreFactor,
)

# The coefficient vector follows this order everywhere (features, betas, prior).
FACTORS: tuple[ScoreFactor, ...] = tuple(ScoreFactor)


@dataclass(frozen=True)
class Outcome:
    """One labelled offer. `group` is the donation: all of a donation's offers fall on the
    same side of the split, so the holdout never shares a donation with training."""

    group: str
    features: tuple[float, ...]  # factor values, in FACTORS order
    accepted: bool


def prior_vector(weights: Mapping[ScoreFactor, float] = SCORE_WEIGHTS) -> np.ndarray:
    return np.array([float(weights[f]) for f in FACTORS])


@dataclass(frozen=True)
class SyntheticOffer:
    """One simulated offer, as the simulation harness produces it and the service stores it."""

    donation_ref: uuid.UUID
    organization_ref: uuid.UUID
    features: tuple[float, ...]  # factor values, in FACTORS order
    accepted: bool


def floor_reason(real_n: int, real_accepted: int, real_declined: int) -> str | None:
    """Why the real-outcome floor is not met, or None when it is."""
    if real_n < MODEL_MIN_REAL_OUTCOMES:
        return f"below the real-outcome floor: {real_n} labelled offers (need {MODEL_MIN_REAL_OUTCOMES})"
    if real_accepted < MODEL_MIN_REAL_PER_CLASS:
        return f"below the real-outcome floor: {real_accepted} accepted (need {MODEL_MIN_REAL_PER_CLASS})"
    if real_declined < MODEL_MIN_REAL_PER_CLASS:
        return f"below the real-outcome floor: {real_declined} declined (need {MODEL_MIN_REAL_PER_CLASS})"
    return None


def in_holdout(group: str) -> bool:
    """Deterministic: the same donation is always in the same split, on every machine."""
    digest = hashlib.sha256(group.encode()).digest()
    return digest[0] / 256 < MODEL_HOLDOUT_FRACTION


def ranking_weights(beta: np.ndarray) -> dict[ScoreFactor, float]:
    """Betas normalised to sum to 1. Raises if every beta is zero: the fit then says no
    factor matters, and there is no ranking to normalise."""
    total = float(beta.sum())
    if total <= 0:
        raise ValueError("Every coefficient is zero; there are no ranking weights to normalise.")
    return {f: float(b) / total for f, b in zip(FACTORS, beta)}


def _split(pool: Sequence[Outcome]) -> tuple[list[Outcome], list[Outcome]]:
    train = [o for o in pool if not in_holdout(o.group)]
    holdout = [o for o in pool if in_holdout(o.group)]
    return train, holdout


def _arrays(rows: Sequence[Outcome]) -> tuple[np.ndarray, np.ndarray]:
    X = np.array([o.features for o in rows], dtype=float).reshape(len(rows), len(FACTORS))
    y = np.array([o.accepted for o in rows], dtype=float)
    return X, y


def _loss_and_grad(theta: np.ndarray, X: np.ndarray, y: np.ndarray, prior: np.ndarray):
    beta, b = theta[:-1], theta[-1]
    z = X @ beta + b
    p = expit(z)
    # Summed negative log-likelihood, written stably (logaddexp), plus the prior penalty.
    loss = float(np.sum(np.logaddexp(0.0, z) - y * z) + MODEL_PRIOR_PENALTY * np.sum((beta - prior) ** 2))
    grad_beta = X.T @ (p - y) + 2.0 * MODEL_PRIOR_PENALTY * (beta - prior)
    grad_b = float(np.sum(p - y))
    return loss, np.append(grad_beta, grad_b)


def fit_bounded(rows: Sequence[Outcome], prior: np.ndarray) -> tuple[np.ndarray, float] | None:
    """MAP fit: betas in [0, MODEL_COEF_MAX] with the prior penalty; the intercept is free.
    Returns (beta, intercept), or None if the optimiser did not converge."""
    X, y = _arrays(rows)
    if y.min() == y.max():
        return None  # one class only: no slope can be learned
    start = np.append(prior, np.log(y.mean() / (1 - y.mean())))
    bounds = [(0.0, MODEL_COEF_MAX)] * len(FACTORS) + [(None, None)]
    result = minimize(_loss_and_grad, start, args=(X, y, prior), jac=True, method="L-BFGS-B", bounds=bounds)
    if not result.success:
        return None
    return result.x[:-1], float(result.x[-1])


def fit_intercept_only(rows: Sequence[Outcome], prior: np.ndarray) -> float:
    """The intercept that best fits the rows with the betas held at the prior: the
    cold-start model's own probability level, so its holdout log-loss is a fair baseline."""
    X, y = _arrays(rows)
    z0 = X @ prior

    def neg_log_likelihood(params: np.ndarray):
        z = z0 + params[0]
        value = float(np.sum(np.logaddexp(0.0, z) - y * z))
        return value, np.array([float(np.sum(expit(z) - y))])

    result = minimize(neg_log_likelihood, np.array([0.0]), jac=True, method="L-BFGS-B")
    return float(result.x[0])


def _holdout_loss(rows: Sequence[Outcome], beta: np.ndarray, intercept: float) -> float | None:
    if not rows:
        return None
    X, y = _arrays(rows)
    p = np.clip(expit(X @ beta + intercept), 1e-9, 1 - 1e-9)
    return float(log_loss(y, p, labels=[0.0, 1.0]))


def _auc(rows: Sequence[Outcome], beta: np.ndarray, intercept: float) -> float | None:
    if not rows:
        return None
    X, y = _arrays(rows)
    if y.min() == y.max():
        return None
    return float(roc_auc_score(y, X @ beta + intercept))


def _unconstrained(rows: Sequence[Outcome]) -> tuple[float, ...] | None:
    """scikit-learn's plain logistic regression, for comparison only: where its
    coefficients differ from the bounded fit, the bounds or the penalty are binding."""
    X, y = _arrays(rows)
    if y.min() == y.max():
        return None
    model = LogisticRegression(C=1e12, max_iter=1000).fit(X, y)  # effectively unpenalised
    return tuple(float(c) for c in model.coef_[0])


@dataclass(frozen=True)
class Evaluation:
    """Everything a training run learned from one pool of outcomes."""

    train_n: int
    holdout_n: int
    beta: np.ndarray | None  # None when no fit could be made
    intercept: float | None
    weights: dict[ScoreFactor, float] | None
    prior_weights: dict[ScoreFactor, float]
    fitted_loss: float | None  # held-out log-loss of the fit
    prior_loss: float | None  # held-out log-loss of the cold-start prior
    fitted_auc: float | None
    prior_auc: float | None
    unconstrained: tuple[float, ...] | None  # sklearn, train split, logit scale
    intervals: dict[ScoreFactor, tuple[float, float]] | None = None  # normalised weights
    notes: tuple[str, ...] = field(default=())

    @property
    def max_shift_from_prior(self) -> float | None:
        if self.weights is None:
            return None
        return max(abs(self.weights[f] - self.prior_weights[f]) for f in FACTORS)


def evaluate(
    pool: Sequence[Outcome],
    prior: Mapping[ScoreFactor, float] = SCORE_WEIGHTS,
    bootstrap: int = MODEL_BOOTSTRAP_RESAMPLES,
) -> Evaluation:
    """Split by donation, fit on the training side, score both models on the holdout."""
    prior_vec = prior_vector(prior)
    train, holdout = _split(pool)
    prior_weights = {f: float(prior[f]) for f in FACTORS}
    notes: list[str] = []

    fitted = fit_bounded(train, prior_vec) if train else None
    if fitted is None:
        notes.append("no fit: the training split has one class or the optimiser did not converge")
        prior_intercept = fit_intercept_only(train, prior_vec) if train else None
        return Evaluation(
            train_n=len(train), holdout_n=len(holdout), beta=None, intercept=None, weights=None,
            prior_weights=prior_weights, fitted_loss=None,
            prior_loss=_holdout_loss(holdout, prior_vec, prior_intercept) if prior_intercept is not None else None,
            fitted_auc=None, prior_auc=None, unconstrained=None, notes=tuple(notes),
        )

    beta, intercept = fitted
    prior_intercept = fit_intercept_only(train, prior_vec)
    weights = ranking_weights(beta)
    return Evaluation(
        train_n=len(train),
        holdout_n=len(holdout),
        beta=beta,
        intercept=intercept,
        weights=weights,
        prior_weights=prior_weights,
        fitted_loss=_holdout_loss(holdout, beta, intercept),
        prior_loss=_holdout_loss(holdout, prior_vec, prior_intercept),
        fitted_auc=_auc(holdout, beta, intercept),
        prior_auc=_auc(holdout, prior_vec, prior_intercept),
        unconstrained=_unconstrained(train),
        intervals=_bootstrap_intervals(train, prior_vec, bootstrap),
        notes=tuple(notes),
    )


def _bootstrap_intervals(
    train: Sequence[Outcome], prior: np.ndarray, resamples: int
) -> dict[ScoreFactor, tuple[float, float]] | None:
    """Percentile intervals of the normalised weights, from refitting resampled training
    donations. Seeded, so the same data gives the same intervals."""
    if resamples <= 0 or not train:
        return None
    rng = np.random.default_rng(MODEL_BOOTSTRAP_SEED)
    draws: list[dict[ScoreFactor, float]] = []
    for _ in range(resamples):
        sample = [train[i] for i in rng.integers(0, len(train), len(train))]
        fitted = fit_bounded(sample, prior)
        if fitted is not None and float(fitted[0].sum()) > 0:
            draws.append(ranking_weights(fitted[0]))
    if len(draws) < 2:
        return None
    low, high = MODEL_INTERVAL_PERCENTILES
    return {
        f: (
            float(np.percentile([d[f] for d in draws], low)),
            float(np.percentile([d[f] for d in draws], high)),
        )
        for f in FACTORS
    }


@dataclass(frozen=True)
class Gate:
    activate: bool
    reasons: tuple[str, ...]


def _holdout_reasons(evaluation: Evaluation) -> list[str]:
    """Reasons a fit cannot be activated on its held-out evidence alone."""
    if evaluation.weights is None:
        return ["no fit to activate"]
    if evaluation.fitted_loss is None or evaluation.prior_loss is None:
        return ["no held-out outcomes to compare against the prior"]
    if evaluation.fitted_loss >= evaluation.prior_loss:
        return [
            f"held-out log-loss does not beat the prior ({evaluation.fitted_loss:.4f} vs {evaluation.prior_loss:.4f})"
        ]
    return []


def gate(evaluation: Evaluation, *, real_n: int, real_accepted: int, real_declined: int, sandbox: bool) -> Gate:
    """Whether a fit may become the active weights. Every failed rule is a reason, so the
    CLI and the audit row say why a retrain did not activate. Nothing here is a review
    step: the rules are fixed and checked by code."""
    reasons: list[str] = []
    if sandbox:
        reasons.append("synthetic data was included: a sandbox fit is never activated")
    floor = floor_reason(real_n, real_accepted, real_declined)
    if floor is not None:
        reasons.append(floor)
    reasons.extend(_holdout_reasons(evaluation))
    return Gate(activate=not reasons, reasons=tuple(reasons))


def demo_gate(evaluation: Evaluation) -> Gate:
    """The gate for the college demo (app.services.training.demo_fit): the same held-out
    comparison against the prior, but no real-outcome floor and no refusal of synthetic
    data. Only the demo path may call it, and that path runs on the test database only.
    The production gate above is unchanged: synthetic data never activates there."""
    reasons = _holdout_reasons(evaluation)
    return Gate(activate=not reasons, reasons=tuple(reasons))
