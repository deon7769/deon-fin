function greetingPrefix(hour: number): string {
  if (hour >= 5 && hour < 12) {
    return "Bom dia";
  }
  if (hour >= 12 && hour < 18) {
    return "Boa tarde";
  }
  return "Boa noite";
}

export function greetingForHour(hour: number, name?: string | null): string {
  const normalizedHour = Number.isFinite(hour) ? Math.max(0, Math.min(23, Math.floor(hour))) : 0;
  const prefix = greetingPrefix(normalizedHour);
  const displayName = (name ?? "").trim();
  return displayName ? `${prefix}, ${displayName}!` : `${prefix}!`;
}

export function greetingForDate(date = new Date(), name?: string | null): string {
  return greetingForHour(date.getHours(), name);
}
