const fs = require("fs");
const path = require("path");
const { Document, Packer, Paragraph, TextRun, HeadingLevel, BorderStyle } = require("docx");

// Uso: node build_transcript.js [directorio]
// Lee cfg.json + turns_ts.json del directorio dado (o del cwd si se omite),
// escribe <id>_transcripcion.docx en ese mismo directorio.
const dir = process.argv[2] || ".";
const CFG = JSON.parse(fs.readFileSync(path.join(dir, "cfg.json"), "utf8"));
const turns = JSON.parse(fs.readFileSync(path.join(dir, "turns_ts.json"), "utf8"));

const FONT = "Arial", accent = "2E5B8A";
const ph = v => (v && String(v).trim()) ? v : "(pendiente)";

const meta = [
  ["ID", CFG.id],
  ["Archivo de audio", CFG.archivo || CFG.id],
  ["Idioma detectado", ph(CFG.idioma)],
  ["Duración", ph(CFG.duracion)],
  ["Hablantes", ph(CFG.hablantes)],
  ["Transcripción base", CFG.transcripcionBase || "Deepgram Nova-3 + diarización, detección automática de idioma"],
  ["Marcas de tiempo", "Reales, tomadas del JSON de la API (utterances o palabras); indican el inicio de cada turno"],
  ["Criterio de edición", CFG.criterioEdicion || "Transcripción automática con limpieza fina; fidelidad sobre pulido"],
  ["Estado", CFG.estado || "Borrador para revisión"],
];

function h1(t) { return new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { after: 120 }, children: [new TextRun({ text: t, bold: true, font: FONT, size: 30, color: accent })] }); }
function h2(t) { return new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 220, after: 120 }, children: [new TextRun({ text: t, bold: true, font: FONT, size: 24, color: accent })], border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "CCCCCC", space: 2 } } }); }

const children = [];
children.push(h1("Transcripción — " + CFG.id));
children.push(new Paragraph({ spacing: { after: 160 }, children: [new TextRun({ text: "Transcripción automática · para revisión", font: FONT, size: 18, italics: true, color: "666666" })] }));

children.push(h2("Metadatos"));
meta.forEach(([l, v]) => children.push(new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: l + ": ", bold: true, font: FONT, size: 20 }), new TextRun({ text: v, font: FONT, size: 20 })] })));

if (CFG.notas && CFG.notas.trim()) {
  children.push(h2("Notas del archivo"));
  children.push(new Paragraph({ spacing: { after: 40 }, children: [new TextRun({ text: CFG.notas, font: FONT, size: 20 })] }));
}

children.push(h2("Transcripción"));
turns.forEach(o => {
  if (o.note) {
    children.push(new Paragraph({
      spacing: { after: 140, line: 276 }, children: [
        new TextRun({ text: o.label + "  ", bold: true, font: FONT, size: 21, color: "B00020" }),
        new TextRun({ text: o.text, font: FONT, size: 21, italics: true })]
    }));
  } else {
    children.push(new Paragraph({
      spacing: { after: 140, line: 276 }, children: [
        new TextRun({ text: `${o.label} [${o.ts}]:  `, bold: true, font: FONT, size: 21 }),
        new TextRun({ text: o.text, font: FONT, size: 21 })]
    }));
  }
});

children.push(h2("Notas / pendientes de revisión"));
const pend = (CFG.pendientes && CFG.pendientes.length) ? CFG.pendientes : ["Sin pendientes: la transcripción no dejó tramos dudosos relevantes."];
pend.forEach(t => children.push(new Paragraph({ spacing: { after: 80, line: 264 }, children: [new TextRun({ text: "• " + t, font: FONT, size: 20 })] })));

const doc = new Document({
  styles: { default: { document: { run: { font: FONT, size: 21 } } } },
  sections: [{ properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } }, children }]
});
Packer.toBuffer(doc).then(b => {
  const out = path.join(dir, CFG.id + "_transcripcion.docx");
  fs.writeFileSync(out, b);
  console.log("OK ->", out);
});
