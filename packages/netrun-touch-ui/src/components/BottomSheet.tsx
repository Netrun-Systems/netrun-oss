/**
 * BottomSheet Component - Draggable bottom sheet with gestures
 *
 * A mobile-native bottom sheet component with drag-to-dismiss.
 * Requires Framer Motion for gesture handling.
 *
 * @version 1.0.0
 */

import React, { forwardRef, useCallback, useEffect, useRef } from 'react';
import { motion, AnimatePresence, PanInfo, useAnimation } from 'framer-motion';
import { useReducedMotion } from '../hooks/useReducedMotion';
import { useHaptics } from '../hooks/useHaptics';

export interface BottomSheetProps {
  /** Whether the sheet is open */
  open: boolean;
  /** Callback when sheet should close */
  onClose: () => void;
  /** Sheet content */
  children: React.ReactNode;
  /** Snap points as percentages of viewport height */
  snapPoints?: number[];
  /** Initial snap point index */
  initialSnap?: number;
  /** Show backdrop */
  backdrop?: boolean;
  /** Enable drag to dismiss */
  draggable?: boolean;
  /** Enable haptic feedback */
  haptic?: boolean;
  /** Additional class name */
  className?: string;
  /** Header content (appears above handle) */
  header?: React.ReactNode;
}

/**
 * BottomSheet Component
 *
 * A touch-native bottom sheet with drag gestures and snap points.
 * Respects safe area insets and reduced motion preferences.
 *
 * @example
 * ```tsx
 * const [isOpen, setIsOpen] = useState(false);
 *
 * <BottomSheet open={isOpen} onClose={() => setIsOpen(false)}>
 *   <h2>Menu</h2>
 *   <TouchCard title="Option 1" onClick={() => {}} />
 *   <TouchCard title="Option 2" onClick={() => {}} />
 * </BottomSheet>
 * ```
 */
export const BottomSheet = forwardRef<HTMLDivElement, BottomSheetProps>(
  (
    {
      open,
      onClose,
      children,
      snapPoints = [50, 90],
      initialSnap = 0,
      backdrop = true,
      draggable = true,
      haptic = true,
      className,
      header,
    },
    ref
  ) => {
    const prefersReducedMotion = useReducedMotion();
    const haptics = useHaptics();
    const controls = useAnimation();
    const sheetRef = useRef<HTMLDivElement>(null);

    const transition = prefersReducedMotion
      ? { duration: 0 }
      : { type: 'spring', damping: 30, stiffness: 300 };

    // Calculate snap positions in pixels
    const getSnapY = useCallback(
      (snapIndex: number) => {
        if (typeof window === 'undefined') return 0;
        const vh = window.innerHeight;
        const snapPercent = snapPoints[snapIndex] || snapPoints[0];
        return vh * (1 - snapPercent / 100);
      },
      [snapPoints]
    );

    // Animate to initial position when opened
    useEffect(() => {
      if (open) {
        controls.start({ y: getSnapY(initialSnap) });
      }
    }, [open, initialSnap, controls, getSnapY]);

    const handleDragEnd = useCallback(
      (_: MouseEvent | TouchEvent | PointerEvent, info: PanInfo) => {
        const { velocity, offset } = info;
        const threshold = 100;
        const velocityThreshold = 500;

        // Fast swipe down = close
        if (velocity.y > velocityThreshold || offset.y > threshold) {
          if (haptic) haptics.tap();
          onClose();
          return;
        }

        // Fast swipe up = snap to largest point
        if (velocity.y < -velocityThreshold) {
          if (haptic) haptics.tap();
          controls.start({ y: getSnapY(snapPoints.length - 1), transition });
          return;
        }

        // Find nearest snap point
        const currentY = getSnapY(initialSnap) + offset.y;
        let nearestSnap = 0;
        let minDistance = Infinity;

        snapPoints.forEach((_, index) => {
          const snapY = getSnapY(index);
          const distance = Math.abs(currentY - snapY);
          if (distance < minDistance) {
            minDistance = distance;
            nearestSnap = index;
          }
        });

        if (haptic) haptics.tap();
        controls.start({ y: getSnapY(nearestSnap), transition });
      },
      [haptic, haptics, onClose, controls, getSnapY, snapPoints, initialSnap, transition]
    );

    const sheetStyles: React.CSSProperties = {
      position: 'fixed',
      bottom: 0,
      left: 0,
      right: 0,
      zIndex: 50,
      maxHeight: '90vh',
      borderRadius: '24px 24px 0 0',
      backgroundColor: 'var(--color-surface, #FFFFFF)',
      boxShadow: '0 -8px 32px rgba(0, 0, 0, 0.15)',
      paddingBottom: 'var(--safe-area-bottom, 0px)',
      touchAction: draggable ? 'none' : 'auto',
    };

    const handleStyles: React.CSSProperties = {
      width: '36px',
      height: '4px',
      backgroundColor: 'rgba(128, 128, 128, 0.4)',
      borderRadius: '2px',
      margin: '8px auto 16px',
      cursor: draggable ? 'grab' : 'default',
    };

    const backdropStyles: React.CSSProperties = {
      position: 'fixed',
      inset: 0,
      zIndex: 40,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
    };

    return (
      <AnimatePresence>
        {open && (
          <>
            {/* Backdrop */}
            {backdrop && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={transition}
                style={backdropStyles}
                onClick={onClose}
              />
            )}

            {/* Sheet */}
            <motion.div
              ref={ref || sheetRef}
              initial={{ y: '100%' }}
              animate={controls}
              exit={{ y: '100%' }}
              transition={transition}
              drag={draggable ? 'y' : false}
              dragConstraints={{ top: 0 }}
              dragElastic={0.2}
              onDragEnd={handleDragEnd}
              style={sheetStyles}
              className={className}
            >
              {/* Handle */}
              <div style={handleStyles} />

              {/* Header */}
              {header && (
                <div style={{ padding: '0 24px 16px', borderBottom: '1px solid #E5E7EB' }}>
                  {header}
                </div>
              )}

              {/* Content */}
              <div
                style={{
                  padding: '0 24px 24px',
                  overflowY: 'auto',
                  maxHeight: 'calc(90vh - 60px - var(--safe-area-bottom, 0px))',
                }}
              >
                {children}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    );
  }
);

BottomSheet.displayName = 'BottomSheet';

export default BottomSheet;
