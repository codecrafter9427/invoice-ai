type ComingSoonProps = {
  title: string;
  description: string;
};

export function ComingSoon({ title, description }: ComingSoonProps) {
  return (
    <section className="rounded-lg border border-slate/15 bg-white/70 p-8 shadow-sm backdrop-blur">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-accent">
        Coming Soon
      </p>
      <h1 className="mt-2 font-display text-3xl text-ink">{title}</h1>
      <p className="mt-3 max-w-xl text-slate">{description}</p>
      <button
        type="button"
        disabled
        className="mt-6 cursor-not-allowed rounded-md bg-mist px-4 py-2 text-sm text-slate/70"
      >
        Not available in scaffold
      </button>
    </section>
  );
}
