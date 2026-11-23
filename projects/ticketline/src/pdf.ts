import PDFDocument from "pdfkit";
import { formatMoney } from "./money.js";

export type InvoiceSnapshot = {
  ticket: { id: string; number: number; notes: string; approved_by: string | null; approved_at: string | null };
  client: { name: string; address: string };
  items: { description: string; quantity: number; unit_price_cents: number }[];
  total_cents: number;
  currency: string;
  issued_at: string;
  disclaimer: string;
};

export function renderInvoicePdf(invoice: { number: number; snapshot: InvoiceSnapshot }): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    const doc = new PDFDocument({ size: "A4", margin: 50 });
    const chunks: Buffer[] = [];
    doc.on("data", (chunk: Buffer) => chunks.push(chunk));
    doc.on("end", () => resolve(Buffer.concat(chunks)));
    doc.on("error", reject);

    const snap = invoice.snapshot;
    doc.fontSize(20).text("Demo Electric Co.", { continued: false });
    doc.fontSize(9).fillColor("#666").text("Fictional company — personal demo project");
    doc.moveDown(1.5);
    doc.fillColor("#000").fontSize(16).text(`Invoice #${String(invoice.number).padStart(4, "0")}`);
    doc.fontSize(9).fillColor("#666").text(`Issued ${new Date(snap.issued_at).toISOString().slice(0, 10)}`);
    doc.moveDown();
    doc.fillColor("#000").fontSize(11).text("Bill to");
    doc.fontSize(10).text(snap.client.name);
    doc.text(snap.client.address);
    doc.moveDown();
    doc.fontSize(11).text(`Ticket #${snap.ticket.number}`);
    if (snap.ticket.notes) doc.fontSize(9).fillColor("#444").text(snap.ticket.notes);
    doc.moveDown();

    const top = doc.y;
    doc.fontSize(9).fillColor("#666").text("Description", 50, top);
    doc.text("Qty", 340, top, { width: 40, align: "right" });
    doc.text("Unit", 390, top, { width: 70, align: "right" });
    doc.text("Total", 470, top, { width: 75, align: "right" });
    doc.moveTo(50, top + 14).lineTo(545, top + 14).strokeColor("#ddd").stroke();
    let y = top + 22;
    for (const item of snap.items) {
      const line = item.quantity * item.unit_price_cents;
      doc.fillColor("#000").fontSize(10).text(item.description, 50, y, { width: 280 });
      doc.text(String(item.quantity), 340, y, { width: 40, align: "right" });
      doc.text(formatMoney(item.unit_price_cents, snap.currency), 390, y, { width: 70, align: "right" });
      doc.text(formatMoney(line, snap.currency), 470, y, { width: 75, align: "right" });
      y += 18;
    }
    doc.moveTo(50, y + 2).lineTo(545, y + 2).strokeColor("#ddd").stroke();
    doc.fontSize(12).text("Total", 390, y + 10, { width: 70, align: "right" });
    doc.text(formatMoney(snap.total_cents, snap.currency), 470, y + 10, { width: 75, align: "right" });

    doc.fontSize(8).fillColor("#999").text(snap.disclaimer, 50, 760, { width: 500, align: "center" });
    doc.end();
  });
}
