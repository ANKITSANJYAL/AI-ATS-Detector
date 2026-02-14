#!/usr/bin/env python3
"""
Evaluation script for the AI detection ensemble.

Usage:
    python scripts/eval_classifier.py

Runs the 3-model ensemble against a small labeled benchmark and prints
precision/recall/F1 plus a calibration summary.  This is the script a
DeepMind engineer would run to validate model quality before deploying
new weights.

The benchmark is embedded (no external data needed) — it contains 20
human-written and 20 AI-generated samples covering different styles.
"""
import asyncio
import sys
import os

# Add backend root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.ai_classifier import AIClassifier


# ── Benchmark dataset ──────────────────────────────────────────────────
# label=1 means AI-generated, label=0 means human-written

BENCHMARK = [
    # Human-written samples (label=0)
    (0, "I woke up early today and honestly couldn't decide what to have for breakfast. Ended up making some toast and — yeah — burning it a little."),
    (0, "So my cat just knocked my coffee off the table again. Third time this week. I'm starting to think she's doing it on purpose."),
    (0, "Been working on this bug for hours now. Turns out I was missing a semicolon. A SEMICOLON. I need a break."),
    (0, "Just got back from the grocery store and forgot the one thing I went for. Classic me."),
    (0, "My neighbor's dog barks every single morning at 6 AM. I've tried earplugs, white noise, everything. Nothing works."),
    (0, "The sunset was absolutely gorgeous yesterday. Took a pic but my phone camera doesn't do it justice at all."),
    (0, "I tried making sourdough bread during lockdown and it was a disaster. Like a frisbee. My roommate still brings it up."),
    (0, "Had the weirdest dream last night where I was late for an exam I hadn't studied for. Haven't been in school for ten years."),
    (0, "My grandmother's recipe for apple pie is the best thing I've ever tasted. She never measured anything, just went by feel."),
    (0, "We went camping last weekend and it rained the ENTIRE time. Still had a blast though, honestly."),
    (0, "The interview went... okay? I couldn't tell if they liked me or not. The interviewer had a poker face the whole time."),
    (0, "I've been reading this book about habits and it's actually changed how I start my mornings. Small wins, you know?"),
    (0, "Traffic was insane today. Took me an hour and a half to get to work when it usually takes 20 minutes."),
    (0, "My kid drew a picture of our family and gave me stick legs and giant hands. It's on the fridge now."),
    (0, "Found a $20 bill in my old jacket pocket today. Best surprise ever when you're broke."),
    (0, "The restaurant we went to was so loud I could barely hear my friend across the table. Food was good though."),
    (0, "I hate how autocorrect changes 'duck' to... well, you know. Sent the wrong thing to my boss AGAIN."),
    (0, "Spent the whole afternoon organizing my closet and now it looks amazing. Give it a week though."),
    (0, "My flight got delayed three hours and the airline gave us a $5 food voucher. Thanks, that covers half a sandwich."),
    (0, "Learned to ride a bike at age 30. Yes, thirty. Better late than never, right?"),

    # AI-generated samples (label=1)
    (1, "In today's rapidly evolving digital landscape, it is imperative to understand the multifaceted challenges that organizations face in maintaining competitive advantage."),
    (1, "Furthermore, the implementation of robust frameworks is essential for ensuring sustainable growth and long-term organizational resilience in an uncertain market."),
    (1, "The integration of artificial intelligence into healthcare systems presents both unprecedented opportunities and significant ethical considerations that warrant careful examination."),
    (1, "It is important to note that the correlation between educational attainment and socioeconomic mobility has been extensively documented in peer-reviewed literature."),
    (1, "Moreover, strategic alignment between technological capabilities and business objectives remains a critical success factor for enterprises navigating digital transformation."),
    (1, "The proliferation of cloud computing technologies has fundamentally reshaped the paradigm of enterprise software deployment and infrastructure management."),
    (1, "Subsequently, organizations must adapt their operational paradigms to remain relevant in an increasingly interconnected and data-driven global marketplace."),
    (1, "The intersection of machine learning and natural language processing has yielded significant advancements in automated text generation and comprehension capabilities."),
    (1, "In conclusion, the evidence overwhelmingly suggests that proactive stakeholder engagement is essential for the successful implementation of organizational change initiatives."),
    (1, "It should be noted that the methodological framework employed in this analysis leverages both quantitative and qualitative approaches to ensure comprehensive coverage."),
    (1, "The advent of renewable energy technologies represents a paradigm shift in how societies conceptualize and implement sustainable energy solutions for future generations."),
    (1, "Additionally, the optimization of supply chain logistics through predictive analytics has demonstrated measurable improvements in operational efficiency and cost reduction."),
    (1, "The growing emphasis on data privacy and cybersecurity underscores the need for organizations to implement comprehensive governance frameworks and compliance protocols."),
    (1, "Consequently, the development of cross-functional collaboration mechanisms is paramount for driving innovation and maintaining organizational agility in dynamic environments."),
    (1, "The transformative potential of blockchain technology extends beyond cryptocurrency applications, encompassing supply chain transparency, digital identity verification, and decentralized governance."),
    (1, "Nevertheless, the challenges associated with scaling artificial intelligence solutions across diverse organizational contexts remain substantial and multifaceted."),
    (1, "The systematic review of existing literature reveals a consensus regarding the positive impact of emotional intelligence on leadership effectiveness and team performance."),
    (1, "Furthermore, the integration of sustainability principles into corporate strategy has emerged as a critical determinant of long-term shareholder value and brand reputation."),
    (1, "The empirical evidence suggests that organizations with diverse leadership teams demonstrate superior financial performance and enhanced decision-making capabilities."),
    (1, "In summary, the convergence of technological innovation and organizational design theory provides a robust foundation for understanding contemporary management challenges."),
]


