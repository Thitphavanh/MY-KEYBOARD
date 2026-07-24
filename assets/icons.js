/* NexByte Computer — inline SVG icon set (replaces emoji everywhere) */

const ICON_PATHS = {
  cart: `<circle cx="9" cy="20" r="1.4"/><circle cx="18" cy="20" r="1.4"/><path d="M2.5 3h2l2.4 12.2a2 2 0 0 0 2 1.6h8.2a2 2 0 0 0 2-1.6L21 8H6"/>`,
  heart: `<path d="M12 20.5s-7-4.35-9.5-9A5.5 5.5 0 0 1 12 6.2 5.5 5.5 0 0 1 21.5 11.5c-2.5 4.65-9.5 9-9.5 9z"/>`,
  user: `<circle cx="12" cy="8" r="3.6"/><path d="M4.5 20c1.4-3.6 4.4-5.5 7.5-5.5s6.1 1.9 7.5 5.5"/>`,
  search: `<circle cx="10.5" cy="10.5" r="6.5"/><path d="M20 20l-4.8-4.8"/>`,
  globe: `<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>`,
  menu: `<path d="M3 6h18M3 12h18M3 18h18"/>`,
  close: `<path d="M5 5l14 14M19 5L5 19"/>`,
  chevronDown: `<path d="M5 8l7 7 7-7"/>`,
  chevronRight: `<path d="M8 5l7 7-7 7"/>`,
  truck: `<path d="M2 7h11v9H2z"/><path d="M13 10h4l4 3.5V16h-8z"/><circle cx="6.5" cy="18" r="1.6"/><circle cx="17" cy="18" r="1.6"/>`,
  shield: `<path d="M12 3l8 3v6c0 5-3.4 8.4-8 9-4.6-.6-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>`,
  mapPin: `<path d="M12 21s7-6.1 7-11.5a7 7 0 1 0-14 0C5 14.9 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.4"/>`,
  phone: `<path d="M5 4h3l1.5 4.5-2 1.5a12 12 0 0 0 6.5 6.5l1.5-2L19 16v3a2 2 0 0 1-2.2 2C9.8 20.4 3.6 14.2 3 7.2A2 2 0 0 1 5 4z"/>`,
  mail: `<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 6.5l9 6.5 9-6.5"/>`,
  arrowRight: `<path d="M4 12h16M14 5l7 7-7 7"/>`,
  play: `<path d="M7 4l13 8-13 8z"/>`,
  clock: `<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>`,
  x: `<path d="M6 6l12 12M18 6L6 18"/>`,
  laptop: `<rect x="4" y="5" width="16" height="10" rx="1.2"/><path d="M2 19h20l-2-3H4z"/>`,
  desktop: `<rect x="5" y="4" width="9" height="16" rx="1.2"/><circle cx="9.5" cy="8" r="0.6" fill="currentColor" stroke="none"/><path d="M18 9v9M15.5 6.5h5M15.5 12h5"/>`,
  monitor: `<rect x="3" y="4" width="18" height="12" rx="1.2"/><path d="M9 20h6M12 16v4"/>`,
  gpu: `<rect x="3" y="7" width="18" height="9" rx="1.2"/><circle cx="8" cy="11.5" r="2"/><circle cx="14.5" cy="11.5" r="2"/><path d="M3 16v2h4v-2"/>`,
  cpu: `<rect x="7" y="7" width="10" height="10" rx="1.2"/><path d="M9 3v3M12 3v3M15 3v3M9 18v3M12 18v3M15 18v3M3 9h3M3 12h3M3 15h3M18 9h3M18 12h3M18 15h3"/>`,
  mouse: `<rect x="7" y="3" width="10" height="18" rx="5"/><path d="M12 3v6"/>`,
  keyboard: `<rect x="2.5" y="6" width="19" height="12" rx="1.2"/><path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M6 14h12"/>`,
  storage: `<rect x="4" y="4" width="16" height="16" rx="2"/><circle cx="8" cy="8" r="1.4"/><path d="M4 15h16"/>`,
  headset: `<path d="M4 13v-1a8 8 0 0 1 16 0v1"/><rect x="3" y="13" width="4" height="6" rx="1.2"/><rect x="17" y="13" width="4" height="6" rx="1.2"/>`,
  plug: `<path d="M8 3v5M16 3v5M6 8h12v3a6 6 0 0 1-12 0z"/><path d="M12 17v4"/>`,
  grid: `<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>`,
  home: `<path d="M4 11l8-7 8 7"/><path d="M6 10v9h5v-6h2v6h5v-9"/>`,
  check: `<path d="M5 12l5 5L20 7"/>`,
  edit: `<path d="M4 20h4l11-11-4-4L4 16z"/><path d="M13.5 6.5l4 4"/>`,
  chart: `<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>`,
  sliders: `<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h13M21 18h1"/><circle cx="16" cy="6" r="2"/><circle cx="8" cy="12" r="2"/><circle cx="19" cy="18" r="2"/>`,
  palette: `<path d="M12 3a9 9 0 1 0 0 18c1.1 0 2-.9 2-2 0-.5-.2-1-.5-1.4-.3-.4-.5-.9-.5-1.4 0-1.1.9-2 2-2h1.8A4.7 4.7 0 0 0 21 9.5C21 5.9 16.9 3 12 3z"/><circle cx="7.5" cy="10.5" r="1.2" fill="currentColor" stroke="none"/><circle cx="11" cy="7" r="1.2" fill="currentColor" stroke="none"/><circle cx="15.5" cy="8" r="1.2" fill="currentColor" stroke="none"/>`,
  clockTime: `<circle cx="12" cy="12" r="9"/><path d="M12 7v5l4 2"/>`,
  package: `<path d="M3 8l9-5 9 5-9 5-9-5z"/><path d="M3 8v8l9 5 9-5V8"/><path d="M12 13v8"/>`,
  bank: `<path d="M3 10l9-6 9 6"/><path d="M5 10v8M10 10v8M14 10v8M19 10v8"/><path d="M3 20h18"/>`,
  upload: `<path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/>`,
  arrowLeft: `<path d="M20 12H4M10 5l-7 7 7 7"/>`,
  eye: `<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/>`,
  image: `<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="8.5" cy="9.5" r="1.5"/><path d="M21 15l-5-5-4 4-3-3-6 6"/>`,
  plus: `<path d="M12 4v16M4 12h16"/>`,
  trash: `<path d="M4 7h16"/><path d="M9 7V4h6v3"/><path d="M6 7l1 13a2 2 0 0 0 2 2h6a2 2 0 0 0 2-2l1-13"/><path d="M10 11v6M14 11v6"/>`,
  desk: `<path d="M3 8h18"/><path d="M5 8v10M19 8v10"/><path d="M3 14h18"/>`,
  stool: `<rect x="5" y="6" width="14" height="4" rx="1.5"/><path d="M7 10v9M17 10v9"/>`,
};

