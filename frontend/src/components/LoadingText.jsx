import { useEffect, useMemo, useState } from "react";

const DEFAULT_INTERVAL_MS = 450;
const DOT_STATES = ["", ".", "..", "..."];

export default function LoadingText({ label, intervalMs = DEFAULT_INTERVAL_MS }) {
  const [step, setStep] = useState(0);

  useEffect(() => {
    const timerId = window.setInterval(() => {
      setStep((currentStep) => (currentStep + 1) % DOT_STATES.length);
    }, intervalMs);

    return () => window.clearInterval(timerId);
  }, [intervalMs]);

  const animatedLabel = useMemo(() => {
    const dots = DOT_STATES[step];
    return `${label}${dots}`;
  }, [label, step]);

  return (
    <span
      className="loading-text"
      aria-live="polite"
      aria-label={`${label}...`}
      style={{ display: "inline-flex", minWidth: "max-content", whiteSpace: "nowrap" }}
    >
      {animatedLabel}
      <span
        className="loading-text-reserved-space"
        aria-hidden="true"
        style={{ opacity: 0 }}
      >
        {".".repeat(DOT_STATES[DOT_STATES.length - 1].length - DOT_STATES[step].length)}
      </span>
    </span>
  );
}