async def main():
    print("=" * 60)
    print("AI Detection Ensemble Evaluation")
    print("=" * 60)

    clf = AIClassifier()
    clf._ensure_models()

    if not clf._models:
        print("\nERROR: No models loaded. Install transformers + torch first.")
        print("  pip install transformers torch")
        sys.exit(1)

    print(f"\nModels loaded: {len(clf._models)}")
    for m in clf._models:
        print(f"  - {m['name']} (weight={m['weight']})")

    print(f"\nRunning {len(BENCHMARK)} samples...\n")

    tp = fp = tn = fn = 0
    calibration_bins = {i: {"count": 0, "ai_count": 0, "prob_sum": 0.0} for i in range(10)}

    for label, text in BENCHMARK:
        is_ai, confidence, reason = await clf.classify_text(text)
        pred = 1 if is_ai else 0
        prob = confidence if is_ai else (1 - confidence)

        # Confusion matrix
        if pred == 1 and label == 1:
            tp += 1
        elif pred == 1 and label == 0:
            fp += 1
        elif pred == 0 and label == 0:
            tn += 1
        else:
            fn += 1

        # Calibration
        bin_idx = min(9, int(prob * 10))
        calibration_bins[bin_idx]["count"] += 1
        calibration_bins[bin_idx]["ai_count"] += label
        calibration_bins[bin_idx]["prob_sum"] += prob

    # Metrics
    total = tp + fp + tn + fn
    accuracy = (tp + tn) / total if total > 0 else 0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    print("Confusion Matrix:")
    print(f"  TP={tp}  FP={fp}")
    print(f"  FN={fn}  TN={tn}")
    print()
    print(f"Accuracy:  {accuracy:.1%}")
    print(f"Precision: {precision:.1%}")
    print(f"Recall:    {recall:.1%}")
    print(f"F1 Score:  {f1:.1%}")
    print()
    print("Calibration (predicted prob vs actual rate):")
    print(f"  {'Bin':>10}  {'Count':>5}  {'Pred Prob':>10}  {'Actual Rate':>12}")
    for i in range(10):
        b = calibration_bins[i]
        if b["count"] > 0:
            avg_prob = b["prob_sum"] / b["count"]
            actual_rate = b["ai_count"] / b["count"]
            print(f"  {i*10:>3}-{(i+1)*10:>3}%  {b['count']:>5}  {avg_prob:>10.1%}  {actual_rate:>12.1%}")

    print()
    if f1 >= 0.8:
        print("PASS: F1 >= 0.80")
    else:
        print(f"WARN: F1 = {f1:.2f} (target >= 0.80)")

    print("\nModel versions:")
    for name, rev in clf.model_versions.items():
        print(f"  {name}: {rev}")


if __name__ == "__main__":
    asyncio.run(main())
