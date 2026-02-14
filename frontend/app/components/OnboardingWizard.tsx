"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useUser } from "@clerk/nextjs";
import { ArrowRight, Shield, Target, Sparkles, CheckCircle, X } from "lucide-react";

const ONBOARDING_KEY = "docguard_onboarding_completed";

interface Step {
  icon: React.ElementType;
  title: string;
  description: string;
  action: string;
  href: string;
}

const steps: Step[] = [
  {
    icon: Shield,
    title: "Try AI Detection",
    description: "Upload a document or paste text to detect AI-generated content with sentence-level analysis.",
    action: "Go to AI Detector",
    href: "/ai-detector",
  },
  {
    icon: Target,
    title: "Score Your Resume",
    description: "Upload your resume and a job description to get an ATS compatibility score with actionable feedback.",
    action: "Go to ATS Checker",
    href: "/ats-checker",
  },
  {
    icon: Sparkles,
    title: "Explore Your Dashboard",
    description: "View your analysis history, usage stats, and manage your subscription.",
    action: "View Dashboard",
    href: "/dashboard",
  },
];

export default function OnboardingWizard() {
  const { user } = useUser();
  const [visible, setVisible] = useState(false);
  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    if (!user) return;
    const completed = localStorage.getItem(`${ONBOARDING_KEY}_${user.id}`);
    if (!completed) {
      setVisible(true);
    }
  }, [user]);

  const handleComplete = () => {
    if (user) {
      localStorage.setItem(`${ONBOARDING_KEY}_${user.id}`, "true");
    }
    setVisible(false);
  };

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      handleComplete();
    }
  };

  if (!visible) return null;

  const step = steps[currentStep];

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-md w-full p-8 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-white">
            Welcome to DocGuard! 👋
          </h2>
          <button
            onClick={handleComplete}
            className="text-slate-500 hover:text-white transition"
            aria-label="Close onboarding"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Step indicator */}
        <div className="flex gap-2 mb-8">
          {steps.map((_, i) => (
            <div
              key={i}
              className={`h-1 flex-1 rounded-full transition ${
                i <= currentStep ? "bg-blue-500" : "bg-slate-700"
              }`}
            />
          ))}
        </div>

        {/* Step content */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 bg-blue-600/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <step.icon className="w-8 h-8 text-blue-400" />
          </div>
          <h3 className="text-xl font-bold text-white mb-2">{step.title}</h3>
          <p className="text-slate-400 text-sm leading-relaxed">
            {step.description}
          </p>
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          <Link
            href={step.href}
            onClick={handleComplete}
            className="flex-1 text-center py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-500 transition text-sm inline-flex items-center justify-center gap-2"
          >
            {step.action} <ArrowRight className="w-4 h-4" />
          </Link>
          <button
            onClick={handleNext}
            className="px-4 py-3 text-slate-400 hover:text-white transition text-sm"
          >
            {currentStep < steps.length - 1 ? "Next" : "Done"}
          </button>
        </div>

        {/* Step count */}
        <p className="text-xs text-slate-600 text-center mt-4">
          Step {currentStep + 1} of {steps.length}
        </p>
      </div>
    </div>
  );
}
