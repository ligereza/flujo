import { useState, useMemo } from 'react';
import { Calculator, Plus, Trash2, Download, RotateCcw } from 'lucide-react';
import { cn } from '../utils/cn';

interface LineItem {
  id: string;
  label: string;
  qty: number;
  price: number;
  category: string;
}

const CATEGORY_OPTIONS = ['Diseño', 'Impresión', 'Evento', 'Digital', 'Otro'];

const DEFAULT_ITEMS: LineItem[] = [
  { id: '1', label: 'Diseño etiqueta (vector, 2 revisiones)', qty: 1, price: 65000, category: 'Diseño' },
  { id: '2', label: 'Impresión etiqueta 16.5x6.5 cm (100 unidades)', qty: 1, price: 48000, category: 'Impresión' },
  { id: '3', label: 'Post Instagram (3 variaciones)', qty: 1, price: 30000, category: 'Digital' },
];

const PRESETS: { label: string; items: Omit<LineItem, 'id'>[] }[] = [
  {
    label: 'Etiqueta Suplementos',
    items: [
      { label: 'Diseño etiqueta vectorial (2 revisiones)', qty: 1, price: 65000, category: 'Diseño' },
      { label: 'Impresión 100 unidades', qty: 1, price: 48000, category: 'Impresión' },
      { label: 'Post Instagram', qty: 3, price: 12000, category: 'Digital' },
    ],
  },
  {
    label: 'Kit Evento BASE',
    items: [
      { label: 'Diseño flyer físico A5', qty: 1, price: 45000, category: 'Diseño' },
      { label: 'Impresión flyer A5 (200 unidades)', qty: 1, price: 35000, category: 'Impresión' },
      { label: 'Diseño plano/rider operativo', qty: 1, price: 30000, category: 'Diseño' },
      { label: 'Post Instagram evento', qty: 1, price: 15000, category: 'Digital' },
    ],
  },
  {
    label: 'Kit Evento MAINSTREAM',
    items: [
      { label: 'Diseño flyer físico A4 (2 idiomas)', qty: 1, price: 80000, category: 'Diseño' },
      { label: 'Impresión flyer A4 (500 unidades)', qty: 1, price: 75000, category: 'Impresión' },
      { label: 'Diseño pendón 80x180 cm', qty: 1, price: 55000, category: 'Diseño' },
      { label: 'Diseño cartelera digital', qty: 1, price: 35000, category: 'Digital' },
      { label: 'Plano/rider MAINSTREAM + SVG', qty: 1, price: 45000, category: 'Diseño' },
      { label: 'Pack Instagram (5 posts)', qty: 1, price: 40000, category: 'Digital' },
    ],
  },
];

function formatCLP(n: number) {
  return new Intl.NumberFormat('es-CL', { style: 'currency', currency: 'CLP', maximumFractionDigits: 0 }).format(n);
}

