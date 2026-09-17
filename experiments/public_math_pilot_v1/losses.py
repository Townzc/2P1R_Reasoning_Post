"""Pure loss and offline-selector contracts for the public-math pilot.

No model, tokenizer, data download, or persistence is performed here. The caller
must freeze QDW annotations before training and supply the *whole optimizer
update* raw-token denominator to every microbatch. These are the pilot formulas,
not a reproduction of the upstream DFT/TrimSFT training drivers.
"""
from __future__ import annotations

import hashlib
import json
import math
import operator
import re
from typing import Sequence

import torch


IGNORE_INDEX = -100
ARMS = ("SFT", "DFT", "TrimSFT", "QDW_v0")
QDW_RHO = 0.10
QDW_LAMBDA = 5.0
QDW_POSITIVE_EPSILON = 1e-6
TRIM_M = 1.5
TRIM_TAU = 0.8
_LINE_BREAKS = "\n\r\v\f\x1c\x1d\x1e\x85\u2028\u2029"


def _sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def _positive_integer(value, name):
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a positive integer")
    try:
        integer = operator.index(value)
    except TypeError as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if integer <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return integer


def _finite(value, name):
    if not bool(torch.isfinite(value).all()):
        raise FloatingPointError(f"Nonfinite {name}")


def _shifted(logits, labels, attention_mask=None):
    if (not isinstance(logits, torch.Tensor) or not logits.is_floating_point() or
            logits.ndim != 3 or not isinstance(labels, torch.Tensor) or
            labels.dtype != torch.long or labels.shape != logits.shape[:2] or
            labels.device != logits.device or logits.shape[1] < 2 or logits.shape[2] < 2):
        raise ValueError("Expected floating [B,S,V] logits and aligned int64 [B,S] labels")
    if logits.shape[0] == 0 or bool((labels[:, 0] != IGNORE_INDEX).any()):
        raise ValueError("Every sample needs context: position zero must be ignored")
    _finite(logits, "logits")
    valid = labels[:, 1:] != IGNORE_INDEX
    lengths = valid.sum(dim=1)
    if bool((lengths <= 0).any()):
        raise ValueError("Every sample must contain at least one supervised response token")
    if attention_mask is not None:
        if (not isinstance(attention_mask, torch.Tensor) or attention_mask.shape != labels.shape or
                attention_mask.device != labels.device or
                bool(((attention_mask != 0) & (attention_mask != 1)).any())):
            raise ValueError("Attention mask must be aligned and binary")
        if bool(((labels != IGNORE_INDEX) & ~attention_mask.bool()).any()):
            raise ValueError("Padding cannot be supervised")
        if bool((valid & ~attention_mask[:, :-1].bool()).any()):
            raise ValueError("A supervised token cannot be predicted from a padding position")
    gold = labels[:, 1:][valid]
    if bool(((gold < 0) | (gold >= logits.shape[-1])).any()):
        raise ValueError("Supervised target is outside the vocabulary")
    # Index before the FP32 cast so ignored prompt/padding positions do not
    # allocate a second complete [B,S,V] vocabulary tensor.
    active_logits = logits[:, :-1, :][valid].float()
    _finite(active_logits, "FP32 active logits")
    gold_logits = active_logits.gather(1, gold[:, None]).squeeze(1)
    logp = gold_logits - torch.logsumexp(active_logits, dim=-1)
    _finite(logp, "FP32 gold log probabilities")
    return valid, lengths, gold, active_logits, gold_logits, logp


def causal_gold_log_probs(logits, labels, *, attention_mask=None):
    """Return shifted [B,S-1] FP32 gold logp and its bool supervision mask.

    Unsupervised slots are zero, not an estimate of any token probability.
    A response label at full input position t is stored at output position t-1.
    This helper does not detach; offline callers must use no_grad/eval.
    """
    valid, _, _, _, _, logp = _shifted(logits, labels, attention_mask)
    dense = torch.zeros(valid.shape, dtype=torch.float32, device=logits.device)
    return dense.masked_scatter(valid, logp), valid


