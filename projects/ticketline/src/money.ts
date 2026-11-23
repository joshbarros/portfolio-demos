/** Money is stored and computed in integer cents. No floats in the domain. */
export type Cents = number;

export function assertCents(value: number): Cents {
  if (!Number.isInteger(value) || value < 0) throw new Error("amount must be a non-negative integer in cents");
  return value;
}

export function lineTotal(quantity: number, unitPriceCents: number): Cents {
  if (!Number.isInteger(quantity) || quantity < 1) throw new Error("quantity must be a positive integer");
  assertCents(unitPriceCents);
  return quantity * unitPriceCents;
}

export function invoiceTotal(items: { quantity: number; unit_price_cents: number }[]): Cents {
  return items.reduce((sum, item) => sum + lineTotal(item.quantity, item.unit_price_cents), 0);
}

/** Round-half-up to whole cents, used only at the boundary where rates are applied. */
export function roundCents(value: number): Cents {
  return Math.round(value);
}

export function formatMoney(cents: Cents, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(cents / 100);
}
