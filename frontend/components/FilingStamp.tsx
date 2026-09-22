/** Sello de radicado: tipografía monoespaciada sobre pergamino, tinta bronce. */
export function FilingStamp({ value, size = "md", plain = false }: { value: string; size?: "md" | "lg"; plain?: boolean }) {
  return (
    <span className={`stamp${size === "lg" ? " stamp-lg" : ""}${plain ? " stamp-plain" : ""}`} title="Número de radicado único">
      {value}
    </span>
  );
}