def qdw_token_weights(labels, qdw_mask, *, multiplier=QDW_LAMBDA):
    """Return full-position FP32 weights; prompt/pad zero, each row mass L.

    The mask must be an already-frozen bool tensor. A final answer and EOS have
    the normalized *background* weight when K>0, not absolute weight one.
    The text/ending boundary is verified by select_qdw_tokens at annotation time.
    """
    if (not isinstance(labels, torch.Tensor) or labels.ndim != 2 or labels.dtype != torch.long or
            labels.shape[0] == 0 or labels.shape[1] < 2 or
            not isinstance(qdw_mask, torch.Tensor) or qdw_mask.dtype != torch.bool or
            qdw_mask.shape != labels.shape or qdw_mask.device != labels.device):
        raise ValueError("QDW requires aligned int64 labels and frozen boolean mask")
    if not math.isfinite(multiplier) or multiplier < 1:
        raise ValueError("QDW multiplier must be finite and >= 1")
    valid = labels != IGNORE_INDEX
    if bool(valid[:, 0].any()) or bool((qdw_mask & ~valid).any()):
        raise ValueError("QDW mask or label enters prompt/padding/unpredictable position")
    lengths = valid.sum(dim=1)
    counts = qdw_mask.sum(dim=1)
    if bool((lengths <= 0).any()):
        raise ValueError("Every QDW row requires positive supervised length")
    length = lengths.float()[:, None]
    denominator = length + (multiplier - 1) * counts.float()[:, None]
    weights = length * (1 + (multiplier - 1) * qdw_mask.float()) / denominator
    weights = weights.masked_fill(~valid, 0).detach()
    _finite(weights, "QDW weights")
    if not torch.allclose(weights.sum(dim=1), lengths.float(), atol=2e-4, rtol=2e-6):
        raise FloatingPointError("QDW per-response weight mass is not conserved")
    return weights


def compute_loss(logits, labels, arm, update_denominator, *, qdw_mask=None,
                 attention_mask=None, qdw_lambda=QDW_LAMBDA,
                 trim_m=TRIM_M, trim_tau=TRIM_TAU):
    """Return (differentiable FP32 microbatch contribution, JSON audit).

    ``update_denominator`` is sum(L_i) over the full 32-sample optimizer update,
    including each supervised assistant ending. Do not divide again by the
    microbatch count. DFT/Trim weights are detached and never renormalized.
    """
    canonical = {"QDW-v0": "QDW_v0", "QDW": "QDW_v0"}.get(arm, arm)
    if canonical not in ARMS:
        raise ValueError(f"Unknown arm: {arm!r}")
    denominator = _positive_integer(update_denominator, "Whole-update raw token denominator")
    valid, lengths, gold, active_logits, gold_logits, logp = _shifted(logits, labels, attention_mask)
    count = int(lengths.sum().item())
    if denominator < count:
        raise ValueError("Whole-update denominator is smaller than this microbatch")
    ce = -logp
    gap = None
    if canonical == "QDW_v0":
        weights = qdw_token_weights(labels, qdw_mask, multiplier=qdw_lambda)[:, 1:][valid]
        selected_counts = qdw_mask.sum(dim=1).tolist()
    else:
        if qdw_mask is not None:
            raise ValueError("A QDW mask must not be silently applied to another arm")
        selected_counts = [0] * labels.shape[0]
        if canonical == "SFT":
            weights = torch.ones_like(ce)
        elif canonical == "DFT":
            weights = torch.exp(-ce.detach())
        else:
            if not math.isfinite(trim_m) or not math.isfinite(trim_tau) or trim_tau <= 0:
                raise ValueError("TrimSFT requires finite m and positive finite tau")
            # Top two suffice even with ties: if top1 is gold, top2 is the best
            # non-gold; otherwise top1 is already a valid competing token.
            top_values, top_ids = active_logits.detach().topk(2, dim=-1)
            competitor = torch.where(top_ids[:, 0] == gold, top_values[:, 1], top_values[:, 0])
            gap = gold_logits.detach() - competitor
            _finite(gap, "TrimSFT gap")
            exponent = -((gap - trim_m) / trim_tau).square() / 2
            # Finite very large gaps may yield -inf after FP32 squaring; exp
            # then correctly underflows to zero. No floor is introduced.
            weights = torch.exp(exponent).detach()
    _finite(weights, "loss weights")
    weighted_sum = (ce * weights).sum()
    raw_sum = ce.sum()
    loss = weighted_sum / denominator
    _finite(weighted_sum, "weighted loss numerator")
    _finite(raw_sum, "unweighted loss numerator")
    _finite(loss, "loss")
    per_row_mass = torch.zeros(labels.shape[0], dtype=torch.float32, device=labels.device)
    row_ids = valid.nonzero(as_tuple=True)[0]
    per_row_mass.scatter_add_(0, row_ids, weights)
    audit = {
        "schema": "public_math_loss_v1", "arm": canonical, "calculation_dtype": "float32",
        "label_shift": 1, "denominator_scope": "caller_whole_optimizer_update_raw_tokens",
        "update_denominator": denominator, "microbatch_supervised_tokens": count,
        "microbatch_samples": labels.shape[0], "weighted_numerator": float(weighted_sum.detach()),
        "unweighted_numerator": float(raw_sum.detach()), "loss_contribution": float(loss.detach()),
        "weight_sum": float(weights.sum()), "weight_min": float(weights.min()),
        "weight_max": float(weights.max()), "weight_mean": float(weights.mean()),
        "zero_weight_tokens": int((weights == 0).sum()),
        "per_sample": [{"L": int(n), "K": int(k), "weight_sum": float(m)}
                       for n, k, m in zip(lengths.tolist(), selected_counts, per_row_mass.tolist())],
        "weights_detached": not weights.requires_grad,
    }
    if canonical == "QDW_v0":
        audit.update(qdw_lambda=float(qdw_lambda), qdw_mask_sha256=_sha(qdw_mask.tolist()))
    if gap is not None:
        audit.update(trim_m=float(trim_m), trim_tau=float(trim_tau),
                     gap_min=float(gap.min()), gap_max=float(gap.max()))
    return loss, audit


