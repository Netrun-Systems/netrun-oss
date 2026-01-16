/**
 * useSafeArea Hook - Safe area inset detection
 *
 * Provides reactive values for device safe area insets.
 * Useful for positioning elements that need to avoid notches, home indicators, etc.
 *
 * @version 1.0.0
 */

import { useState, useEffect, useMemo } from 'react';

export interface SafeAreaInsets {
  top: number;
  bottom: number;
  left: number;
  right: number;
}

export interface UseSafeAreaOptions {
  /** Update on resize/orientation change */
  watchChanges?: boolean;
}

/**
 * Parses a CSS env() value to a number
 */
function parseInset(value: string): number {
  const parsed = parseInt(value, 10);
  return isNaN(parsed) ? 0 : parsed;
}

/**
 * Gets safe area insets from CSS environment variables
 */
function getSafeAreaInsets(): SafeAreaInsets {
  if (typeof window === 'undefined' || typeof document === 'undefined') {
    return { top: 0, bottom: 0, left: 0, right: 0 };
  }

  const style = getComputedStyle(document.documentElement);

  return {
    top: parseInset(style.getPropertyValue('--safe-area-top') || '0'),
    bottom: parseInset(style.getPropertyValue('--safe-area-bottom') || '0'),
    left: parseInset(style.getPropertyValue('--safe-area-left') || '0'),
    right: parseInset(style.getPropertyValue('--safe-area-right') || '0'),
  };
}

/**
 * Hook for accessing device safe area insets
 *
 * @example
 * ```tsx
 * const safeArea = useSafeArea();
 *
 * return (
 *   <div style={{ paddingBottom: safeArea.bottom }}>
 *     Content safe from home indicator
 *   </div>
 * );
 * ```
 */
export function useSafeArea(options: UseSafeAreaOptions = {}): SafeAreaInsets {
  const { watchChanges = true } = options;

  const [insets, setInsets] = useState<SafeAreaInsets>(() => getSafeAreaInsets());

  useEffect(() => {
    if (!watchChanges) return;

    const updateInsets = () => {
      setInsets(getSafeAreaInsets());
    };

    // Update on resize and orientation change
    window.addEventListener('resize', updateInsets);
    window.addEventListener('orientationchange', updateInsets);

    // Initial update
    updateInsets();

    return () => {
      window.removeEventListener('resize', updateInsets);
      window.removeEventListener('orientationchange', updateInsets);
    };
  }, [watchChanges]);

  return insets;
}

/**
 * Hook that returns whether the device has significant safe area insets (notch)
 */
export function useHasNotch(): boolean {
  const insets = useSafeArea();
  return useMemo(() => insets.top > 20 || insets.bottom > 20, [insets]);
}

export default useSafeArea;
