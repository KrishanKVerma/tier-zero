import { type Tier } from "@/lib/api";

type TierMeta = {
  label: string;
  badgeClass: string;
  scoreClass: string;
  description: string;
};

export const TIER_META: Record<Tier, TierMeta> = {
  "tier-zero": {
    label: "TIER-ZERO",
    badgeClass: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
    scoreClass: "text-emerald-300",
    description: "Staff / principal signal. Production-grade impact.",
  },
  strong: {
    label: "STRONG",
    badgeClass: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
    scoreClass: "text-emerald-400",
    description: "Senior signal. Real depth, real shipping.",
  },
  mid: {
    label: "MID",
    badgeClass: "bg-amber-500/10 text-amber-300 border-amber-500/30",
    scoreClass: "text-amber-300",
    description: "Competent junior or mid. Some real work present.",
  },
  weak: {
    label: "WEAK",
    badgeClass: "bg-orange-500/10 text-orange-300 border-orange-500/30",
    scoreClass: "text-orange-300",
    description: "Thin profile. Insufficient evidence for senior judgment.",
  },
  "red-flag": {
    label: "RED-FLAG",
    badgeClass: "bg-rose-500/10 text-rose-300 border-rose-500/30",
    scoreClass: "text-rose-300",
    description: "Bio claims unsupported, or active signs of gaming.",
  },
};

export function impactColor(impact: "high" | "medium" | "low"): string {
  switch (impact) {
    case "high":
      return "text-emerald-400";
    case "medium":
      return "text-amber-300";
    case "low":
      return "text-zinc-400";
  }
}