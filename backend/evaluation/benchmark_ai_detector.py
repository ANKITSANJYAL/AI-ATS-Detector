"""
═══════════════════════════════════════════════════════════════════════
AI Content Detector — Benchmark Evaluation Script
═══════════════════════════════════════════════════════════════════════

Datasets:
  1. HC3  (Hello-SimpleAI/HC3)  — Human vs ChatGPT QA pairs  (~24K rows)
  2. RAID (liamdugan/raid)      — 11 LLMs × 11 domains × 12 attacks (~6M+ rows)

Metrics computed:
  • Accuracy, Precision, Recall, F1, AUROC
  • Expected Calibration Error (ECE, 10 bins)
  • Reliability diagram (calibration curve)
  • Confusion matrix
  • Per-domain breakdown (RAID)
  • Clean vs adversarial performance (RAID)

Usage:
  cd backend
  python evaluation/benchmark_ai_detector.py          # full benchmark
  python evaluation/benchmark_ai_detector.py --quick   # 100 samples for smoke test
"""

import sys
import os
import json
import time
import math
import argparse
from pathlib import Path
from datetime import datetime

import numpy as np

# Add backend to path so we can import our modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ─── Helpers ─────────────────────────────────────────────────────────

def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def compute_metrics(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5):
    """Compute standard binary classification metrics."""
    y_pred = (y_prob >= threshold).astype(int)
    tp = np.sum((y_pred == 1) & (y_true == 1))
    fp = np.sum((y_pred == 1) & (y_true == 0))
    fn = np.sum((y_pred == 0) & (y_true == 1))
    tn = np.sum((y_pred == 0) & (y_true == 0))

    accuracy = (tp + tn) / len(y_true) if len(y_true) > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    return {
        "accuracy": float(accuracy),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
        "n": len(y_true),
    }


