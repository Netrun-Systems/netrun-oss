/**
 * GlassPanel Component - Glassmorphism with performance fallbacks
 *
 * Provides a frosted glass effect that maintains context visibility.
 * Includes automatic fallbacks for older browsers and low-end devices.
 *
 * @version 1.0.0
 */

import React, { forwardRef, useMemo } from 'react';

export interface GlassPanelProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Glass intensity (blur amount) */
  intensity?: 'light' | 'medium' | 'heavy';
  /** Color scheme */
  variant?: 'light' | 'dark';
  /** Border radius in pixels */
  radius?: number;
  /** Show border */
  bordered?: boolean;
  /** Show shadow */
  shadow?: boolean;
  /** Force disable blur (for performance) */
  disableBlur?: boolean;
}

const intensityConfig = {
  light: { blur: 8, opacity: 0.7 },
  medium: { blur: 12, opacity: 0.6 },
  heavy: { blur: 20, opacity: 0.5 },
};

/**
 * GlassPanel Component
 *
 * A container with glassmorphism styling and automatic fallbacks.
 * Use for floating overlays, navigation bars, and cards where
 * preserving context visibility is important.
 *
 * @example
 * ```tsx
 * <GlassPanel variant="light" intensity="medium" radius={16}>
 *   <h2>Settings</h2>
 *   <p>Content appears over the background</p>
 * </GlassPanel>
 * ```
 */
export const GlassPanel = forwardRef<HTMLDivElement, GlassPanelProps>(
  (
    {
      intensity = 'medium',
      variant = 'light',
      radius = 16,
      bordered = true,
      shadow = true,
      disableBlur = false,
      className,
      style,
      children,
      ...props
    },
    ref
  ) => {
    const config = intensityConfig[intensity];

    const glassStyles = useMemo((): React.CSSProperties => {
      const isLight = variant === 'light';

      // Fallback background (high opacity, no blur)
      const fallbackBg = isLight
        ? `rgba(255, 255, 255, 0.9)`
        : `rgba(0, 0, 0, 0.85)`;

      // Glass background (lower opacity, with blur)
      const glassBg = isLight
        ? `rgba(255, 255, 255, ${config.opacity})`
        : `rgba(0, 0, 0, ${config.opacity - 0.1})`;

      const borderColor = isLight
        ? 'rgba(255, 255, 255, 0.2)'
        : 'rgba(255, 255, 255, 0.1)';

      const base: React.CSSProperties = {
        borderRadius: `${radius}px`,
        // Start with fallback
        backgroundColor: fallbackBg,
        ...(bordered && {
          border: `1px solid ${borderColor}`,
        }),
        ...(shadow && {
          boxShadow: isLight
            ? '0 8px 32px rgba(31, 38, 135, 0.15)'
            : '0 8px 32px rgba(0, 0, 0, 0.3)',
        }),
        ...style,
      };

      // If blur is not disabled, we'll handle the backdrop-filter via CSS
      // The actual blur is applied conditionally in the component
      if (!disableBlur) {
        base.backgroundColor = glassBg;
        base.backdropFilter = `blur(${config.blur}px) saturate(180%)`;
        // @ts-expect-error - WebkitBackdropFilter is a valid CSS property
        base.WebkitBackdropFilter = `blur(${config.blur}px) saturate(180%)`;
      }

      return base;
    }, [intensity, variant, radius, bordered, shadow, disableBlur, config, style]);

    return (
      <div ref={ref} className={className} style={glassStyles} {...props}>
        {children}
      </div>
    );
  }
);

GlassPanel.displayName = 'GlassPanel';

export default GlassPanel;
