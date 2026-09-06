const SESSION_TIMEZONE = "Asia/Kolkata";

function parseApiDate(value: string) {
  return new Date(/[zZ]|[+-]\d{2}:?\d{2}$/.test(value) ? value : `${value}Z`);
}

function formatDateTime(value: string) {
  const date = parseApiDate(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-IN", {
    timeZone: SESSION_TIMEZONE,
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date);
}

export function formatSessionTime(start: string, end: string, status?: string) {
  const endDate = parseApiDate(end);
  if (status === "IN_PROGRESS" && endDate.getTime() < Date.now()) {
    return `Scheduled end: ${formatDateTime(end)}`;
  }
  return `${formatDateTime(start)} - ${formatDateTime(end)}`;
}

export function parseSessionDate(value: string) {
  return parseApiDate(value);
}
