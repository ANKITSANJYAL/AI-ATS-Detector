"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  FileText,
  Target,
  Clock,
  CreditCard,
  BarChart3,
  Shield,
  TrendingUp,
  Loader2,
} from "lucide-react";
import { config } from "../lib/config";
import OnboardingWizard from "../components/OnboardingWizard";

interface UsageSummary {
  ai_detection_count: number;
  ats_scoring_count: number;
  total_usage: number;
}

interface SubscriptionStatus {
  status: string;
  plan: string;
  usage_limit: number;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
}

export default function DashboardPage() {
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchDashboard() {
      try {
        const [usageRes, subRes] = await Promise.allSettled([
          fetch(`${config.apiV1}/billing/usage`),
          fetch(`${config.apiV1}/billing/status`),
        ]);

        if (usageRes.status === "fulfilled" && usageRes.value.ok) {
          setUsage(await usageRes.value.json());
        }
        if (subRes.status === "fulfilled" && subRes.value.ok) {
          setSubscription(await subRes.value.json());
        }
      } catch {
        // Dashboard works without billing data
      } finally {
        setLoading(false);
      }
    }
    fetchDashboard();
  }, []);

  const planBadge = subscription?.plan || "free";
  const planColor =
    planBadge === "pro"
      ? "bg-blue-500/20 text-blue-400 border-blue-500/50"
      : planBadge === "enterprise"
      ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/50"
      : "bg-slate-700 text-slate-400 border-slate-600";

  return (
    <main className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      <OnboardingWizard />
      <div className="max-w-6xl mx-auto px-4 py-16">
        <div className="flex items-center justify-between mb-12">
          <div>
            <h1 className="text-4xl font-bold text-white mb-2">Dashboard</h1>
            <p className="text-slate-400">Welcome back. Here&apos;s your overview.</p>
          </div>
          <span
            className={`px-4 py-1.5 rounded-full text-sm font-semibold border ${planColor} capitalize`}
          >
            {planBadge} Plan
          </span>
        </div>

        {/* Usage Stats Cards */}
        <div className="grid md:grid-cols-4 gap-6 mb-12">
          <StatCard
            icon={<Shield className="w-6 h-6 text-blue-400" />}
            label="AI Detections"
            value={loading ? "..." : String(usage?.ai_detection_count ?? 0)}
            color="blue"
          />
          <StatCard
            icon={<Target className="w-6 h-6 text-emerald-400" />}
            label="ATS Scores"
            value={loading ? "..." : String(usage?.ats_scoring_count ?? 0)}
            color="emerald"
          />
          <StatCard
            icon={<BarChart3 className="w-6 h-6 text-purple-400" />}
            label="Total Analyses"
            value={loading ? "..." : String(usage?.total_usage ?? 0)}
            color="purple"
          />
          <StatCard
            icon={<TrendingUp className="w-6 h-6 text-amber-400" />}
            label="Usage Limit"
            value={
              loading
                ? "..."
                : subscription?.usage_limit === -1
                ? "∞"
                : String(subscription?.usage_limit ?? 5)
            }
            color="amber"
          />
        </div>

        {/* Quick Actions */}
        <h2 className="text-xl font-semibold text-white mb-6">Quick Actions</h2>
        <div className="grid md:grid-cols-4 gap-6 mb-12">
          <ActionCard
            href="/ai-detector"
            icon={<FileText className="w-8 h-8 text-blue-400" />}
            title="AI Detector"
            description="Detect AI-generated content"
            hoverColor="hover:border-blue-500/50"
          />
          <ActionCard
            href="/ats-checker"
            icon={<Target className="w-8 h-8 text-emerald-400" />}
            title="ATS Checker"
            description="Score your resume"
            hoverColor="hover:border-emerald-500/50"
          />
          <ActionCard
            href="/history"
            icon={<Clock className="w-8 h-8 text-purple-400" />}
            title="History"
            description="View past analyses"
            hoverColor="hover:border-purple-500/50"
          />
          <ActionCard
            href="/pricing"
            icon={<CreditCard className="w-8 h-8 text-amber-400" />}
            title="Upgrade"
            description="View plans & billing"
            hoverColor="hover:border-amber-500/50"
          />
        </div>

        {/* Subscription Info */}
        {subscription && subscription.status !== "free" && (
          <div className="bg-slate-800/50 border border-slate-700 rounded-2xl p-6">
            <h2 className="text-lg font-semibold text-white mb-4 flex items-center">
              <CreditCard className="w-5 h-5 mr-2 text-slate-400" />
              Subscription
            </h2>
            <div className="grid md:grid-cols-3 gap-4 text-sm">
              <div>
                <span className="text-slate-400">Status</span>
                <p className="text-white capitalize">{subscription.status}</p>
              </div>
              <div>
                <span className="text-slate-400">Current Period Ends</span>
                <p className="text-white">
                  {subscription.current_period_end
                    ? new Date(subscription.current_period_end).toLocaleDateString()
                    : "N/A"}
                </p>
              </div>
              <div>
                <span className="text-slate-400">Auto-Renew</span>
                <p className="text-white">
                  {subscription.cancel_at_period_end ? "No (cancels at period end)" : "Yes"}
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}

function StatCard({
  icon,
  label,
  value,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
      <div className="flex items-center justify-between mb-3">
        {icon}
      </div>
      <p className="text-3xl font-bold text-white">{value}</p>
      <p className="text-slate-400 text-sm mt-1">{label}</p>
    </div>
  );
}

function ActionCard({
  href,
  icon,
  title,
  description,
  hoverColor,
}: {
  href: string;
  icon: React.ReactNode;
  title: string;
  description: string;
  hoverColor: string;
}) {
  return (
    <Link
      href={href}
      className={`bg-slate-800/50 border border-slate-700 rounded-xl p-6 transition-colors group ${hoverColor}`}
    >
      <div className="mb-3 group-hover:scale-110 transition-transform">{icon}</div>
      <h3 className="text-white font-semibold">{title}</h3>
      <p className="text-slate-400 text-sm">{description}</p>
    </Link>
  );
}
