# @netrun/touch-ui

Touch-first UI component library implementing Modern Touch UI Standards for React applications.

## Features

- **48dp Minimum Touch Targets** - Material Design 3 compliant touch targets
- **Thumb Zone Navigation** - Bottom navigation optimized for one-handed use
- **Glassmorphism** - Modern glass effects with `@supports` fallbacks for older browsers
- **Framer Motion Gestures** - Swipe, drag, and tap interactions
- **Safe Area Support** - Full support for notched devices (iPhone, Android gesture nav)
- **Haptic Feedback** - Vibration API integration for tactile responses
- **Reduced Motion** - Respects `prefers-reduced-motion` accessibility setting

## Installation

```bash
npm install @netrun/touch-ui framer-motion
# or
pnpm add @netrun/touch-ui framer-motion
# or
yarn add @netrun/touch-ui framer-motion
```

## Peer Dependencies

- `react` ^18.0.0 || ^19.0.0
- `react-dom` ^18.0.0 || ^19.0.0
- `framer-motion` ^10.0.0 || ^11.0.0

## Quick Start

```tsx
import {
  TouchButton,
  TouchCard,
  BottomNav,
  BentoGrid,
  BentoItem,
  useHaptics,
  useSafeArea,
} from '@netrun/touch-ui';
import '@netrun/touch-ui/styles';

function App() {
  const { trigger } = useHaptics();
  const { bottom } = useSafeArea();

  return (
    <div style={{ paddingBottom: bottom }}>
      <BentoGrid columns={2} gap={16}>
        <BentoItem colSpan={2} variant="glass">
          <h1>Welcome</h1>
        </BentoItem>
        <BentoItem>
          <TouchCard
            onTap={() => trigger('light')}
            swipeable
          >
            Card Content
          </TouchCard>
        </BentoItem>
      </BentoGrid>

      <BottomNav
        items={[
          { icon: HomeIcon, label: 'Home', path: '/' },
          { icon: SearchIcon, label: 'Search', path: '/search' },
        ]}
        haptic
      />
    </div>
  );
}
```

## Components

### TouchButton

Touch-optimized button with 48dp minimum target size.

```tsx
<TouchButton
  size="default"     // 'sm' | 'default' | 'lg' | 'icon'
  variant="primary"  // 'primary' | 'secondary' | 'ghost'
  haptic             // Enable haptic feedback
  onClick={() => {}}
>
  Click Me
</TouchButton>
```

### TouchCard

Interactive card with gesture support.

```tsx
<TouchCard
  onTap={() => {}}
  onLongPress={() => {}}
  onSwipeLeft={() => {}}
  onSwipeRight={() => {}}
  swipeable
  pressable
  variant="elevated"  // 'default' | 'elevated' | 'glass'
>
  Card content
</TouchCard>
```

### BentoGrid / BentoItem

Responsive grid layout system.

```tsx
<BentoGrid
  columns={4}        // Base columns (responsive)
  gap={16}           // Gap in pixels
  safeArea           // Apply safe area padding
>
  <BentoItem colSpan={2} rowSpan={2} variant="glass">
    Featured content
  </BentoItem>
  <BentoItem>Regular item</BentoItem>
</BentoGrid>
```

### GlassPanel

Glassmorphism container with automatic fallbacks.

```tsx
<GlassPanel
  blur={12}           // Blur amount in pixels
  opacity={0.8}       // Background opacity
  dark                // Dark variant
>
  Content with glass effect
</GlassPanel>
```

### BottomNav

Thumb-zone optimized navigation bar.

```tsx
<BottomNav
  items={[
    { icon: HomeIcon, label: 'Home', path: '/' },
    { icon: ProfileIcon, label: 'Profile', path: '/profile' },
  ]}
  haptic              // Enable haptic feedback
  glass               // Glass effect background
/>
```

### BottomSheet

Draggable bottom sheet with snap points.

```tsx
<BottomSheet
  isOpen={isOpen}
  onClose={() => setIsOpen(false)}
  snapPoints={[0.5, 0.9]}  // 50% and 90% of screen
  initialSnap={0}
>
  Sheet content
</BottomSheet>
```

### PermissionPrimer

Permission request priming modal.

```tsx
<PermissionPrimer
  permission="camera"   // 'camera' | 'microphone' | 'location' | 'notifications'
  onAllow={() => requestPermission()}
  onDeny={() => setShowPrimer(false)}
  title="Enable Camera"
  description="We need camera access to scan documents"
/>
```

## Hooks

### useHaptics

Trigger haptic feedback patterns.

```tsx
const { trigger, isSupported } = useHaptics();

// Patterns: 'light' | 'medium' | 'heavy' | 'success' | 'warning' | 'error'
trigger('success');

// Custom pattern (vibration durations in ms)
trigger([10, 50, 10]);
```

### useSafeArea

Get safe area insets for notched devices.

```tsx
const { top, bottom, left, right, hasNotch } = useSafeArea();

return (
  <div style={{ paddingTop: top, paddingBottom: bottom }}>
    Content
  </div>
);
```

### useReducedMotion

Respect user's motion preferences.

```tsx
const prefersReducedMotion = useReducedMotion();

return (
  <motion.div
    animate={{ x: 100 }}
    transition={{ duration: prefersReducedMotion ? 0 : 0.3 }}
  />
);
```

## CSS Utilities

Import the stylesheet for utility classes:

```tsx
import '@netrun/touch-ui/styles';
```

Available classes:

```css
/* Safe area padding */
.pt-safe    /* padding-top: env(safe-area-inset-top) */
.pb-safe    /* padding-bottom: env(safe-area-inset-bottom) */
.pl-safe    /* padding-left: env(safe-area-inset-left) */
.pr-safe    /* padding-right: env(safe-area-inset-right) */

/* Touch targets */
.touch-target     /* min-width/height: 48px */
.touch-target-lg  /* min-width/height: 56px */

/* Glassmorphism */
.glass-panel      /* Light glass effect */
.glass-panel-dark /* Dark glass effect */

/* Touch feedback */
.touch-active     /* Scale + opacity on :active */
```

## Design Tokens

Access design constants programmatically:

```tsx
import { TOUCH_STANDARDS } from '@netrun/touch-ui';

TOUCH_STANDARDS.TARGET_MIN        // 48 (pixels)
TOUCH_STANDARDS.TARGET_COMFORTABLE // 56
TOUCH_STANDARDS.TARGET_LARGE      // 64
TOUCH_STANDARDS.SPACING_MIN       // 8
TOUCH_STANDARDS.NAV_HEIGHT_MOBILE // 60
TOUCH_STANDARDS.LIST_ITEM_MIN     // 56
```

## Browser Support

- Chrome/Edge 88+
- Safari 15.4+
- Firefox 103+

Glassmorphism effects gracefully degrade on older browsers via `@supports` queries.

## Accessibility

- All touch targets meet WCAG 2.5.5 (44px) and 2.5.8 (24px) requirements
- `prefers-reduced-motion` is respected throughout
- Focus management for modals and sheets
- Screen reader announcements for state changes

## License

MIT - Netrun Systems

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) in the root of the netrun-oss repository.
