/**
 * TouchCard Component - Large touchable card for mobile interfaces
 *
 * Extracted from Intirkast's proven implementation.
 * Provides generous touch targets (56-88px) and clear visual feedback.
 *
 * @version 1.0.0
 */

import React, { forwardRef } from 'react';
import { useHaptics } from '../hooks/useHaptics';
import { useReducedMotion } from '../hooks/useReducedMotion';

export interface TouchCardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Icon element */
  icon?: React.ReactNode;
  /** Card title */
  title: string;
  /** Optional description text */
  description?: string;
  /** Optional badge text */
  badge?: string;
  /** Badge color variant */
  badgeVariant?: 'success' | 'warning' | 'error' | 'info' | 'default';
  /** Whether the card is selected/active */
  selected?: boolean;
  /** Whether the card is disabled */
  disabled?: boolean;
  /** Card visual variant */
  variant?: 'default' | 'outlined' | 'elevated' | 'glass';
  /** Right-side action element */
  action?: React.ReactNode;
  /** Size variant */
  size?: 'compact' | 'default' | 'large';
  /** Enable haptic feedback */
  haptic?: boolean;
}

const sizeStyles: Record<string, React.CSSProperties> = {
  compact: { minHeight: '56px', padding: '12px 16px' },
  default: { minHeight: '72px', padding: '16px 24px' },
  large: { minHeight: '88px', padding: '20px 24px' },
};

const badgeColors: Record<string, { bg: string; color: string }> = {
  success: { bg: '#10B981', color: 'white' },
  warning: { bg: '#F59E0B', color: 'white' },
  error: { bg: '#EF4444', color: 'white' },
  info: { bg: '#3B82F6', color: 'white' },
  default: { bg: '#E5E7EB', color: '#374151' },
};

/**
 * TouchCard Component
 *
 * A touch-friendly card component optimized for mobile interfaces.
 * Minimum touch target of 56px height ensures easy interaction.
 *
 * @example
 * ```tsx
 * <TouchCard
 *   icon={<UserIcon />}
 *   title="Profile Settings"
 *   description="Manage your account preferences"
 *   badge="New"
 *   badgeVariant="success"
 *   onClick={() => navigate('/settings')}
 * />
 * ```
 */
export const TouchCard = forwardRef<HTMLDivElement, TouchCardProps>(
  (
    {
      icon,
      title,
      description,
      badge,
      badgeVariant = 'default',
      onClick,
      selected = false,
      disabled = false,
      variant = 'default',
      action,
      size = 'default',
      haptic = true,
      className,
      style,
      ...props
    },
    ref
  ) => {
    const haptics = useHaptics();
    const prefersReducedMotion = useReducedMotion();
    const isClickable = !!onClick && !disabled;

    const handleClick = (e: React.MouseEvent<HTMLDivElement>) => {
      if (!isClickable) return;
      if (haptic) haptics.tap();
      onClick?.(e);
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (isClickable && (e.key === 'Enter' || e.key === ' ')) {
        e.preventDefault();
        onClick?.(e as unknown as React.MouseEvent<HTMLDivElement>);
      }
    };

    const getVariantStyles = (): React.CSSProperties => {
      const base: React.CSSProperties = {
        borderRadius: '12px',
        border: '1px solid',
      };

      switch (variant) {
        case 'outlined':
          return {
            ...base,
            backgroundColor: 'transparent',
            borderColor: selected ? 'var(--color-primary, #0066FF)' : '#D1D5DB',
            borderWidth: '2px',
          };
        case 'elevated':
          return {
            ...base,
            backgroundColor: 'var(--color-surface, #FFFFFF)',
            borderColor: '#E5E7EB',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.1)',
          };
        case 'glass':
          return {
            ...base,
            backgroundColor: 'rgba(255, 255, 255, 0.6)',
            borderColor: 'rgba(255, 255, 255, 0.2)',
            backdropFilter: 'blur(12px)',
            WebkitBackdropFilter: 'blur(12px)',
          };
        default:
          return {
            ...base,
            backgroundColor: selected
              ? 'var(--color-surface-selected, #F0F9FF)'
              : 'var(--color-surface, #F9FAFB)',
            borderColor: selected ? 'var(--color-primary, #0066FF)' : '#E5E7EB',
          };
      }
    };

    const baseStyles: React.CSSProperties = {
      display: 'flex',
      alignItems: 'center',
      gap: '16px',
      cursor: isClickable ? 'pointer' : 'default',
      opacity: disabled ? 0.5 : 1,
      transition: prefersReducedMotion ? 'none' : 'all 200ms ease-out',
      WebkitTapHighlightColor: 'transparent',
      touchAction: 'manipulation',
      ...sizeStyles[size],
      ...getVariantStyles(),
      ...style,
    };

    return (
      <div
        ref={ref}
        role={isClickable ? 'button' : undefined}
        tabIndex={isClickable ? 0 : undefined}
        aria-pressed={selected}
        aria-disabled={disabled}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        className={className}
        style={baseStyles}
        {...props}
      >
        {/* Icon */}
        {icon && (
          <div
            style={{
              flexShrink: 0,
              fontSize: size === 'large' ? '32px' : size === 'compact' ? '20px' : '24px',
              color: selected ? 'var(--color-primary, #0066FF)' : '#6B7280',
            }}
          >
            {icon}
          </div>
        )}

        {/* Content */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <span
              style={{
                fontWeight: 600,
                fontSize: size === 'large' ? '18px' : size === 'compact' ? '14px' : '16px',
                color: 'var(--color-text-primary, #111827)',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {title}
            </span>
            {badge && (
              <span
                style={{
                  fontSize: '12px',
                  fontWeight: 500,
                  padding: '2px 8px',
                  borderRadius: '9999px',
                  backgroundColor: badgeColors[badgeVariant].bg,
                  color: badgeColors[badgeVariant].color,
                }}
              >
                {badge}
              </span>
            )}
          </div>
          {description && (
            <p
              style={{
                fontSize: size === 'large' ? '14px' : '12px',
                color: 'var(--color-text-secondary, #6B7280)',
                margin: 0,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical',
              }}
            >
              {description}
            </p>
          )}
        </div>

        {/* Action */}
        {action && (
          <div style={{ flexShrink: 0, color: '#9CA3AF' }}>{action}</div>
        )}
      </div>
    );
  }
);

TouchCard.displayName = 'TouchCard';

export default TouchCard;
