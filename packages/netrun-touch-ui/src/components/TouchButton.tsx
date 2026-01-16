/**
 * TouchButton Component - Touch-optimized button with 48dp minimum targets
 *
 * Implements Material Design 3 touch target standards.
 * Uses "phantom padding" to maintain visual aesthetics while ensuring
 * sufficient touch target size.
 *
 * @version 1.0.0
 */

import React, { forwardRef } from 'react';
import { useHaptics } from '../hooks/useHaptics';
import { useReducedMotion } from '../hooks/useReducedMotion';

export interface TouchButtonProps
  extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, 'style'> {
  /** Button variant */
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'destructive';
  /** Size variant - all meet 48dp minimum */
  size?: 'default' | 'lg' | 'icon';
  /** Enable haptic feedback on tap */
  haptic?: boolean;
  /** Visual width can be smaller than touch target */
  compact?: boolean;
  /** Loading state */
  loading?: boolean;
  /** Icon to display */
  icon?: React.ReactNode;
  /** Icon position */
  iconPosition?: 'left' | 'right';
  /** Additional inline styles */
  style?: React.CSSProperties;
}

const sizeStyles: Record<string, React.CSSProperties> = {
  default: {
    minHeight: '48px',
    minWidth: '48px',
    padding: '12px 24px',
    fontSize: '16px',
  },
  lg: {
    minHeight: '56px',
    minWidth: '56px',
    padding: '16px 32px',
    fontSize: '18px',
  },
  icon: {
    minHeight: '48px',
    minWidth: '48px',
    padding: '12px',
    fontSize: '24px',
  },
};

const variantStyles: Record<string, React.CSSProperties> = {
  primary: {
    backgroundColor: 'var(--color-primary, #0066FF)',
    color: 'white',
    border: 'none',
  },
  secondary: {
    backgroundColor: 'var(--color-secondary, #6B7280)',
    color: 'white',
    border: 'none',
  },
  outline: {
    backgroundColor: 'transparent',
    color: 'var(--color-primary, #0066FF)',
    border: '2px solid currentColor',
  },
  ghost: {
    backgroundColor: 'transparent',
    color: 'inherit',
    border: 'none',
  },
  destructive: {
    backgroundColor: 'var(--color-destructive, #DC2626)',
    color: 'white',
    border: 'none',
  },
};

/**
 * TouchButton Component
 *
 * A touch-optimized button that meets Material Design 3's 48dp minimum target size.
 * Includes haptic feedback support for Android devices.
 *
 * @example
 * ```tsx
 * <TouchButton variant="primary" onClick={handleSubmit}>
 *   Submit
 * </TouchButton>
 *
 * <TouchButton variant="outline" size="icon" icon={<MenuIcon />} />
 * ```
 */
export const TouchButton = forwardRef<HTMLButtonElement, TouchButtonProps>(
  (
    {
      variant = 'primary',
      size = 'default',
      haptic = true,
      compact = false,
      loading = false,
      icon,
      iconPosition = 'left',
      className,
      style,
      children,
      onClick,
      disabled,
      ...props
    },
    ref
  ) => {
    const haptics = useHaptics();
    const prefersReducedMotion = useReducedMotion();

    const handleClick = (e: React.MouseEvent<HTMLButtonElement>) => {
      if (disabled || loading) return;

      if (haptic) {
        haptics.tap();
      }

      onClick?.(e);
    };

    const baseStyles: React.CSSProperties = {
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '8px',
      fontWeight: 600,
      borderRadius: '12px',
      cursor: disabled || loading ? 'not-allowed' : 'pointer',
      opacity: disabled ? 0.5 : 1,
      transition: prefersReducedMotion ? 'none' : 'all 150ms ease-out',
      WebkitTapHighlightColor: 'transparent',
      touchAction: 'manipulation',
      userSelect: 'none',
      ...sizeStyles[size],
      ...variantStyles[variant],
      ...(compact && { padding: '8px 16px' }),
      ...style,
    };

    const content = (
      <>
        {loading ? (
          <span
            style={{
              width: '20px',
              height: '20px',
              border: '2px solid currentColor',
              borderTopColor: 'transparent',
              borderRadius: '50%',
              animation: prefersReducedMotion ? 'none' : 'spin 0.8s linear infinite',
            }}
          />
        ) : icon && iconPosition === 'left' ? (
          icon
        ) : null}
        {children}
        {!loading && icon && iconPosition === 'right' ? icon : null}
      </>
    );

    return (
      <button
        ref={ref}
        className={className}
        style={baseStyles}
        onClick={handleClick}
        disabled={disabled || loading}
        {...props}
      >
        {content}
        <style>{`
          @keyframes spin {
            to { transform: rotate(360deg); }
          }
        `}</style>
      </button>
    );
  }
);

TouchButton.displayName = 'TouchButton';

export default TouchButton;
