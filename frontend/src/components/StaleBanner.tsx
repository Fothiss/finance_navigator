type Props = {
  stale: boolean;
  sources: { name: string; last_date: string | null; stale: boolean }[];
};

export function StaleBanner({ stale, sources }: Props) {
  if (!stale) {
    return null;
  }
  const staleSources = sources.filter((source) => source.stale);
  return (
    <div className="rounded-lg border border-amber-300 bg-amber-50 p-3 text-sm text-amber-800" role="status">
      <p className="font-medium">Данные устарели — вердикт не выдаётся.</p>
      <ul className="mt-1 list-inside list-disc">
        {staleSources.map((source) => (
          <li key={source.name}>
            {source.name}: последняя дата {source.last_date ?? "нет данных"}
          </li>
        ))}
      </ul>
    </div>
  );
}