export default function QuotePanel() {
  const [items, setItems] = useState<LineItem[]>(DEFAULT_ITEMS);
  const [clientName, setClientName] = useState('');
  const [eventName, setEventName] = useState('');
  const [notes, setNotes] = useState('');
  const [discount, setDiscount] = useState(0);

  const subtotal = useMemo(() => items.reduce((acc, it) => acc + it.qty * it.price, 0), [items]);
  const discountAmount = Math.round(subtotal * (discount / 100));
  const total = subtotal - discountAmount;

  const addItem = () => {
    const id = String(Date.now());
    setItems(prev => [...prev, { id, label: '', qty: 1, price: 0, category: 'Diseño' }]);
  };

  const updateItem = (id: string, key: keyof LineItem, val: string | number) => {
    setItems(prev => prev.map(it => it.id === id ? { ...it, [key]: val } : it));
  };

  const removeItem = (id: string) => setItems(prev => prev.filter(it => it.id !== id));

  const applyPreset = (preset: typeof PRESETS[number]) => {
    setItems(preset.items.map((it, i) => ({ ...it, id: String(Date.now() + i) })));
  };

  const exportMarkdown = () => {
    const lines = [
      `# COTIZACIÓN — ${eventName || 'Sin nombre'}\n`,
      `**Cliente:** ${clientName || 'Sin especificar'}  `,
      `**Fecha:** ${new Date().toLocaleDateString('es-CL')}  `,
      `\n## DETALLE DE SERVICIOS\n`,
      `| Categoría | Servicio / Item | Qty | Precio Unitario | Total |`,
      `| :--- | :--- | :---: | :---: | :---: |`,
      ...items.map(it => `| ${it.category} | ${it.label} | ${it.qty} | ${formatCLP(it.price)} | ${formatCLP(it.qty * it.price)} |`),
      `\n--------------------------------------------------\n`,
      `**Subtotal:** ${formatCLP(subtotal)}  `,
      discount > 0 ? `**Descuento (${discount}%):** -${formatCLP(discountAmount)}  ` : '',
      `**TOTAL ESTIMADO:** ${formatCLP(total)}  `,
      `\n*Sujeto a confirmación técnica de ONG Reduciendo Daño.*`,
      notes ? `\n### NOTAS ADICIONALES\n${notes}` : '',
    ].filter(l => l !== undefined);

    const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `cotizacion_${(eventName || 'flujo').toLowerCase().replace(/\s+/g, '_')}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const categoryColor: Record<string, string> = {
    Diseño: 'text-purple-400 bg-purple-950/40 border-purple-800/40',
    Impresión: 'text-blue-400 bg-blue-950/40 border-blue-800/40',
    Evento: 'text-orange-400 bg-orange-950/40 border-orange-800/40',
    Digital: 'text-emerald-400 bg-emerald-950/40 border-emerald-800/40',
    Otro: 'text-zinc-400 bg-zinc-900 border-zinc-700',
  };

  return (
    <div className="space-y-6">
      {/* ── Printable Area for Quote (Designed for paper and PDF) ── */}
      <div className="hidden print:block text-black bg-white p-8 font-sans text-xs">
        <header className="border-b-4 border-black pb-4 mb-8 flex justify-between items-end">
          <div>
            <h1 className="text-3xl font-black italic tracking-tighter uppercase">COTIZACIÓN DE SERVICIOS</h1>
            <p className="text-[9px] uppercase tracking-[0.2em] font-bold mt-1">ONG Reduciendo Daño</p>
          </div>
          <div className="text-right">
            <p className="text-base font-bold">ORGANIZACIÓN RD</p>
            <p className="text-[9px] opacity-60">Servicios de Reducción de Daño v2026</p>
          </div>
        </header>

        <section className="mb-6">
          <h2 className="text-lg font-black uppercase tracking-tight mb-2">Resumen de la Cotización</h2>
          <div className="grid grid-cols-2 gap-4 leading-relaxed">
            <p><strong>Evento / Proyecto:</strong> {eventName || 'Sin nombre'}</p>
            <p><strong>Cliente:</strong> {clientName || 'Sin especificar'}</p>
            <p><strong>Fecha de Emisión:</strong> {new Date().toLocaleDateString('es-CL')}</p>
          </div>
        </section>

        <section className="mb-6">
          <h2 className="text-lg font-black uppercase tracking-tight mb-2">Detalle de Servicios</h2>
          <table className="w-full border-collapse border border-zinc-300 text-xs">
            <thead>
              <tr className="bg-zinc-100">
                <th className="border border-zinc-300 p-2 text-left">Categoría</th>
                <th className="border border-zinc-300 p-2 text-left">Ítem / Servicio</th>
                <th className="border border-zinc-300 p-2 text-center">Cantidad</th>
                <th className="border border-zinc-300 p-2 text-right">Precio Unitario</th>
                <th className="border border-zinc-300 p-2 text-right">Total</th>
              </tr>
            </thead>
            <tbody>
              {items.map(it => (
                <tr key={it.id}>
                  <td className="border border-zinc-300 p-2">{it.category}</td>
                  <td className="border border-zinc-300 p-2">{it.label}</td>
                  <td className="border border-zinc-300 p-2 text-center">{it.qty}</td>
                  <td className="border border-zinc-300 p-2 text-right">{formatCLP(it.price)}</td>
                  <td className="border border-zinc-300 p-2 text-right">{formatCLP(it.qty * it.price)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="text-right space-y-1.5 border-t border-black pt-4">
          <p><strong>Subtotal:</strong> {formatCLP(subtotal)}</p>
          {discount > 0 && <p><strong>Descuento ({discount}%):</strong> -{formatCLP(discountAmount)}</p>}
          <p className="text-base font-black"><strong>TOTAL ESTIMADO:</strong> {formatCLP(total)}</p>
        </section>

        {notes && (
          <section className="mt-6 border-t border-zinc-300 pt-4">
            <h3 className="font-bold mb-1">Notas Adicionales:</h3>
            <p className="text-zinc-600 leading-relaxed">{notes}</p>
          </section>
        )}
      </div>

      {/* Screen View (Interactive App Tool) */}
      <div className="print:hidden space-y-5">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-2xl font-black">
            <Calculator className="h-6 w-6" /> Cotización
          </h1>
          <p className="mt-1 text-sm text-zinc-500">Base editable para productora/jefatura.</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => { setItems(DEFAULT_ITEMS); setDiscount(0); }}
            className="flex items-center gap-2 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-xs font-bold text-zinc-400 hover:text-zinc-200 transition-colors"
          >
            <RotateCcw className="h-3.5 w-3.5" /> Reset
          </button>
          <button
            onClick={exportMarkdown}
            className="flex items-center gap-2 rounded-lg border border-zinc-700 bg-zinc-900 px-3 py-2 text-xs font-bold text-zinc-300 hover:bg-zinc-800 transition-colors"
          >
            <Download className="h-3.5 w-3.5" /> Exportar (.md)
          </button>
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_340px]">
        {/* Left: items */}
        <div className="space-y-4">
          {/* Client info */}
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/45 p-4 grid gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-[10px] font-bold uppercase tracking-widest text-zinc-500">Cliente</label>
              <input
                value={clientName}
                onChange={e => setClientName(e.target.value)}
                placeholder="Nombre productora / jefatura"
                className="w-full rounded-lg border border-zinc-800 bg-black/40 px-3 py-2 text-sm outline-none focus:border-zinc-600 transition-colors"
              />
            </div>
            <div>
              <label className="mb-1 block text-[10px] font-bold uppercase tracking-widest text-zinc-500">Proyecto / Evento</label>
              <input
                value={eventName}
                onChange={e => setEventName(e.target.value)}
                placeholder="Nombre del evento o proyecto"
                className="w-full rounded-lg border border-zinc-800 bg-black/40 px-3 py-2 text-sm outline-none focus:border-zinc-600 transition-colors"
              />
            </div>
          </div>

          {/* Presets */}
          <div className="flex flex-wrap gap-2">
            <span className="text-[10px] font-bold uppercase tracking-widest text-zinc-600 self-center">Presets:</span>
            {PRESETS.map(p => (
              <button
                key={p.label}
                onClick={() => applyPreset(p)}
                className="rounded-lg border border-zinc-800 bg-zinc-900 px-3 py-1.5 text-xs text-zinc-400 hover:border-zinc-600 hover:text-zinc-200 transition-colors"
              >
                {p.label}
              </button>
            ))}
          </div>

          {/* Line items */}
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/45 overflow-hidden">
            {/* Table header */}
            <div className="grid grid-cols-[1fr_60px_100px_80px_32px] gap-2 px-4 py-2 border-b border-zinc-800 bg-zinc-950/50">
              {['Descripción', 'Qty', 'Precio unit.', 'Total', ''].map(h => (
                <div key={h} className="text-[9px] font-bold uppercase tracking-widest text-zinc-600">{h}</div>
              ))}
            </div>

            {/* Rows */}
            <div className="divide-y divide-zinc-800/60">
              {items.map(it => (
                <div key={it.id} className="grid grid-cols-[1fr_60px_100px_80px_32px] gap-2 px-4 py-2.5 items-center">
                  <div className="min-w-0 space-y-1">
                    <input
                      value={it.label}
                      onChange={e => updateItem(it.id, 'label', e.target.value)}
                      placeholder="Descripción del servicio..."
                      className="w-full bg-transparent text-sm font-medium outline-none placeholder:text-zinc-700 text-zinc-200"
                    />
                    <select
                      value={it.category}
                      onChange={e => updateItem(it.id, 'category', e.target.value)}
                      className={cn('rounded border px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-widest outline-none bg-transparent cursor-pointer', categoryColor[it.category] || categoryColor['Otro'])}
                    >
                      {CATEGORY_OPTIONS.map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                  </div>
                  <input
                    type="number"
                    value={it.qty}
                    onChange={e => updateItem(it.id, 'qty', Number(e.target.value))}
                    min={1}
                    className="w-full bg-transparent text-center font-mono text-sm font-bold outline-none text-zinc-300"
                  />
                  <input
                    type="number"
                    value={it.price}
                    onChange={e => updateItem(it.id, 'price', Number(e.target.value))}
                    className="w-full bg-transparent text-right font-mono text-sm font-bold outline-none text-zinc-300"
                  />
                  <div className="text-right font-mono text-xs font-bold text-zinc-400">
                    {formatCLP(it.qty * it.price)}
                  </div>
                  <button
                    onClick={() => removeItem(it.id)}
                    className="flex items-center justify-center text-zinc-700 hover:text-red-400 transition-colors"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              ))}
            </div>

            {/* Add row */}
            <div className="border-t border-zinc-800 px-4 py-2">
              <button
                onClick={addItem}
                className="flex items-center gap-2 text-xs text-zinc-500 hover:text-zinc-200 transition-colors"
              >
                <Plus className="h-3.5 w-3.5" /> Agregar ítem
              </button>
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="mb-1 block text-[10px] font-bold uppercase tracking-widest text-zinc-500">Notas</label>
            <textarea
              value={notes}
              onChange={e => setNotes(e.target.value)}
              rows={3}
              placeholder="Condiciones, plazos, observaciones..."
              className="w-full rounded-xl border border-zinc-800 bg-zinc-900/50 px-4 py-3 text-sm outline-none focus:border-zinc-600 transition-colors resize-y"
            />
          </div>
        </div>

        {/* Right: summary */}
        <div className="space-y-4">
          {/* Totals */}
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/45 p-5 space-y-3">
            <h2 className="text-sm font-bold uppercase tracking-widest text-zinc-500">Resumen</h2>

            {/* By category */}
            {CATEGORY_OPTIONS.map(cat => {
              const catTotal = items.filter(it => it.category === cat).reduce((a, it) => a + it.qty * it.price, 0);
              if (!catTotal) return null;
              return (
                <div key={cat} className="flex items-center justify-between text-xs text-zinc-500">
                  <span className={cn('rounded border px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-widest', categoryColor[cat] || categoryColor['Otro'])}>{cat}</span>
                  <span>{formatCLP(catTotal)}</span>
                </div>
              );
            })}

            <div className="border-t border-zinc-800 pt-3 space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-zinc-400">Subtotal</span>
                <span className="font-mono font-bold">{formatCLP(subtotal)}</span>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-sm text-zinc-400 shrink-0">Descuento</span>
                <input
                  type="number"
                  value={discount}
                  onChange={e => setDiscount(Math.min(100, Math.max(0, Number(e.target.value))))}
                  className="w-16 rounded-lg border border-zinc-800 bg-black/40 px-2 py-1 text-center font-mono text-sm outline-none focus:border-zinc-600"
                  min={0}
                  max={100}
                />
                <span className="text-zinc-500">%</span>
                {discount > 0 && (
                  <span className="ml-auto font-mono text-sm text-red-400">-{formatCLP(discountAmount)}</span>
                )}
              </div>

              <div className="flex items-center justify-between rounded-xl border border-emerald-800/40 bg-emerald-950/30 px-3 py-2">
                <span className="text-sm font-bold text-emerald-300">TOTAL</span>
                <span className="font-mono text-lg font-black text-emerald-300">{formatCLP(total)}</span>
              </div>
            </div>
          </div>

          {/* Quote preview header */}
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/30 p-4 space-y-2">
            <h2 className="text-sm font-bold uppercase tracking-widest text-zinc-500">Vista previa</h2>
            <div className="rounded-xl bg-black/40 p-4 space-y-2 text-xs font-mono text-zinc-400">
              <p className="text-zinc-200 font-bold text-sm">{eventName || '(sin nombre de proyecto)'}</p>
              <p>Cliente: {clientName || '—'}</p>
              <p>Fecha: {new Date().toLocaleDateString('es-CL')}</p>
              <div className="border-t border-zinc-800 my-2" />
              {items.map(it => (
                <p key={it.id} className="truncate">
                  {it.label || '(sin descripción)'} × {it.qty} = {formatCLP(it.qty * it.price)}
                </p>
              ))}
              <div className="border-t border-zinc-800 my-2" />
              <p className="text-zinc-200 font-bold">TOTAL: {formatCLP(total)}</p>
              {notes && <p className="text-zinc-600 text-[10px] mt-2">{notes}</p>}
            </div>
          </div>

          {/* CLI hint */}
          <div className="rounded-2xl border border-zinc-800/60 bg-zinc-900/20 p-3">
            <p className="text-[10px] font-bold uppercase tracking-widest text-zinc-600 mb-2">CLI equivalente</p>
            <code className="block text-[10px] text-zinc-500 leading-5">
              py -m flujo brief paquete-cotizacion jobs/&lt;job&gt;
            </code>
          </div>
        </div>
      </div>
    </div>
  </div>
  );
}
