"use client";

import Link from "next/link";
import { Mail, MessageSquare, MapPin, ExternalLink } from "lucide-react";
import { useState } from "react";

export default function ContactPage() {
  const [submitted, setSubmitted] = useState(false);
  const [form, setForm] = useState({ name: "", email: "", subject: "", message: "" });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // In production, POST to /api/v1/contact or a third-party form service
    console.log("Contact form submitted:", form);
    setSubmitted(true);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-950 to-slate-900 text-white">
      {/* Navigation */}
      <nav className="border-b border-slate-800 bg-slate-950/80 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link href="/" className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            DocGuard & CareerMatch
          </Link>
          <div className="flex items-center gap-6 text-sm text-slate-400">
            <Link href="/about" className="hover:text-white transition">About</Link>
            <Link href="/pricing" className="hover:text-white transition">Pricing</Link>
            <Link href="/contact" className="text-white">Contact</Link>
            <Link href="/dashboard" className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-500 transition">
              Dashboard
            </Link>
          </div>
        </div>
      </nav>

      <main className="max-w-5xl mx-auto px-6 py-20">
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold mb-4">Get in Touch</h1>
          <p className="text-xl text-slate-400">
            Have questions or feedback? We&apos;d love to hear from you.
          </p>
        </div>

        <div className="grid md:grid-cols-3 gap-8 mb-16">
          {[
            {
              icon: Mail,
              title: "Email",
              detail: "support@docguard.ai",
              sub: "We respond within 24 hours",
            },
            {
              icon: MessageSquare,
              title: "Live Chat",
              detail: "Available Mon–Fri",
              sub: "9 AM – 6 PM PST",
            },
            {
              icon: MapPin,
              title: "Location",
              detail: "San Francisco, CA",
              sub: "United States",
            },
          ].map((item, i) => (
            <div
              key={i}
              className="bg-slate-800/50 rounded-xl p-6 border border-slate-700 text-center"
            >
              <item.icon className="w-8 h-8 text-blue-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold mb-1">{item.title}</h3>
              <p className="text-white">{item.detail}</p>
              <p className="text-sm text-slate-500">{item.sub}</p>
            </div>
          ))}
        </div>

        {submitted ? (
          <div className="bg-green-900/30 border border-green-700 rounded-2xl p-12 text-center">
            <h2 className="text-2xl font-bold text-green-400 mb-2">Message Sent!</h2>
            <p className="text-slate-400">
              Thank you for reaching out. We&apos;ll get back to you shortly.
            </p>
          </div>
        ) : (
          <form
            onSubmit={handleSubmit}
            className="bg-slate-800/50 rounded-2xl p-8 border border-slate-700 max-w-2xl mx-auto"
          >
            <h2 className="text-2xl font-bold mb-6">Send a Message</h2>
            <div className="grid md:grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-sm text-slate-400 mb-1">Name</label>
                <input
                  type="text"
                  required
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500 transition"
                  placeholder="Your name"
                />
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-1">Email</label>
                <input
                  type="email"
                  required
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  className="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500 transition"
                  placeholder="you@example.com"
                />
              </div>
            </div>
            <div className="mb-4">
              <label className="block text-sm text-slate-400 mb-1">Subject</label>
              <input
                type="text"
                required
                value={form.subject}
                onChange={(e) => setForm({ ...form, subject: e.target.value })}
                className="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500 transition"
                placeholder="How can we help?"
              />
            </div>
            <div className="mb-6">
              <label className="block text-sm text-slate-400 mb-1">Message</label>
              <textarea
                required
                rows={5}
                value={form.message}
                onChange={(e) => setForm({ ...form, message: e.target.value })}
                className="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:border-blue-500 transition resize-none"
                placeholder="Tell us more..."
              />
            </div>
            <button
              type="submit"
              className="w-full py-3 bg-blue-600 text-white rounded-lg font-semibold hover:bg-blue-500 transition"
            >
              Send Message
            </button>
          </form>
        )}

        {/* Links */}
        <div className="mt-16 text-center">
          <h3 className="text-lg font-semibold mb-4">Other Resources</h3>
          <div className="flex justify-center gap-6 text-sm">
            <a
              href="https://github.com/ANKITSANJYAL/AI-ATS-Detector"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-blue-400 hover:text-blue-300 transition"
            >
              GitHub <ExternalLink className="w-3 h-3" />
            </a>
            <Link href="/docs" className="text-blue-400 hover:text-blue-300 transition">
              API Docs
            </Link>
            <Link href="/pricing" className="text-blue-400 hover:text-blue-300 transition">
              Pricing
            </Link>
          </div>
        </div>
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
