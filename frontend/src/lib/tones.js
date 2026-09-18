/** Series colours by index, as tone names viz.jsx maps to literal classes. Kept out
 *  of the component file so Fast Refresh can reload it cleanly. */
export const toneFor = (i) => ['brand', 'bright', 'faint', 'line', 'ink', 'soft'][i % 6]
export const TONE_CLASS = {
  brand: 'bg-brand', bright: 'bg-brand-bright', faint: 'bg-ink-faint',
  line: 'bg-line-strong', ink: 'bg-ink', soft: 'bg-brand-soft',
}