def _token_ids(values, name):
    result = list(values)
    if any(type(v) is not int or v < 0 for v in result):
        raise ValueError(f"{name} must contain nonnegative integer token IDs")
    return result


def validate_response_alignment(full_input_ids, blank_input_ids, full_prefix_length,
                                blank_prefix_length, response_ids):
    """Fail closed unless both teacher-forced inputs have the identical suffix."""
    full = _token_ids(full_input_ids, "Full input")
    blank = _token_ids(blank_input_ids, "Blank input")
    response = _token_ids(response_ids, "Response")
    fp = _positive_integer(full_prefix_length, "Full prefix length")
    bp = _positive_integer(blank_prefix_length, "Blank prefix length")
    if not response or full[fp:] != response or blank[bp:] != response or fp >= len(full) or bp >= len(blank):
        raise ValueError("Full/blank response token IDs do not align exactly")
    return {"response_ids": response, "full_prefix_length": fp, "blank_prefix_length": bp,
            "full_input_ids_sha256": _sha(full), "blank_input_ids_sha256": _sha(blank),
            "response_ids_sha256": _sha(response), "alignment": "exact_identical_response_ids"}


def _escaped(text, index):
    before = index - 1
    while before >= 0 and text[before] == "\\":
        before -= 1
    return (index - before - 1) % 2 == 1


def final_boxed_boundary(reference_text):
    """Find the last brace-balanced literal LaTeX boxed command.

    Nested braces (including fractions) and escaped braces are handled without
    executing or mathematically judging the answer. An unbalanced later command
    does not invalidate a preceding balanced one. Empty balanced boxes are still
    syntactic boundaries. The entire box's line, not just its contents, is out.
    """
    if not isinstance(reference_text, str):
        raise ValueError("Reference must be original text")
    found = None
    for match in re.finditer(r"\\boxed\s*\{", reference_text):
        if _escaped(reference_text, match.start()):
            continue
        opening = match.end() - 1
        depth = 1
        for position in range(opening + 1, len(reference_text)):
            char = reference_text[position]
            if char in "{}" and not _escaped(reference_text, position):
                depth += 1 if char == "{" else -1
            if depth == 0:
                line_start = 1 + max(reference_text.rfind(c, 0, match.start()) for c in _LINE_BREAKS)
                found = {"command_start": match.start(), "box_end": position + 1,
                         "content_start": opening + 1, "content_end": position,
                         "line_start": line_start,
                         "boxed_text": reference_text[match.start():position + 1]}
                break
    return found


def _frozen_fp32_vector(values, length, name):
    if isinstance(values, torch.Tensor) and values.requires_grad:
        raise ValueError(f"{name} must come from frozen no-grad annotation")
    result = torch.as_tensor(values, dtype=torch.float32, device="cpu").detach()
    if result.shape != (length,):
        raise ValueError(f"{name} length does not match the response IDs")
    _finite(result, name)
    if bool((result > 0).any()):
        raise ValueError(f"{name} contains positive values, not valid log probabilities")
    return result


