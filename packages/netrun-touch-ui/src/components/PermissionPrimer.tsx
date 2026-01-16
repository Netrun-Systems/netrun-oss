/**
 * PermissionPrimer Component - Camera/Microphone permission flow
 *
 * Implements the "Double-Request" pattern for hardware permissions.
 * Shows a custom primer modal before triggering the native browser prompt.
 *
 * @version 1.0.0
 */

import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useReducedMotion } from '../hooks/useReducedMotion';
import { useHaptics } from '../hooks/useHaptics';

export type PermissionType = 'camera' | 'microphone' | 'camera-microphone';

export interface PermissionPrimerProps {
  /** Type of permission to request */
  type: PermissionType;
  /** Whether the modal is open */
  open: boolean;
  /** Callback when permission is granted */
  onGranted: (stream: MediaStream) => void;
  /** Callback when permission is denied or cancelled */
  onDenied: (reason: 'cancelled' | 'denied' | 'error') => void;
  /** Custom title */
  title?: string;
  /** Custom description */
  description?: string;
  /** Custom icon */
  icon?: React.ReactNode;
  /** Primary button text */
  allowText?: string;
  /** Secondary button text */
  cancelText?: string;
}

const defaultConfig: Record<PermissionType, { title: string; description: string; icon: string }> = {
  camera: {
    title: 'Camera Access',
    description: 'We need camera access to scan documents. Your photos are processed locally and never stored on our servers.',
    icon: '📷',
  },
  microphone: {
    title: 'Microphone Access',
    description: 'We need microphone access to record voice notes. Your recordings are processed locally.',
    icon: '🎤',
  },
  'camera-microphone': {
    title: 'Camera & Microphone Access',
    description: 'We need camera and microphone access for video recording. Your media is processed locally.',
    icon: '📹',
  },
};

const getConstraints = (type: PermissionType): MediaStreamConstraints => {
  switch (type) {
    case 'camera':
      return { video: true, audio: false };
    case 'microphone':
      return { video: false, audio: true };
    case 'camera-microphone':
      return { video: true, audio: true };
  }
};

/**
 * PermissionPrimer Component
 *
 * A custom modal that explains why permissions are needed before
 * triggering the native browser permission prompt.
 *
 * @example
 * ```tsx
 * const [showPrimer, setShowPrimer] = useState(false);
 * const [stream, setStream] = useState<MediaStream | null>(null);
 *
 * <button onClick={() => setShowPrimer(true)}>
 *   Scan Document
 * </button>
 *
 * <PermissionPrimer
 *   type="camera"
 *   open={showPrimer}
 *   onGranted={(stream) => {
 *     setStream(stream);
 *     setShowPrimer(false);
 *   }}
 *   onDenied={(reason) => {
 *     console.log('Permission denied:', reason);
 *     setShowPrimer(false);
 *   }}
 * />
 * ```
 */
export const PermissionPrimer: React.FC<PermissionPrimerProps> = ({
  type,
  open,
  onGranted,
  onDenied,
  title,
  description,
  icon,
  allowText = 'Allow Access',
  cancelText = 'Not Now',
}) => {
  const [isRequesting, setIsRequesting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const prefersReducedMotion = useReducedMotion();
  const haptics = useHaptics();

  const config = defaultConfig[type];

  const handleAllow = useCallback(async () => {
    setIsRequesting(true);
    setError(null);
    haptics.tap();

    try {
      const constraints = getConstraints(type);
      const stream = await navigator.mediaDevices.getUserMedia(constraints);
      haptics.success();
      onGranted(stream);
    } catch (err) {
      const error = err as Error;

      if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
        setError('Permission was denied. Please enable it in your browser settings.');
        haptics.error();
        onDenied('denied');
      } else if (error.name === 'NotFoundError' || error.name === 'DevicesNotFoundError') {
        setError('No camera/microphone found. Please connect a device and try again.');
        haptics.error();
        onDenied('error');
      } else {
        setError(`Failed to access ${type}: ${error.message}`);
        haptics.error();
        onDenied('error');
      }
    } finally {
      setIsRequesting(false);
    }
  }, [type, onGranted, onDenied, haptics]);

  const handleCancel = useCallback(() => {
    haptics.tap();
    onDenied('cancelled');
  }, [onDenied, haptics]);

  const transition = prefersReducedMotion
    ? { duration: 0 }
    : { type: 'spring', damping: 25, stiffness: 300 };

  const backdropStyles: React.CSSProperties = {
    position: 'fixed',
    inset: 0,
    zIndex: 50,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '24px',
  };

  const modalStyles: React.CSSProperties = {
    width: '100%',
    maxWidth: '400px',
    backgroundColor: 'var(--color-surface, #FFFFFF)',
    borderRadius: '24px',
    padding: '32px 24px',
    textAlign: 'center',
    boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
  };

  const iconStyles: React.CSSProperties = {
    fontSize: '48px',
    marginBottom: '16px',
  };

  const titleStyles: React.CSSProperties = {
    fontSize: '20px',
    fontWeight: 700,
    color: 'var(--color-text-primary, #111827)',
    marginBottom: '12px',
  };

  const descriptionStyles: React.CSSProperties = {
    fontSize: '14px',
    color: 'var(--color-text-secondary, #6B7280)',
    marginBottom: '24px',
    lineHeight: 1.6,
  };

  const errorStyles: React.CSSProperties = {
    fontSize: '13px',
    color: '#DC2626',
    backgroundColor: '#FEF2F2',
    padding: '12px',
    borderRadius: '8px',
    marginBottom: '16px',
  };

  const buttonContainerStyles: React.CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  };

  const primaryButtonStyles: React.CSSProperties = {
    minHeight: '48px',
    padding: '12px 24px',
    fontSize: '16px',
    fontWeight: 600,
    backgroundColor: 'var(--color-primary, #0066FF)',
    color: 'white',
    border: 'none',
    borderRadius: '12px',
    cursor: isRequesting ? 'not-allowed' : 'pointer',
    opacity: isRequesting ? 0.7 : 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
  };

  const secondaryButtonStyles: React.CSSProperties = {
    minHeight: '48px',
    padding: '12px 24px',
    fontSize: '16px',
    fontWeight: 500,
    backgroundColor: 'transparent',
    color: 'var(--color-text-secondary, #6B7280)',
    border: 'none',
    cursor: 'pointer',
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={transition}
          style={backdropStyles}
          onClick={(e) => {
            if (e.target === e.currentTarget) handleCancel();
          }}
        >
          <motion.div
            initial={{ scale: 0.9, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0.9, opacity: 0 }}
            transition={transition}
            style={modalStyles}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={iconStyles}>{icon || config.icon}</div>
            <h2 style={titleStyles}>{title || config.title}</h2>
            <p style={descriptionStyles}>{description || config.description}</p>

            {error && <div style={errorStyles}>{error}</div>}

            <div style={buttonContainerStyles}>
              <button
                onClick={handleAllow}
                disabled={isRequesting}
                style={primaryButtonStyles}
              >
                {isRequesting ? (
                  <>
                    <span
                      style={{
                        width: '20px',
                        height: '20px',
                        border: '2px solid white',
                        borderTopColor: 'transparent',
                        borderRadius: '50%',
                        animation: 'spin 0.8s linear infinite',
                      }}
                    />
                    Requesting...
                  </>
                ) : (
                  allowText
                )}
              </button>
              <button onClick={handleCancel} style={secondaryButtonStyles}>
                {cancelText}
              </button>
            </div>

            <style>{`
              @keyframes spin {
                to { transform: rotate(360deg); }
              }
            `}</style>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default PermissionPrimer;
