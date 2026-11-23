export const TICKET_STATUSES = ["draft", "submitted", "approved", "rejected", "invoiced"] as const;
export type TicketStatus = (typeof TICKET_STATUSES)[number];

export type Role = "technician" | "reviewer";

const TRANSITIONS: Record<TicketStatus, TicketStatus[]> = {
  draft: ["submitted"],
  submitted: ["approved", "rejected"],
  rejected: ["draft", "submitted"],
  approved: ["invoiced"],
  invoiced: []
};

export function canTransition(from: TicketStatus, to: TicketStatus): boolean {
  return TRANSITIONS[from]?.includes(to) ?? false;
}

export function assertTransition(from: TicketStatus, to: TicketStatus): void {
  if (!canTransition(from, to)) {
    throw Object.assign(new Error(`invalid transition ${from} -> ${to}`), { statusCode: 409 });
  }
}

export function canCreate(role: Role): boolean {
  return role === "technician" || role === "reviewer";
}

export function canReview(role: Role): boolean {
  return role === "reviewer";
}

export function canEditTicket(role: Role, actorId: string, ticket: { status: TicketStatus; technician_id: string }): boolean {
  if (ticket.status !== "draft" && ticket.status !== "rejected") return false;
  if (role === "reviewer") return true;
  return ticket.technician_id === actorId;
}
