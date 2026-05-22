const base = {
  width: 20,
  height: 20,
  viewBox: '0 0 24 24',
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.8,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
  'aria-hidden': true,
}

export function IconSparkles(props) {
  return (
    <svg {...base} {...props}>
      <path d="M12 3v4" />
      <path d="M12 17v4" />
      <path d="M3 12h4" />
      <path d="M17 12h4" />
      <path d="M5.6 5.6l2.8 2.8" />
      <path d="M15.6 15.6l2.8 2.8" />
      <path d="M5.6 18.4l2.8-2.8" />
      <path d="M15.6 8.4l2.8-2.8" />
    </svg>
  )
}

export function IconShieldCheck(props) {
  return (
    <svg {...base} {...props}>
      <path d="M12 3l8 3v6c0 5-3.5 8.5-8 9-4.5-.5-8-4-8-9V6l8-3z" />
      <path d="M9 12l2 2 4-4" />
    </svg>
  )
}

export function IconGraph(props) {
  return (
    <svg {...base} {...props}>
      <circle cx="6" cy="6" r="2.2" />
      <circle cx="18" cy="6" r="2.2" />
      <circle cx="6" cy="18" r="2.2" />
      <circle cx="18" cy="18" r="2.2" />
      <circle cx="12" cy="12" r="2.4" />
      <path d="M7.6 7.6l3 3" />
      <path d="M16.4 7.6l-3 3" />
      <path d="M7.6 16.4l3-3" />
      <path d="M16.4 16.4l-3-3" />
    </svg>
  )
}

export function IconBeaker(props) {
  return (
    <svg {...base} {...props}>
      <path d="M9 3h6" />
      <path d="M10 3v6L4.5 18.5A2 2 0 0 0 6.2 21.5h11.6a2 2 0 0 0 1.7-3L14 9V3" />
      <path d="M7.5 14h9" />
    </svg>
  )
}

export function IconBolt(props) {
  return (
    <svg {...base} {...props}>
      <path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z" />
    </svg>
  )
}

export function IconLayers(props) {
  return (
    <svg {...base} {...props}>
      <path d="M12 3l9 5-9 5-9-5 9-5z" />
      <path d="M3 13l9 5 9-5" />
      <path d="M3 17l9 5 9-5" />
    </svg>
  )
}

export function IconArrowRight(props) {
  return (
    <svg {...base} {...props}>
      <path d="M5 12h14" />
      <path d="M13 6l6 6-6 6" />
    </svg>
  )
}

export function IconCheck(props) {
  return (
    <svg {...base} {...props} width={16} height={16}>
      <path d="M5 12l4 4 10-10" />
    </svg>
  )
}

export function IconUsers(props) {
  return (
    <svg {...base} {...props}>
      <circle cx="9" cy="8" r="3.2" />
      <path d="M3 21v-1.4A4.6 4.6 0 0 1 7.6 15h2.8A4.6 4.6 0 0 1 15 19.6V21" />
      <circle cx="17" cy="8.5" r="2.8" />
      <path d="M15.5 14.6c1.9.4 3.5 1.9 3.5 4V21" />
    </svg>
  )
}

export function IconCode(props) {
  return (
    <svg {...base} {...props}>
      <path d="M8 7l-5 5 5 5" />
      <path d="M16 7l5 5-5 5" />
      <path d="M14 4l-4 16" />
    </svg>
  )
}

export function IconClipboard(props) {
  return (
    <svg {...base} {...props}>
      <rect x="6" y="4" width="12" height="17" rx="2" />
      <path d="M9 4V3a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v1" />
      <path d="M9 10h6" />
      <path d="M9 14h6" />
      <path d="M9 18h4" />
    </svg>
  )
}

export function IconSun(props) {
  return (
    <svg {...base} {...props}>
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2" />
      <path d="M12 20v2" />
      <path d="M2 12h2" />
      <path d="M20 12h2" />
      <path d="M4.6 4.6l1.4 1.4" />
      <path d="M18 18l1.4 1.4" />
      <path d="M4.6 19.4L6 18" />
      <path d="M18 6l1.4-1.4" />
    </svg>
  )
}

export function IconMoon(props) {
  return (
    <svg {...base} {...props}>
      <path d="M21 12.8A8.5 8.5 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
    </svg>
  )
}

export function IconGithub(props) {
  return (
    <svg {...base} {...props}>
      <path d="M9 19c-4 1.5-4-2-6-2" />
      <path d="M15 21v-3.4a3 3 0 0 0-.9-2.4c3-.3 6-1.5 6-6.6a5 5 0 0 0-1.4-3.6 4.7 4.7 0 0 0-.1-3.5s-1.1-.4-3.6 1.3a12.4 12.4 0 0 0-6 0C6.6 1 5.5 1.4 5.5 1.4a4.7 4.7 0 0 0-.1 3.5A5 5 0 0 0 4 8.5c0 5.1 3 6.3 6 6.6a3 3 0 0 0-.9 2.4V21" />
    </svg>
  )
}

export function IconLogo(props) {
  return (
    <svg
      {...base}
      {...props}
      width={26}
      height={26}
      strokeWidth={1.6}
      viewBox="0 0 32 32"
    >
      <defs>
        <linearGradient id="lp-logo-grad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#0ea5e9" />
          <stop offset="100%" stopColor="#8b5cf6" />
        </linearGradient>
      </defs>
      <path
        d="M7 6c6 4 12 4 18 0"
        stroke="url(#lp-logo-grad)"
        fill="none"
      />
      <path
        d="M7 16c6 4 12 4 18 0"
        stroke="url(#lp-logo-grad)"
        fill="none"
      />
      <path
        d="M7 26c6 4 12 4 18 0"
        stroke="url(#lp-logo-grad)"
        fill="none"
      />
      <circle cx="7" cy="6" r="1.6" fill="url(#lp-logo-grad)" stroke="none" />
      <circle cx="25" cy="6" r="1.6" fill="url(#lp-logo-grad)" stroke="none" />
      <circle cx="7" cy="16" r="1.6" fill="url(#lp-logo-grad)" stroke="none" />
      <circle cx="25" cy="16" r="1.6" fill="url(#lp-logo-grad)" stroke="none" />
      <circle cx="7" cy="26" r="1.6" fill="url(#lp-logo-grad)" stroke="none" />
      <circle cx="25" cy="26" r="1.6" fill="url(#lp-logo-grad)" stroke="none" />
    </svg>
  )
}
