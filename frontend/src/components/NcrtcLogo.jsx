export default function NcrtcLogo({ inverse = false, className = '' }) {
  const dots = [
    [17, 12, 'blue'], [35, 12, 'blue'], [53, 12, 'blue'], [71, 12, 'orange'],
    [27, 30, 'blue'], [45, 30, 'blue'], [63, 30, 'blue'], [81, 30, 'orange'],
    [27, 48, 'blue'], [45, 48, 'blue'], [63, 48, 'orange'], [81, 48, 'orange'], [99, 48, 'orange'],
    [27, 66, 'blue'], [45, 66, 'blue'], [63, 66, 'orange'], [81, 66, 'orange'],
    [17, 84, 'blue'], [35, 84, 'blue'], [53, 84, 'blue'], [71, 84, 'blue'],
  ]

  return (
    <svg className={`ncrtc-logo${inverse ? ' ncrtc-logo-inverse' : ''} ${className}`} viewBox="0 0 420 100" role="img" aria-label="NCRTC — Bus Management System" xmlns="http://www.w3.org/2000/svg">
      <g aria-hidden="true">
        {dots.map(([cx, cy, color], index) => <circle key={index} cx={cx} cy={cy} r="7.5" className={`logo-dot-${color}`} />)}
      </g>
      <text x="132" y="57" className="logo-wordmark">NCRTC</text>
      <text x="134" y="81" className="logo-tagline">BUS MANAGEMENT SYSTEM</text>
    </svg>
  )
}
