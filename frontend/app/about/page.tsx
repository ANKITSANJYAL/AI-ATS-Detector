"use client";

import Link from "next/link";
import { Shield, Target, Users, Zap, ArrowRight } from "lucide-react";

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 to-slate-900 text-white">
      {/* Navigation */}
      <nav className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            DocGuard & CareerMatch
          </Link>
          <div className="flex items-center gap-6 text-sm text-slate-400">
            <Link href="/about" className="text-white">About</Link>
            <Link href="/pricing" className="hover:text-white transition">Pricing</Link>
            <Link href="/contact" className="hover:text-white transition">Contact</Link>
            <Link href="/dashboard" className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500 transition">
              Dashboard
            </Link>
          </div>
        </div>
      </nav>

      <main className="max-w-5xl mx-auto px-6 py-20">
        {/* Hero */}
        <div className="text-center mb-20">
          <h1 className="text-5xl font-bold mb-6">
            Building Trust in the Age of AI
          </h1>
          <p className="text-xl text-slate-400 max-w-3xl mx-auto leading-relaxed">
            DocGuard & CareerMatch is a professional-grade SaaS platform that
            helps organizations verify content authenticity and optimize career
            documents with cutting-edge AI analysis.
          </p>
        </div>

        {/* Mission */}
        <section className="mb-20">
          <h2 className="text-3xl font-bold mb-6">Our Mission</h2>
          <div className="bg-slate-800/50 rounded-2xl p-8 border border-slate-700">
            <p className="text-lg text-slate-300 leading-relaxed">
              As AI-generated content becomes indistinguishable from human
              writing, the need for reliable detection has never been greater. We
              combine multi-model ensemble analysis with linguistic forensics to
              deliver detection accuracy that institutions can trust. Alongside
              detection, our ATS scoring engine helps job seekers optimize their
              resumes with actionable, data-driven feedback.
            </p>
          </div>
        </section>

        {/* Core Values */}
        <section className="mb-20">
          <h2 className="text-3xl font-bold mb-10 text-center">What Sets Us Apart</h2>
          <div className="grid md:grid-cols-2 gap-6">
            {[
              {
                icon: Shield,
                title: "Multi-Model Ensemble",
                description:
                  "We don't rely on a single model. Our ensemble approach cross-verifies results across multiple transformers with Platt-calibrated confidence scoring.",
              },
              {
                icon: Zap,
                title: "Sentence-Level Analysis",
                description:
                  "Every sentence gets its own score with linguistic feature reasoning — perplexity, burstiness, vocabulary richness, and syntactic patterns.",
              },
              {
                icon: Target,
                title: "ATS Intelligence",
                description:
                  "Semantic similarity, keyword gap analysis, and format scoring — powered by GPT-4 Turbo for recruiter-grade resume optimization.",
              },
              {
                icon: Users,
                title: "Privacy First",
                description:
                  "Documents are processed in-memory and never stored permanently. All data is encrypted in transit and at rest.",
              },
            ].map((value, i) => (
              <div
                key={i}
                className="bg-slate-800/50 rounded-xl p-6 border border-slate-700 hover:border-slate-600 transition"
              >
                <value.icon className="w-8 h-8 text-blue-400 mb-4" />
                <h3 className="text-xl font-semibold mb-2">{value.title}</h3>
                <p className="text-slate-400">{value.description}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Tech Stack */}
        <section className="mb-20">
          <h2 className="text-3xl font-bold mb-6">Technology</h2>
          <div className="bg-slate-800/50 rounded-2xl p-8 border border-slate-700">
            <div className="grid md:grid-cols-3 gap-6 text-sm">
              <div>
                <h3 className="text-blue-400 font-semibold mb-3 uppercase tracking-wider">Frontend</h3>
                <ul className="space-y-2 text-slate-400">
                  <li>Next.js 14 (App Router)</li>
                  <li>TypeScript</li>
                  <li>TailwindCSS</li>
                  <li>Clerk Authentication</li>
                </ul>
              </div>
              <div>
                <h3 className="text-purple-400 font-semibold mb-3 uppercase tracking-wider">Backend</h3>
                <ul className="space-y-2 text-slate-400">
                  <li>FastAPI + Python 3.11+</li>
                  <li>PostgreSQL + Redis</li>
                  <li>SQLAlchemy 2.0 (async)</li>
                  <li>Alembic Migrations</li>
                </ul>
              </div>
              <div>
                <h3 className="text-green-400 font-semibold mb-3 uppercase tracking-wider">AI / ML</h3>
                <ul className="space-y-2 text-slate-400">
                  <li>RoBERTa Transformer Ensemble</li>
                  <li>Platt Calibration</li>
                  <li>GPT-4 Turbo (LLM)</li>
                  <li>Sentence Embeddings</li>
                </ul>
              </div>
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="text-center">
          <h2 className="text-3xl font-bold mb-4">Ready to Get Started?</h2>
          <p className="text-slate-400 mb-8">
            Start analyzing documents for free. No credit card required.
          </p>
          <Link
            href="/sign-up"
            className="inline-flex items-center gap-2 px-8 py-4 bg-blue-600 text-white rounded-xl font-semibold hover:bg-blue-500 transition text-lg"
          >
            Create Free Account <ArrowRight className="w-5 h-5" />
          </Link>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800 mt-20">
        <div className="max-w-7xl mx-auto px-6 py-8 text-center text-sm text-slate-500">
          © {new Date().getFullYear()} DocGuard & CareerMatch. All rights reserved.
        </div>
      </footer>
    </div>
  );
}
