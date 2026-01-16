/**
 * BentoGrid Component - Modular grid layout system
 *
 * Implements the Bento Box layout pattern for information-dense
 * touch interfaces. Provides predictable, rectangular hit targets.
 *
 * @version 1.0.0
 */

import React, { forwardRef } from 'react';

export interface BentoGridProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Number of columns at different breakpoints */
  columns?: {
    mobile?: number;
    tablet?: number;
    desktop?: number;
  };
  /** Gap between items in pixels */
  gap?: number;
  /** Base row height in pixels */
  rowHeight?: number;
  /** Include safe area padding */
  safeArea?: boolean;
}

export interface BentoItemProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Column span (1-4) */
  colSpan?: 1 | 2 | 3 | 4;
  /** Row span (1-4) */
  rowSpan?: 1 | 2 | 3 | 4;
  /** Make item span full row */
  fullWidth?: boolean;
}

/**
 * BentoGrid Component
 *
 * A CSS Grid-based layout system optimized for touch interfaces.
 * Automatically adjusts columns based on viewport width.
 *
 * @example
 * ```tsx
 * <BentoGrid columns={{ mobile: 1, tablet: 2, desktop: 4 }}>
 *   <BentoItem colSpan={2} rowSpan={2}>
 *     <LargeWidget />
 *   </BentoItem>
 *   <BentoItem>
 *     <SmallWidget />
 *   </BentoItem>
 *   <BentoItem>
 *     <SmallWidget />
 *   </BentoItem>
 * </BentoGrid>
 * ```
 */
export const BentoGrid = forwardRef<HTMLDivElement, BentoGridProps>(
  (
    {
      columns = { mobile: 1, tablet: 2, desktop: 4 },
      gap = 16,
      rowHeight = 150,
      safeArea = true,
      className,
      style,
      children,
      ...props
    },
    ref
  ) => {
    const gridStyles: React.CSSProperties = {
      display: 'grid',
      gridTemplateColumns: `repeat(${columns.mobile || 1}, 1fr)`,
      gridAutoRows: `${rowHeight}px`,
      gap: `${gap}px`,
      ...(safeArea && {
        padding: `var(--safe-area-top, 0px) var(--safe-area-right, 16px) var(--safe-area-bottom, 0px) var(--safe-area-left, 16px)`,
      }),
      ...style,
    };

    // Generate responsive CSS
    const responsiveId = React.useId();
    const responsiveStyles = `
      @media (min-width: 640px) {
        [data-bento-id="${responsiveId}"] {
          grid-template-columns: repeat(${columns.tablet || 2}, 1fr);
        }
      }
      @media (min-width: 1024px) {
        [data-bento-id="${responsiveId}"] {
          grid-template-columns: repeat(${columns.desktop || 4}, 1fr);
        }
      }
    `;

    return (
      <>
        <style>{responsiveStyles}</style>
        <div
          ref={ref}
          data-bento-id={responsiveId}
          className={className}
          style={gridStyles}
          {...props}
        >
          {children}
        </div>
      </>
    );
  }
);

BentoGrid.displayName = 'BentoGrid';

/**
 * BentoItem Component
 *
 * A grid item that can span multiple columns and rows.
 * Use within BentoGrid for responsive bento layouts.
 *
 * @example
 * ```tsx
 * <BentoItem colSpan={2} rowSpan={2}>
 *   <img src="/hero.jpg" alt="Hero" />
 * </BentoItem>
 * ```
 */
export const BentoItem = forwardRef<HTMLDivElement, BentoItemProps>(
  (
    {
      colSpan = 1,
      rowSpan = 1,
      fullWidth = false,
      className,
      style,
      children,
      ...props
    },
    ref
  ) => {
    const itemStyles: React.CSSProperties = {
      gridColumn: fullWidth ? '1 / -1' : `span ${colSpan}`,
      gridRow: `span ${rowSpan}`,
      borderRadius: '16px',
      overflow: 'hidden',
      minHeight: 0,
      ...style,
    };

    return (
      <div ref={ref} className={className} style={itemStyles} {...props}>
        {children}
      </div>
    );
  }
);

BentoItem.displayName = 'BentoItem';

export default BentoGrid;
