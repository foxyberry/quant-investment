/**
 * Footer component with copyright and version info
 */
export default function Footer() {
  const currentYear = new Date().getFullYear();
  const version = process.env.NEXT_PUBLIC_APP_VERSION || '0.1.0';

  return (
    <footer className="border-t border-[var(--border)] bg-[var(--background-secondary)] py-4 px-6">
      <div className="flex flex-col sm:flex-row items-center justify-between gap-2 text-sm text-[var(--foreground-muted)]">
        <p>
          &copy; {currentYear} Quant Investment. All rights reserved.
        </p>
        <p>
          Version {version}
        </p>
      </div>
    </footer>
  );
}
