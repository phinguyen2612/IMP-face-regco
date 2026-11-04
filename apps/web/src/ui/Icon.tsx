const paths = {
  camera: 'M3 7h12v12H3z M15 11l6-4v12l-6-4 M6 4h6',
  image: 'M3 3h18v18H3z M3 17l6-6 4 4 3-3 5 5 M8 7h.01',
  arrow: 'M5 12h14 M13 6l6 6-6 6',
  download: 'M12 3v12 M7 10l5 5 5-5 M4 16v5h16v-5',
  grid: 'M3 3h7v7H3z M14 3h7v7h-7z M3 14h7v7H3z M14 14h7v7h-7z',
  check: 'M5 12l4 4L19 6',
  warning: 'M12 3L2 21h20L12 3z M12 9v5 M12 17v1',
  clock: 'M12 3a9 9 0 1 0 0 18 9 9 0 1 0 0-18 M12 7v5l3 2',
  settings: 'M4 7h16 M4 17h16 M8 4v6 M16 14v6',
  logout: 'M9 3H3v18h6 M8 12h13 M17 8l4 4-4 4',
};
export function Icon({name, className = ''}: {name: keyof typeof paths; className?: string}) {
  return <svg className={`product-icon ${className}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]}/></svg>;
}