/* brand / filled icons (fill=currentColor instead of stroke) */
const ICON_FILLED = {
  facebook: { vb: "0 0 24 24", d: `<path d="M22 12a10 10 0 1 0-11.5 9.9v-7H8v-3h2.5V9.5A3.5 3.5 0 0 1 14 6h2v3h-1.5c-.8 0-1 .4-1 1v2h2.5l-.4 3H13.5v7A10 10 0 0 0 22 12z"/>` },
  heartFill: { vb: "0 0 24 24", d: `<path d="M12 20.5s-7-4.35-9.5-9A5.5 5.5 0 0 1 12 6.2 5.5 5.5 0 0 1 21.5 11.5c-2.5 4.65-9.5 9-9.5 9z"/>` },
  whatsapp: { vb: "0 0 16 16", d: `<path d="M13.601 2.326A7.85 7.85 0 0 0 7.994 0C3.627 0 .068 3.558.064 7.926c0 1.399.366 2.76 1.057 3.965L0 16l4.204-1.102a7.9 7.9 0 0 0 3.79.965h.004c4.368 0 7.926-3.558 7.93-7.93A7.9 7.9 0 0 0 13.6 2.326zM7.994 14.521a6.6 6.6 0 0 1-3.356-.92l-.24-.144-2.494.654.666-2.433-.156-.251a6.56 6.56 0 0 1-1.006-3.492c0-3.626 2.957-6.584 6.591-6.584a6.56 6.56 0 0 1 4.66 1.931 6.56 6.56 0 0 1 1.928 4.66c-.004 3.639-2.961 6.596-6.593 6.596zm3.615-4.934c-.199-.1-1.176-.58-1.358-.646-.182-.067-.315-.1-.448.1-.133.199-.513.646-.629.777-.116.133-.232.148-.43.05-.199-.1-.836-.308-1.592-.982-.588-.525-.985-1.174-1.101-1.372-.116-.199-.012-.307.087-.406.09-.09.199-.232.298-.348.1-.116.133-.199.199-.332.067-.133.033-.249-.017-.348-.05-.1-.448-1.079-.613-1.479-.161-.388-.324-.336-.448-.342-.116-.006-.249-.007-.382-.007a.73.73 0 0 0-.531.25c-.182.199-.696.68-.696 1.658 0 .977.712 1.922.81 2.054.1.133 1.4 2.132 3.392 2.99.474.205.844.327 1.132.418.475.15.907.129 1.249.078.381-.057 1.176-.48 1.341-.943.166-.464.166-.86.116-.943-.05-.083-.182-.133-.38-.232z"/>` },
};

function icon(name, cls) {
  if (ICON_FILLED[name]) {
    const f = ICON_FILLED[name];
    return `<svg class="icon ${cls||""}" viewBox="${f.vb}" fill="currentColor">${f.d}</svg>`;
  }
  const d = ICON_PATHS[name];
  if (!d) return "";
  return `<svg class="icon ${cls||""}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
}
