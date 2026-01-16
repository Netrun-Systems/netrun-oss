/**
 * useHaptics Hook - Vibration API wrapper for tactile feedback
 *
 * Provides haptic feedback patterns for touch interactions.
 * Progressive enhancement - works on Android, gracefully degrades on iOS.
 *
 * @version 1.0.0
 */

import { useCallback, useMemo } from 'react';

export interface HapticPattern {
  /** Short crisp tick (success) */
  success: () => void;
  /** Double buzz (error) */
  error: () => void;
  /** Long acknowledgment (action start) */
  start: () => void;
  /** Light tap (selection) */
  tap: () => void;
  /** Custom pattern */
  custom: (pattern: number | number[]) => void;
}

export interface UseHapticsOptions {
  /** Disable haptics globally */
  disabled?: boolean;
}

/**
 * Hook for providing haptic feedback on touch interactions
 *
 * @example
 * ```tsx
 * const haptics = useHaptics();
 *
 * const handleSuccess = () => {
 *   saveData();
 *   haptics.success();
 * };
 *
 * const handleError = () => {
 *   haptics.error();
 * };
 * ```
 */
export function useHaptics(options: UseHapticsOptions = {}): HapticPattern {
  const { disabled = false } = options;

  const canVibrate = useMemo(() => {
    if (typeof navigator === 'undefined') return false;
    return 'vibrate' in navigator;
  }, []);

  const vibrate = useCallback(
    (pattern: number | number[]) => {
      if (disabled || !canVibrate) return;
      try {
        navigator.vibrate(pattern);
      } catch {
        // Silently fail if vibration not supported
      }
    },
    [disabled, canVibrate]
  );

  const success = useCallback(() => {
    vibrate(50); // Short crisp tick
  }, [vibrate]);

  const error = useCallback(() => {
    vibrate([50, 50, 50]); // Double buzz
  }, [vibrate]);

  const start = useCallback(() => {
    vibrate(200); // Long acknowledgment
  }, [vibrate]);

  const tap = useCallback(() => {
    vibrate(10); // Light tap
  }, [vibrate]);

  const custom = useCallback(
    (pattern: number | number[]) => {
      vibrate(pattern);
    },
    [vibrate]
  );

  return {
    success,
    error,
    start,
    tap,
    custom,
  };
}

export default useHaptics;
