"use client";

import Link from "next/link";
import { ArrowLeft, Check, Zap, Building2, Sparkles } from "lucide-react";
import { config } from "../lib/config";
import { useState } from "react";

const plans = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    description: "Try it out with limited usage",
    features: [
      "5 AI detections per month",
      "5 ATS scores per month",
      "Basic sentence analysis",
      "Community support",
    ],
    cta: "Get Started",
    href: "/sign-up",
    highlight: false,
    icon: Sparkles,
    color: "slate",
  },
  {
    name: "Pro",
    price: "$19",
    period: "/month",
    description: "For job seekers and content creators",
    features: [
      "Unlimited AI detections",
      "Unlimited ATS scores",
      "Sentence-level analysis",
      "Multi-model ensemble detection",
      "PDF/CSV export",
      "Analysis history",
      "Priority support",
    ],
    cta: "Start Pro Plan",
    plan: "pro",
    highlight: true,
    icon: Zap,
    color: "blue",
  },
  {
    name: "Enterprise",
    price: "$99",
    period: "/month",
    description: "For teams and organizations",
    features: [
      "Everything in Pro",
      "Team workspace (up to 25 seats)",
      "API access & webhooks",
      "Bulk document analysis",
      "Custom model training",
      "SSO / SAML integration",
      "Dedicated account manager",
      "99.9% SLA",
    ],
    cta: "Contact Sales",
    plan: "enterprise",
    highlight: false,
    icon: Building2,
    color: "emerald",
  },
];

export default function PricingPage() {
  const [loading, setLoading] = useState<string | null>(null);

  const handleCheckout = async (plan: string) => {
    setLoading(plan);
    try {
      const res = await fetch(`${config.apiV1}/billing/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          plan,
          success_url: `${window.location.origin}/dashboard?checkout=success`,
          cancel_url: `${window.location.origin}/pricing?checkout=cancelled`,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        alert(data.detail || "Billing is not configured yet. Coming soon!");
        return;
      }

      const data = await res.json();
      window.location.href = data.checkout_url;
    } catch {
      alert("Unable to start checkout. Please try again.");
    } finally {
      setLoading(null);
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <div className="max-w-6xl mx-auto px-4 py-16">
        <Link
          href="/"
          className="inline-flex items-center text-slate-400 hover:text-white mb-12"
        >
          <ArrowLeft className="w-5 h-5 mr-2" />
          Back to Home
        </Link>

        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
            Simple, Transparent Pricing
          </h1>
          <p className="text-slate-400 text-lg max-w-2xl mx-auto">
            Start free. Upgrade when you need more. Cancel anytime.
          </p>
        </div>

        {/* Plans grid */}
        <div className="grid md:grid-cols-3 gap-8 mb-16">
          {plans.map((plan) => {
            const Icon = plan.icon;
            const isHighlight = plan.highlight;
            return (
              <div
                key={plan.name}
                className={`relative rounded-2xl p-8 ${
                  isHighlight
                    ? "bg-blue-500/10 border-2 border-blue-500 shadow-2xl shadow-blue-500/20"
                    : "bg-slate-800/50 border border-slate-700"
                }`}
              >
                {isHighlight && (
                  <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-blue-500 text-white px-4 py-1 rounded-full text-sm font-semibold">
                    Most Popular
                  </div>
                )}

                <Icon
                  className={`w-10 h-10 mb-4 ${
                    isHighlight
                      ? "text-blue-400"
                      : plan.color === "emerald"
                      ? "text-emerald-400"
                      : "text-slate-400"
                  }`}
                />

                <h2 className="text-2xl font-bold text-white mb-1">{plan.name}</h2>
                <div className="flex items-baseline mb-2">
                  <span className="text-4xl font-bold text-white">{plan.price}</span>
                  <span className="text-slate-400 ml-1">{plan.period}</span>
                </div>
                <p className="text-slate-400 text-sm mb-6">{plan.description}</p>

                <ul className="space-y-3 mb-8">
                  {plan.features.map((feature) => (
                    <li key={feature} className="flex items-start text-sm">
                      <Check className="w-4 h-4 text-emerald-400 mr-2 mt-0.5 flex-shrink-0" />
                      <span className="text-slate-300">{feature}</span>
                    </li>
                  ))}
                </ul>

                {plan.href ? (
                  <Link
                    href={plan.href}
                    className={`block w-full text-center py-3 rounded-lg font-semibold transition-colors ${
                      isHighlight
                        ? "bg-blue-500 text-white hover:bg-blue-600"
                        : "bg-slate-700 text-white hover:bg-slate-600"
                    }`}
                  >
                    {plan.cta}
                  </Link>
                ) : (
                  <button
                    onClick={() => plan.plan && handleCheckout(plan.plan)}
                    disabled={loading === plan.plan}
                    className={`w-full py-3 rounded-lg font-semibold transition-colors disabled:opacity-50 ${
                      isHighlight
                        ? "bg-blue-500 text-white hover:bg-blue-600"
                        : plan.color === "emerald"
                        ? "bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 border border-emerald-500/50"
                        : "bg-slate-700 text-white hover:bg-slate-600"
                    }`}
                  >
                    {loading === plan.plan ? "Loading..." : plan.cta}
                  </button>
                )}
              </div>
            );
          })}
        </div>

        {/* FAQ */}
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-bold text-white mb-8 text-center">
            Frequently Asked Questions
          </h2>
          <div className="space-y-6">
            {[
              {
                q: "Can I cancel anytime?",
                a: "Yes! You can cancel your subscription at any time from your dashboard. Your access continues until the end of the billing period.",
              },
              {
                q: "What payment methods do you accept?",
                a: "We accept all major credit cards, debit cards, and Apple Pay through our secure Stripe payment processor.",
              },
              {
                q: "Is my data secure?",
                a: "Absolutely. Documents are encrypted at rest, processed in isolated containers, and automatically purged after 30 days. We never train on your data.",
              },
              {
                q: "What AI models do you detect?",
                a: "Our multi-model ensemble detects content from GPT-3.5, GPT-4, Claude, Gemini, and other major LLMs with sentence-level precision.",
              },
            ].map((faq) => (
              <div
                key={faq.q}
                className="bg-slate-800/50 border border-slate-700 rounded-xl p-6"
              >
                <h3 className="text-white font-semibold mb-2">{faq.q}</h3>
                <p className="text-slate-400 text-sm">{faq.a}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
