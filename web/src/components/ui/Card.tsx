import { ReactNode } from 'react';

interface CardProps {
  /** Card title displayed in header */
  title?: string;
  /** Card content */
  children: ReactNode;
  /** Additional CSS classes */
  className?: string;
  /** Card padding size */
  padding?: 'none' | 'sm' | 'md' | 'lg';
  /** Show border */
  bordered?: boolean;
  /** Show shadow */
  shadow?: boolean;
}

const paddingStyles = {
  none: '',
  sm: 'p-4',
  md: 'p-6',
  lg: 'p-8',
};

/**
 * Card component for containing content sections
 */
export default function Card({
  title,
  children,
  className = '',
  padding = 'md',
  bordered = true,
  shadow = true,
}: CardProps) {
  return (
    <div
      className={`
        flex flex-col
        rounded-lg
        bg-[var(--background-secondary)]
        ${bordered ? 'border border-[var(--border)]' : ''}
        ${shadow ? 'shadow-sm' : ''}
        ${className}
      `}
    >
      {title && (
        <div className="border-b border-[var(--border)] px-6 py-4">
          <h3 className="text-lg font-semibold text-[var(--foreground)]">
            {title}
          </h3>
        </div>
      )}
      <div className={`${paddingStyles[padding]} flex-1`}>{children}</div>
    </div>
  );
}
