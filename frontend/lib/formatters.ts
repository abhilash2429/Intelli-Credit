export function formatRatio(value: number | null | undefined, decimals = 2, suffix = 'x'): string {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return 'Not Available';
  }
  return `${Number(Number(value).toFixed(decimals))}${suffix}`;
}

export function formatCurrencyCr(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return 'Not Available';
  }
  return `₹${Number(value).toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })} Cr`;
}

export function formatPercentage(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return 'Not Available';
  }
  return `${Number(Number(value).toFixed(1))}%`;
}