def select_qdw_tokens(reference_text, response_ids, response_offsets, full_logp, blank_logp, *,
                      blank_response_ids, special_ids, rho=QDW_RHO,
                      positive_epsilon=QDW_POSITIVE_EPSILON,
                      full_prefix_length=None, blank_prefix_length=None):
    """Build an auditable response-position QDW mask, without changing the text.

    Offsets are half-open character spans relative to the original response
    start. Special ending tokens may use (0,0); serialized ending offsets may
    lie beyond the original reference. Tokens straddling the answer-line start
    are excluded in full. Whitespace is decided from each original text span.
    Call validate_response_alignment on the actual inputs before the forwards.
    """
    if not isinstance(reference_text, str):
        raise ValueError("Reference must be original text")
    ids = _token_ids(response_ids, "Full response")
    blank_ids = _token_ids(blank_response_ids, "Blank response")
    special = set(_token_ids(special_ids, "Special IDs"))
    if not ids or ids != blank_ids:
        raise ValueError("Full/blank response IDs must align; do not drop mismatched samples")
    offsets = [list(pair) for pair in response_offsets]
    if len(offsets) != len(ids) or any(len(p) != 2 or any(type(v) is not int for v in p) or
                                     not 0 <= p[0] <= p[1] for p in offsets):
        raise ValueError("Token offsets must be aligned nonnegative half-open character spans")
    if not math.isfinite(rho) or not 0 < rho <= 1 or not math.isfinite(positive_epsilon) or positive_epsilon < 0:
        raise ValueError("Invalid QDW rank fraction or positivity threshold")
    if (full_prefix_length is None) != (blank_prefix_length is None):
        raise ValueError("Supply both full and blank prefix lengths or neither")
    if full_prefix_length is not None:
        full_prefix_length = _positive_integer(full_prefix_length, "Full prefix length")
        blank_prefix_length = _positive_integer(blank_prefix_length, "Blank prefix length")
    full = _frozen_fp32_vector(full_logp, len(ids), "Full log probabilities")
    blank = _frozen_fp32_vector(blank_logp, len(ids), "Blank log probabilities")
    scores = full - blank
    _finite(scores, "QDW scores")
    boundary = final_boxed_boundary(reference_text)
    eligible = []
    if boundary is not None:
        for index, (token, (start, end)) in enumerate(zip(ids, offsets)):
            if token not in special and start < end <= boundary["line_start"]:
                if not reference_text[start:end].isspace():
                    eligible.append(index)
    # All arithmetic through score subtraction is FP32. Threshold comparison
    # also uses FP32, then ties sort by original response index explicitly.
    positive = [i for i in eligible if bool(scores[i] > positive_epsilon)]
    ranked = sorted(positive, key=lambda i: (-float(scores[i]), i))
    quota = math.ceil(rho * len(eligible))
    selected = ranked[:min(quota, len(positive))]
    mask = [False] * len(ids)
    for i in selected:
        mask[i] = True
    reason = ("no_parseable_boxed_boundary" if boundary is None else
              "empty_eligible_region" if not eligible else
              "no_positive_scores" if not selected else "selected")
    result = {
        "schema": "public_math_qdw_selection_v1", "response_ids": ids,
        "response_offsets": offsets, "response_ids_sha256": _sha(ids),
        "reference_sha256": hashlib.sha256(reference_text.encode()).hexdigest(),
        "full_prefix_length": full_prefix_length, "blank_prefix_length": blank_prefix_length,
        "full_logp": full.tolist(), "blank_logp": blank.tolist(), "scores": scores.tolist(),
        "score_dtype": "float32", "score_definition": "full_gold_logp_minus_blank_gold_logp",
        "boundary": boundary, "boundary_policy": "whole_tokens_ending_by_final_box_line_start",
        "eligible_indices": eligible, "positive_indices": positive,
        "ranked_positive_indices": ranked, "selected_indices": sorted(selected),
        "selection_order": selected, "mask": mask, "mask_sha256": _sha(mask),
        "L": len(ids), "K": len(selected), "eligible_count": len(eligible),
        "positive_count": len(positive), "quota": quota, "rho": float(rho),
        "positive_epsilon": float(positive_epsilon), "tie_break": "ascending_response_token_index",
        "status": reason, "uniform_ce_fallback": not selected,
        "special_ids": sorted(special),
    }
    return result
