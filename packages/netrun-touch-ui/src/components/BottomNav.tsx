/**
 * BottomNav Component - Thumb zone optimized navigation
 *
 * Fixed bottom navigation bar for mobile interfaces.
 * Implements Material Design's 48dp touch targets in the thumb zone.
 *
 * @version 1.0.0
 */

import React, { forwardRef } from 'react';
import { useHaptics } from '../hooks/useHaptics';
import { useReducedMotion } from '../hooks/useReducedMotion';

export interface NavItem {
  /** Unique key for the item */
  key: string;
  /** Icon element */
  icon: React.ReactNode;
  /** Active icon (optional, different icon when selected) */
  activeIcon?: React.ReactNode;
  /** Label text */
  label: string;
  /** Navigation path or action */
  path?: string;
  /** Badge count */
  badge?: number;
}

export interface BottomNavProps extends Omit<React.HTMLAttributes<HTMLElement>, 'onChange'> {
  /** Navigation items (3-5 recommended) */
  items: NavItem[];
  /** Currently active item key */
  activeKey: string;
  /** Callback when item is selected */
  onChange: (key: string, path?: string) => void;
  /** Enable haptic feedback */
  haptic?: boolean;
  /** Visual variant */
  variant?: 'default' | 'glass' | 'elevated';
  /** Show labels */
  showLabels?: boolean;
}

/**
 * BottomNav Component
 *
 * A touch-optimized bottom navigation bar that sits in the thumb zone.
 * Hidden on desktop (lg breakpoint and above).
 *
 * @example
 * ```tsx
 * const [activeTab, setActiveTab] = useState('home');
 *
 * <BottomNav
 *   items={[
 *     { key: 'home', icon: <HomeIcon />, label: 'Home', path: '/' },
 *     { key: 'search', icon: <SearchIcon />, label: 'Search', path: '/search' },
 *     { key: 'profile', icon: <UserIcon />, label: 'Profile', path: '/profile' },
 *   ]}
 *   activeKey={activeTab}
 *   onChange={(key, path) => {
 *     setActiveTab(key);
 *     navigate(path);
 *   }}
 * />
 * ```
 */
export const BottomNav = forwardRef<HTMLElement, BottomNavProps>(
  (
    {
      items,
      activeKey,
      onChange,
      haptic = true,
      variant = 'default',
      showLabels = true,
      className,
      style,
      ...props
    },
    ref
  ) => {
    const haptics = useHaptics();
    const prefersReducedMotion = useReducedMotion();

    const handleItemClick = (item: NavItem) => {
      if (item.key === activeKey) return;
      if (haptic) haptics.tap();
      onChange(item.key, item.path);
    };

    const getVariantStyles = (): React.CSSProperties => {
      switch (variant) {
        case 'glass':
          return {
            backgroundColor: 'rgba(255, 255, 255, 0.8)',
            backdropFilter: 'blur(12px) saturate(180%)',
            WebkitBackdropFilter: 'blur(12px) saturate(180%)',
            borderTop: '1px solid rgba(255, 255, 255, 0.2)',
          };
        case 'elevated':
          return {
            backgroundColor: 'var(--color-surface, #FFFFFF)',
            boxShadow: '0 -4px 20px rgba(0, 0, 0, 0.1)',
            borderTop: 'none',
          };
        default:
          return {
            backgroundColor: 'var(--color-surface, #FFFFFF)',
            borderTop: '1px solid #E5E7EB',
          };
      }
    };

    const navStyles: React.CSSProperties = {
      position: 'fixed',
      bottom: 0,
      left: 0,
      right: 0,
      zIndex: 50,
      paddingBottom: 'var(--safe-area-bottom, 0px)',
      ...getVariantStyles(),
      ...style,
    };

    const containerStyles: React.CSSProperties = {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-around',
      height: '60px',
      padding: '0 8px',
    };

    return (
      <nav ref={ref} className={className} style={navStyles} {...props}>
        <div style={containerStyles}>
          {items.map((item) => {
            const isActive = item.key === activeKey;

            const buttonStyles: React.CSSProperties = {
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              minWidth: '64px',
              height: '56px',
              padding: '8px 12px',
              gap: '4px',
              border: 'none',
              background: 'transparent',
              cursor: 'pointer',
              borderRadius: '12px',
              transition: prefersReducedMotion ? 'none' : 'all 200ms ease-out',
              color: isActive ? 'var(--color-primary, #0066FF)' : '#6B7280',
              WebkitTapHighlightColor: 'transparent',
              touchAction: 'manipulation',
            };

            const iconStyles: React.CSSProperties = {
              fontSize: '24px',
              transition: prefersReducedMotion ? 'none' : 'transform 200ms ease-out',
              transform: isActive ? 'scale(1.1)' : 'scale(1)',
            };

            const labelStyles: React.CSSProperties = {
              fontSize: '12px',
              fontWeight: isActive ? 600 : 500,
            };

            const badgeStyles: React.CSSProperties = {
              position: 'absolute',
              top: '4px',
              right: '4px',
              minWidth: '18px',
              height: '18px',
              padding: '0 4px',
              fontSize: '11px',
              fontWeight: 600,
              backgroundColor: '#EF4444',
              color: 'white',
              borderRadius: '9px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            };

            return (
              <button
                key={item.key}
                onClick={() => handleItemClick(item)}
                style={buttonStyles}
                aria-label={item.label}
                aria-current={isActive ? 'page' : undefined}
              >
                <span style={{ position: 'relative', ...iconStyles }}>
                  {isActive && item.activeIcon ? item.activeIcon : item.icon}
                  {item.badge !== undefined && item.badge > 0 && (
                    <span style={badgeStyles}>
                      {item.badge > 99 ? '99+' : item.badge}
                    </span>
                  )}
                </span>
                {showLabels && <span style={labelStyles}>{item.label}</span>}
              </button>
            );
          })}
        </div>
      </nav>
    );
  }
);

BottomNav.displayName = 'BottomNav';

export default BottomNav;
