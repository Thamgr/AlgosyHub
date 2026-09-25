import { useEffect, useState } from "react";
import type { Contest } from "../api/types";
import { contestTimer, formatCountdown } from "../lib/contestTimer";

export default function ContestTimer({ contest }: { contest: Contest }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);
  const timer = contestTimer(contest, now);
  return (
    <span role="timer" aria-live="off" aria-label={timer.label}
      className="shrink-0 whitespace-nowrap font-mono text-xl tabular-nums font-semibold text-gray-800">
      {timer.milliseconds === null ? "—" : formatCountdown(timer.milliseconds)}
    </span>
  );
}