def compute_auroc(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    """Compute AUROC via trapezoidal integration over sorted thresholds."""
    # Sort by descending probability
    desc_idx = np.argsort(-y_prob)
    y_true_sorted = y_true[desc_idx]

    n_pos = np.sum(y_true == 1)
    n_neg = np.sum(y_true == 0)
    if n_pos == 0 or n_neg == 0:
        return 0.5

    tpr_prev, fpr_prev = 0.0, 0.0
    auc = 0.0
    tp_count, fp_count = 0, 0

    for label in y_true_sorted:
        if label == 1:
            tp_count += 1
        else:
            fp_count += 1
        tpr = tp_count / n_pos
        fpr = fp_count / n_neg
        auc += 0.5 * (tpr + tpr_prev) * (fpr - fpr_prev)
        tpr_prev, fpr_prev = tpr, fpr

    return float(auc)


def compute_ece(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    """Expected Calibration Error with uniform-width bins."""
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    for i in range(n_bins):
        mask = (y_prob >= bin_boundaries[i]) & (y_prob < bin_boundaries[i + 1])
        if i == n_bins - 1:
            mask = (y_prob >= bin_boundaries[i]) & (y_prob <= bin_boundaries[i + 1])
        if np.sum(mask) == 0:
            continue
        bin_acc = np.mean(y_true[mask])
        bin_conf = np.mean(y_prob[mask])
        bin_size = np.sum(mask)
        ece += (bin_size / len(y_true)) * abs(bin_acc - bin_conf)
    return float(ece)


def calibration_bins(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10):
    """Return (mean_predicted, fraction_positive, count) per bin."""
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    bins = []
    for i in range(n_bins):
        lo, hi = bin_boundaries[i], bin_boundaries[i + 1]
        mask = (y_prob >= lo) & (y_prob < hi) if i < n_bins - 1 else (y_prob >= lo) & (y_prob <= hi)
        count = int(np.sum(mask))
        if count == 0:
            bins.append((float((lo + hi) / 2), 0.0, 0))
        else:
            bins.append((float(np.mean(y_prob[mask])), float(np.mean(y_true[mask])), count))
    return bins


# ─── Data Loading ────────────────────────────────────────────────────

def load_hc3_samples(n_per_class: int = 250) -> list[dict]:
    """
    Load balanced human/AI samples from HC3 dataset.
    Returns list of {"text": str, "label": int, "source": str}
    label: 0=human, 1=AI

    HC3 uses a legacy loading script so we download the JSONL directly
    via huggingface_hub and parse it ourselves.
    """
    import json as _json
    from huggingface_hub import hf_hub_download

    print(f"⏳ Loading HC3 dataset (sampling {n_per_class} per class)...")
    local_path = hf_hub_download(
        repo_id="Hello-SimpleAI/HC3",
        filename="all.jsonl",
        repo_type="dataset",
    )

    human_texts = []
    ai_texts = []

    with open(local_path, "r", encoding="utf-8") as fh:
        for line in fh:
            row = _json.loads(line)
            h_answers = row.get("human_answers", [])
            a_answers = row.get("chatgpt_answers", [])

            for ans in h_answers:
                if isinstance(ans, str) and len(ans.strip()) > 50:
                    human_texts.append(ans.strip())
            for ans in a_answers:
                if isinstance(ans, str) and len(ans.strip()) > 50:
                    ai_texts.append(ans.strip())

            if len(human_texts) >= n_per_class * 3 and len(ai_texts) >= n_per_class * 3:
                break

    # Shuffle and sample
    rng = np.random.RandomState(42)
    rng.shuffle(human_texts)
    rng.shuffle(ai_texts)

    samples = []
    for text in human_texts[:n_per_class]:
        samples.append({"text": text, "label": 0, "source": "hc3_human"})
    for text in ai_texts[:n_per_class]:
        samples.append({"text": text, "label": 1, "source": "hc3_chatgpt"})

    rng.shuffle(samples)
    print(f"  ✅ Loaded {len(samples)} HC3 samples ({n_per_class} human, {n_per_class} AI)")
    return samples


def load_raid_samples(n_per_class: int = 250, domains: list[str] | None = None) -> list[dict]:
    """
    Load balanced human/AI samples from RAID dataset.
    Returns list of {"text": str, "label": int, "source": str, "model": str, "domain": str, "attack": str}
    """
    from datasets import load_dataset
    print(f"⏳ Loading RAID dataset (sampling {n_per_class} per class, streaming)...")

    ds = load_dataset("liamdugan/raid", "raid", split="train", streaming=True)

    human_texts = []
    ai_texts = []
    target_domains = set(domains) if domains else {"news", "abstracts", "wiki", "reddit", "reviews"}

    for row in ds:
        domain = row.get("domain", "unknown")
        if domain not in target_domains:
            continue

        text = row.get("generation", "")
        if not text or not isinstance(text, str) or len(text.strip()) < 50:
            continue

        model = row.get("model", "")
        attack = row.get("attack", "none") or "none"

        if model == "human":
            human_texts.append({
                "text": text.strip(),
                "label": 0,
                "source": "raid_human",
                "model": "human",
                "domain": domain,
                "attack": attack,
            })
        else:
            ai_texts.append({
                "text": text.strip(),
                "label": 1,
                "source": f"raid_{model}",
                "model": model or "unknown",
                "domain": domain,
                "attack": attack,
            })

        if len(human_texts) >= n_per_class * 3 and len(ai_texts) >= n_per_class * 3:
            break

    rng = np.random.RandomState(42)
    rng.shuffle(human_texts)
    rng.shuffle(ai_texts)

    samples = human_texts[:n_per_class] + ai_texts[:n_per_class]
    rng.shuffle(samples)
    print(f"  ✅ Loaded {len(samples)} RAID samples ({min(n_per_class, len(human_texts))} human, {min(n_per_class, len(ai_texts))} AI)")
    return samples


# ─── Classifier Inference ────────────────────────────────────────────

def run_classifier_on_samples(samples: list[dict], classifier) -> tuple[np.ndarray, np.ndarray]:
    """
    Run the AIClassifier ensemble on each sample.
    Returns (y_true, y_prob) arrays.
    """
    import asyncio

    y_true = []
    y_prob = []
    total = len(samples)

    for i, sample in enumerate(samples):
        text = sample["text"]
        # Truncate very long texts to avoid excessive inference time
        if len(text) > 3000:
            text = text[:3000]

        # Use the sync ensemble predict directly (we're not in async context)
        prob = classifier._ensemble_predict_sync(text)

        y_true.append(sample["label"])
        y_prob.append(prob)

        if (i + 1) % 25 == 0 or i == total - 1:
            print(f"  [{i+1}/{total}] Classified — latest P(AI) = {prob:.4f} (true={sample['label']})")

    return np.array(y_true), np.array(y_prob)


# ─── Report Generation ──────────────────────────────────────────────

def print_report(name: str, y_true: np.ndarray, y_prob: np.ndarray, extra_cols: dict | None = None):
    """Print a formatted metrics report."""
    metrics = compute_metrics(y_true, y_prob)
    auroc = compute_auroc(y_true, y_prob)
    ece = compute_ece(y_true, y_prob)
    bins = calibration_bins(y_true, y_prob)

    print(f"\n{'═' * 65}")
    print(f" {name}")
    print(f"{'═' * 65}")
    print(f"  Samples:    {metrics['n']}")
    print(f"  Accuracy:   {metrics['accuracy']:.4f}")
    print(f"  Precision:  {metrics['precision']:.4f}")
    print(f"  Recall:     {metrics['recall']:.4f}")
    print(f"  F1:         {metrics['f1']:.4f}")
    print(f"  AUROC:      {auroc:.4f}")
    print(f"  ECE:        {ece:.4f}")
    print(f"  Confusion:  TP={metrics['tp']}  FP={metrics['fp']}  FN={metrics['fn']}  TN={metrics['tn']}")
    print(f"\n  Calibration bins (predicted → actual):")
    for pred, actual, count in bins:
        bar = "█" * int(count / max(1, max(b[2] for b in bins)) * 20)
        if count > 0:
            print(f"    [{pred:.2f}] → {actual:.2f}  (n={count:>4}) {bar}")

    # Save as JSON for regression tracking
    result = {
        "name": name,
        "timestamp": datetime.now().isoformat(),
        **metrics,
        "auroc": auroc,
        "ece": ece,
        "calibration_bins": [{"predicted": p, "actual": a, "count": c} for p, a, c in bins],
    }

    return result


def print_per_group_report(name: str, samples: list[dict], y_prob: np.ndarray, group_key: str):
    """Print metrics broken down by a grouping key (e.g., model, domain, attack)."""
    groups: dict[str, list[int]] = {}
    for i, s in enumerate(samples):
        key = s.get(group_key, "unknown")
        groups.setdefault(key, []).append(i)

    print(f"\n  {'─' * 55}")
    print(f"  Per-{group_key} breakdown:")
    print(f"  {'─' * 55}")
    print(f"  {'Group':<20} {'N':>5} {'Acc':>7} {'F1':>7} {'AUROC':>7} {'ECE':>7}")
    print(f"  {'─' * 55}")

    for group_name in sorted(groups.keys()):
        idx = groups[group_name]
        if len(idx) < 5:
            continue
        y_t = np.array([samples[i]["label"] for i in idx])
        y_p = y_prob[idx]

        if len(set(y_t)) < 2:
            # Can't compute AUROC with single class
            m = compute_metrics(y_t, y_p)
            print(f"  {group_name:<20} {m['n']:>5} {m['accuracy']:>7.3f} {m['f1']:>7.3f} {'  N/A':>7} {compute_ece(y_t, y_p):>7.3f}")
        else:
            m = compute_metrics(y_t, y_p)
            auc = compute_auroc(y_t, y_p)
            ece = compute_ece(y_t, y_p)
            print(f"  {group_name:<20} {m['n']:>5} {m['accuracy']:>7.3f} {m['f1']:>7.3f} {auc:>7.3f} {ece:>7.3f}")


# ─── Main ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Benchmark AI Detector Pipeline")
    parser.add_argument("--quick", action="store_true", help="Quick mode: 50 samples per class")
    parser.add_argument("--hc3-only", action="store_true", help="Only run HC3 benchmark")
    parser.add_argument("--raid-only", action="store_true", help="Only run RAID benchmark")
    parser.add_argument("--n", type=int, default=None, help="Samples per class (overrides --quick)")
    parser.add_argument("--output", type=str, default=None, help="Save results JSON to file")
    args = parser.parse_args()

    n_per_class = args.n or (50 if args.quick else 250)
    results = []

    # ── Load classifier ──────────────────────────────────────────────
    print("🔧 Initializing AI Classifier ensemble...")
    from app.services.ai_classifier import get_ai_classifier
    classifier = get_ai_classifier()
    classifier._ensure_models()

    if not classifier._models:
        print("❌ FATAL: No models loaded. Install transformers + torch.")
        sys.exit(1)

    print(f"  ✅ Loaded {len(classifier._models)} models:")
    for m in classifier._models:
        n_params = sum(p.numel() for p in m['model'].parameters()) / 1e6
        print(f"     • {m['name']} (weight={m['weight']:.2f}, params={n_params:.1f}M)")

    # ── HC3 Benchmark ────────────────────────────────────────────────
    if not args.raid_only:
        hc3_samples = load_hc3_samples(n_per_class=n_per_class)

        print(f"\n🔬 Running classifier on {len(hc3_samples)} HC3 samples...")
        t0 = time.time()
        y_true_hc3, y_prob_hc3 = run_classifier_on_samples(hc3_samples, classifier)
        elapsed_hc3 = time.time() - t0
        print(f"  ⏱  Inference time: {elapsed_hc3:.1f}s ({elapsed_hc3/len(hc3_samples):.2f}s/sample)")

        r = print_report("HC3 Benchmark (Human vs ChatGPT)", y_true_hc3, y_prob_hc3)
        r["inference_time_s"] = elapsed_hc3
        r["time_per_sample_s"] = elapsed_hc3 / len(hc3_samples)
        results.append(r)

    # ── RAID Benchmark ───────────────────────────────────────────────
    if not args.hc3_only:
        raid_samples = load_raid_samples(n_per_class=n_per_class)

        print(f"\n🔬 Running classifier on {len(raid_samples)} RAID samples...")
        t0 = time.time()
        y_true_raid, y_prob_raid = run_classifier_on_samples(raid_samples, classifier)
        elapsed_raid = time.time() - t0
        print(f"  ⏱  Inference time: {elapsed_raid:.1f}s ({elapsed_raid/len(raid_samples):.2f}s/sample)")

        r = print_report("RAID Benchmark (Multi-LLM, Multi-Domain)", y_true_raid, y_prob_raid)
        r["inference_time_s"] = elapsed_raid
        r["time_per_sample_s"] = elapsed_raid / len(raid_samples)
        results.append(r)

        # Per-domain and per-model breakdowns
        print_per_group_report("RAID", raid_samples, y_prob_raid, "domain")
        print_per_group_report("RAID", raid_samples, y_prob_raid, "model")

        # Clean vs adversarial
        clean_idx = [i for i, s in enumerate(raid_samples) if s.get("attack", "none") == "none"]
        adv_idx = [i for i, s in enumerate(raid_samples) if s.get("attack", "none") != "none"]

        if clean_idx:
            y_t_clean = np.array([raid_samples[i]["label"] for i in clean_idx])
            y_p_clean = y_prob_raid[np.array(clean_idx)]
            print_report("RAID — Clean Texts Only", y_t_clean, y_p_clean)

        if adv_idx:
            y_t_adv = np.array([raid_samples[i]["label"] for i in adv_idx])
            y_p_adv = y_prob_raid[np.array(adv_idx)]
            print_report("RAID — Adversarial Texts Only", y_t_adv, y_p_adv)
            print_per_group_report("RAID-Adversarial", [raid_samples[i] for i in adv_idx],
                                   y_p_adv, "attack")

    # ── Save results ─────────────────────────────────────────────────
    output_path = args.output or str(Path(__file__).parent / "results_ai_detector.json")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Results saved to {output_path}")

    # ── Summary ──────────────────────────────────────────────────────
    print(f"\n{'═' * 65}")
    print(f" SUMMARY")
    print(f"{'═' * 65}")
    for r in results:
        status = "✅ PASS" if r["f1"] >= 0.80 and r["auroc"] >= 0.85 else "⚠️  NEEDS WORK"
        print(f"  {r['name']}")
        print(f"    F1={r['f1']:.3f}  AUROC={r['auroc']:.3f}  ECE={r['ece']:.3f}  → {status}")
    print(f"{'═' * 65}\n")


if __name__ == "__main__":
    main()
