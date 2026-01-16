/**
 * Netrun Touch UI - Touch-first component library
 *
 * Implements Modern Touch UI Standards for React applications.
 * - 48dp minimum touch targets (Material Design 3)
 * - Thumb zone optimized navigation
 * - Glassmorphism with performance fallbacks
 * - Framer Motion gesture support
 * - Safe area inset support
 *
 * @version 1.0.0
 * @author Netrun Systems
 */

// Components
export {
  TouchButton,
  type TouchButtonProps,
  TouchCard,
  type TouchCardProps,
  BentoGrid,
  BentoItem,
  type BentoGridProps,
  type BentoItemProps,
  GlassPanel,
  type GlassPanelProps,
  BottomNav,
  type BottomNavProps,
  type NavItem,
  BottomSheet,
  type BottomSheetProps,
  PermissionPrimer,
  type PermissionPrimerProps,
  type PermissionType,
} from './components';

// Hooks
export {
  useHaptics,
  type HapticPattern,
  type UseHapticsOptions,
  useSafeArea,
  useHasNotch,
  type SafeAreaInsets,
  type UseSafeAreaOptions,
  useReducedMotion,
} from './hooks';

// Design tokens and constants
export const TOUCH_STANDARDS = {
  /** Minimum touch target size (Material Design 3) */
  TARGET_MIN: 48,
  /** Comfortable touch target size */
  TARGET_COMFORTABLE: 56,
  /** Large touch target size */
  TARGET_LARGE: 64,
  /** Minimum spacing between targets */
  SPACING_MIN: 8,
  /** Mobile nav height */
  NAV_HEIGHT_MOBILE: 60,
  /** Tablet nav height */
  NAV_HEIGHT_TABLET: 72,
  /** List item minimum height (target + spacing) */
  LIST_ITEM_MIN: 56,
} as const;
