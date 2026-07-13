export default function LoadingIndicator({ label = "Chargement..." }: { label?: string }) {
  return (
    <div className="inline-flex items-center gap-2 border border-foreground bg-card px-3 py-1 text-xs uppercase tracking-wide">
      <span className="h-2 w-2 animate-pulse bg-primary" />
      <span>{label}</span>
    </div>
  );
}
