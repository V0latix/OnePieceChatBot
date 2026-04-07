"use client";

interface SpoilerFilterProps {
  value: string;
  onChange: (next: string) => void;
}

const arcs = ["Aucun", "East Blue", "Alabasta", "Enies Lobby", "Marineford", "Dressrosa", "Wano"];

export default function SpoilerFilter({ value, onChange }: SpoilerFilterProps) {
  return (
    <label className="card fade-in flex flex-col gap-2 rounded-2xl p-4 text-sm text-[#d9caa8]">
      Filtre anti-spoiler
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="rounded-lg border border-gold/30 bg-[#0d1729] px-3 py-2 text-sm"
      >
        {arcs.map((arc) => (
          <option key={arc} value={arc}>
            {arc}
          </option>
        ))}
      </select>
    </label>
  );
}
