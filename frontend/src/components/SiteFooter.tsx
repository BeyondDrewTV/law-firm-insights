import { Link } from "react-router-dom";

const SiteFooter = () => (
  <footer className="border-t border-slate-200 bg-slate-100 py-10">
    <div className="section-container">
      <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
        <div className="max-w-md">
          <p className="text-sm font-semibold text-slate-900">Clarion</p>
          <p className="mt-1 text-xs text-slate-600">
            Turn scattered client feedback into clear insights and implementation plans for professional services
            firms.
          </p>
        </div>
        <div className="grid gap-6 text-xs text-slate-600 sm:grid-cols-2">
          <div>
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Product</p>
            <div className="grid gap-y-2">
              <Link to="/features" className="transition-colors hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">Features</Link>
              <Link to="/how-it-works" className="transition-colors hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">How It Works</Link>
              <Link to="/pricing" className="transition-colors hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">Pricing</Link>
              <Link to="/contact" className="transition-colors hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">Contact</Link>
            </div>
          </div>
          <div>
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">Trust</p>
            <div className="grid gap-y-2">
              <Link to="/security" className="transition-colors hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">Security</Link>
              <Link to="/terms" className="transition-colors hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">Terms</Link>
              <Link to="/privacy" className="transition-colors hover:text-slate-900 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2">Privacy</Link>
            </div>
          </div>
        </div>
      </div>
      <p className="mt-6 text-center text-xs text-slate-500">&copy; {new Date().getFullYear()} Clarion. All rights reserved.</p>
    </div>
  </footer>
);

export default SiteFooter;
