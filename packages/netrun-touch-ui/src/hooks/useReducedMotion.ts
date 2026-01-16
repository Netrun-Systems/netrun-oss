/**
 * useReducedMotion Hook - prefers-reduced-motion detection
 *
 * Respects user preference for reduced motion.
 * Essential for accessibility - some users experience motion sickness.
 *
 * @version 1.0.0
 */

import { useState, useEffect } from 'react';

/**
 * Hook that returns whether the user prefers reduced motion
 *
 * @example
 * ```tsx
 * const prefersReducedMotion = useReducedMotion();
 *
 * const animation = prefersReducedMotion
 *   ? { duration: 0 }
 *   : { type: 'spring', stiffness: 300, damping: 30 };
 *
 * return (
 *   <motion.div animate={animation}>
 *     Animated content
 *   </motion.div>
 * );
 * ```
 */
export function useReducedMotion(): boolean {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(() => {
    if (typeof window === 'undefined') return false;
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    return mediaQuery.matches;
  });

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');

    const handleChange = (event: MediaQueryListEvent) => {
      setPrefersReducedMotion(event.matches);
    };

    // Modern browsers
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', handleChange);
      return () => mediaQuery.removeEventListener('change', handleChange);
    }

    // Legacy browsers
    mediaQuery.addListener(handleChange);
    return () => mediaQuery.removeListener(handleChange);
  }, []);

  return prefersReducedMotion;
}

export default useReducedMotion;
