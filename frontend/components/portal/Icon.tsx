import type { ReactNode } from "react";

// Iconos de línea (24x24) usados por Mi Portal y las pantallas de acceso.
const PATHS: Record<string, ReactNode> = {
  home: <path d="M4 10.5 12 4l8 6.5V19a1 1 0 0 1-1 1h-4v-6H9v6H5a1 1 0 0 1-1-1z" />,
  folder: <path d="M3.5 7.5A1.5 1.5 0 0 1 5 6h4l2 2h8a1.5 1.5 0 0 1 1.5 1.5v8A1.5 1.5 0 0 1 19 19H5a1.5 1.5 0 0 1-1.5-1.5z" />,
  tasks: (
    <>
      <path d="m4 6 1.5 1.5L8 5M4 12l1.5 1.5L8 11M4 18l1.5 1.5L8 17" />
      <path d="M11 6.5h9M11 12.5h9M11 18.5h9" />
    </>
  ),
  upload: (
    <>
      <path d="M12 16V5m0 0L8 9m4-4 4 4" />
      <path d="M5 15v3a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-3" />
    </>
  ),
  bell: (
    <>
      <path d="M6 16V11a6 6 0 1 1 12 0v5l1.5 2h-15z" />
      <path d="M10 20.5a2 2 0 0 0 4 0" />
    </>
  ),
  logout: (
    <>
      <path d="M10 5H6a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h4" />
      <path d="M14 8l4 4-4 4M18 12H9" />
    </>
  ),
  download: (
    <>
      <path d="M12 4v11m0 0-4-4m4 4 4-4" />
      <path d="M5 19h14" />
    </>
  ),
  cloudDownload: (
    <>
      <path d="M7 17.5a4 4 0 0 1-.6-7.95A5.5 5.5 0 0 1 17 8.5a4.5 4.5 0 0 1 .5 9" />
      <path d="M12 11v8m0 0-3-3m3 3 3-3" />
    </>
  ),
  eye: (
    <>
      <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z" />
      <circle cx="12" cy="12" r="2.8" />
    </>
  ),
  search: (
    <>
      <circle cx="11" cy="11" r="6.5" />
      <path d="m16 16 4.5 4.5" />
    </>
  ),
  chevronRight: <path d="m9 6 6 6-6 6" />,
  chevronLeft: <path d="m15 6-6 6 6 6" />,
  chevronDown: <path d="m6 9 6 6 6-6" />,
  arrowUpRight: <path d="M7 17 17 7M9 7h8v8" />,
  arrowLeft: <path d="M19 12H5m0 0 6-6m-6 6 6 6" />,
  plus: <path d="M12 5v14M5 12h14" />,
  user: (
    <>
      <circle cx="12" cy="8.5" r="3.5" />
      <path d="M5 19.5c1-3.5 4-5 7-5s6 1.5 7 5" />
    </>
  ),
  lock: (
    <>
      <rect x="5" y="10.5" width="14" height="9.5" rx="2" />
      <path d="M8.5 10.5V8a3.5 3.5 0 0 1 7 0v2.5" />
    </>
  ),
  idCard: (
    <>
      <rect x="3" y="5" width="18" height="14" rx="2" />
      <circle cx="9" cy="11" r="2" />
      <path d="M6 16c.5-1.5 1.7-2 3-2s2.5.5 3 2M14.5 10h4M14.5 13h3" />
    </>
  ),
  hash: <path d="M9 4 7 20M17 4l-2 16M4 9h16M3.5 15h16" />,
  mail: (
    <>
      <rect x="3" y="5.5" width="18" height="13" rx="2" />
      <path d="m3.5 7 8.5 6 8.5-6" />
    </>
  ),
  receipt: (
    <>
      <path d="M6 3.5h12v17l-2-1.5-2 1.5-2-1.5-2 1.5-2-1.5-2 1.5z" />
      <path d="M9 9h6M9 13h6" />
    </>
  ),
  certificate: (
    <>
      <rect x="4" y="4" width="16" height="12" rx="2" />
      <circle cx="12" cy="10" r="2.5" />
      <path d="m9.5 16-1 4.5 3.5-2 3.5 2-1-4.5" />
    </>
  ),
  clip: <path d="m20 11-8 8a5 5 0 0 1-7-7l8.5-8.5a3.5 3.5 0 0 1 5 5L10 17a2 2 0 0 1-3-3l7.5-7.5" />,
  chat: (
    <>
      <path d="M4 5.5h16a1 1 0 0 1 1 1V16a1 1 0 0 1-1 1h-8l-5 3.5V17H4a1 1 0 0 1-1-1V6.5a1 1 0 0 1 1-1z" />
    </>
  ),
  info: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 11v5M12 8v.01" />
    </>
  ),
  check: <path d="m5 12.5 4.5 4.5L19 7.5" />,
  refresh: (
    <>
      <path d="M19 8a7.5 7.5 0 0 0-13-2L4.5 8M4.5 4v4h4" />
      <path d="M5 16a7.5 7.5 0 0 0 13 2l1.5-2m0 4v-4h-4" />
    </>
  ),
  fileNew: (
    <>
      <path d="M7 3.5h7l4 4V20a.5.5 0 0 1-.5.5h-10.5a.5.5 0 0 1-.5-.5z" />
      <path d="M14 3.5v4h4M9.5 13h5M9.5 16.5h5" />
    </>
  ),
  clock: (
    <>
      <circle cx="12" cy="12" r="8.5" />
      <path d="M12 7.5V12l3 2" />
    </>
  ),
  box: (
    <>
      <path d="M3.5 7.5h17V10h-17zM5 10v8a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-8M10 13.5h4" />
    </>
  ),
  menu: <path d="M4 7h16M4 12h16M4 17h16" />,
  whatsapp: (
    <>
      <path d="M4 20l1.2-4.2A8 8 0 1 1 8.3 18.9z" />
      <path d="M9 9.5c0 3 2.5 5.5 5.5 5.5l1-1.3-1.8-1-.8.7a4 4 0 0 1-2-2l.7-.8-1-1.8z" />
    </>
  ),
  eyeOff: (
    <>
      <path d="M3 3l18 18M10.5 6a8.8 8.8 0 0 1 1.5-.5c6 0 9.5 6.5 9.5 6.5a16 16 0 0 1-2.4 3M6.7 7.5C4 9.2 2.5 12 2.5 12s3.5 6.5 9.5 6.5c1.3 0 2.5-.3 3.5-.8" />
    </>
  ),
};

export type IconName = keyof typeof PATHS;

export function Icon({ name, size = 20, stroke = 1.8 }: { name: IconName; size?: number; stroke?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={stroke}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {PATHS[name]}
    </svg>
  );
}
