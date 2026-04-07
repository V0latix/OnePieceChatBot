export default function LoadingIndicator({ label = "Chargement..." }: { label?: string }) {
  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-gold/30 bg-[#102036] px-3 py-1 text-xs text-gold">
      <span className="h-2 w-2 animate-pulse rounded-full bg-gold" />
      <span>{label}</span>
    </div>
  );
}
