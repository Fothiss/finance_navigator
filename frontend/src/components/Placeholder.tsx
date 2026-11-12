type Props = {
  title: string;
  description: string;
};

export function Placeholder({ title, description }: Props) {
  return (
    <section className="rounded-lg border border-dashed border-line p-6">
      <h1 className="text-xl font-semibold">{title}</h1>
      <p className="mt-1 text-sm text-muted">{description}</p>
      <p className="mt-3 text-sm text-muted">Модуль появится в следующих изменениях.</p>
    </section>
  );
}
