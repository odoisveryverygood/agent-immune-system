type Props = { role: string; status?: string; rejected?: boolean };
/** Original vector characters. Roles and activity are supplied by the real task. */
export default function AgentRobot({ role, status, rejected }: Props) {
  const shopping = role === "shopping",
    repair = role === "repair",
    review = role === "reviewer";
  const accent = rejected
    ? "#E68E7D"
    : repair
      ? "#EFAB64"
      : review
        ? "#9ECBBE"
        : "#BBD7F4";
  return (
    <svg
      className={`agent-robot ${status === "running" ? "robot-working" : ""}`}
      viewBox="0 0 140 150"
      fill="none"
      aria-hidden="true"
    >
      <ellipse cx="70" cy="142" rx="40" ry="6" fill="#080E18" opacity=".45" />
      <path
        d="M51 118V134H39M89 118V134H102"
        stroke="#7890A6"
        strokeWidth="10"
        strokeLinecap="round"
      />
      <path
        d="M40 88L29 105M100 88L111 105"
        stroke="#BBD7F4"
        strokeWidth="10"
        strokeLinecap="round"
      />
      <circle cx="27" cy="108" r="8" fill={accent} />
      <circle cx="113" cy="108" r="8" fill={accent} />
      <rect
        x="42"
        y="77"
        width="56"
        height="48"
        rx="18"
        fill="#D8E3E8"
        stroke="#8AABBC"
        strokeWidth="2"
      />
      <path
        d="M48 83H91"
        stroke="#FFFFFF"
        strokeOpacity=".6"
        strokeWidth="3"
        strokeLinecap="round"
      />
      <rect x="62" y="69" width="16" height="14" rx="5" fill="#68839A" />
      <path
        d="M70 28V15"
        stroke="#8BA5BA"
        strokeWidth="4"
        strokeLinecap="round"
      />
      <circle cx="70" cy="12" r="6" fill={accent} />
      <circle cx="68" cy="10" r="2" fill="#FFF" fillOpacity=".7" />
      <rect x="27" y="41" width="11" height="22" rx="5" fill={accent} />
      <rect x="102" y="41" width="11" height="22" rx="5" fill={accent} />
      <rect
        x="33"
        y="27"
        width="74"
        height="51"
        rx={review ? 17 : 22}
        fill="#F4F1E9"
        stroke="#A9BDC9"
        strokeWidth="2"
      />
      <path
        d="M46 33C50 30 87 30 94 34"
        stroke="#FFF"
        strokeWidth="3"
        strokeLinecap="round"
      />
      <rect x="41" y="39" width="58" height="28" rx="13" fill="#233446" />
      <rect x="51" y="47" width="9" height="11" rx="4.5" fill={accent} />
      <rect x="80" y="47" width="9" height="11" rx="4.5" fill={accent} />
      <path
        d="M65 59Q70 62 75 59"
        stroke={accent}
        strokeWidth="2"
        strokeLinecap="round"
      />
      {repair && (
        <>
          <path d="M33 39Q35 18 70 21Q104 18 107 39Z" fill="#EFAB64" />
          <path
            d="M66 22V36M42 29L45 37M96 29L93 37"
            stroke="#B7763B"
            strokeWidth="3"
            strokeLinecap="round"
          />
          <path
            d="M30 40H110"
            stroke="#FAC693"
            strokeWidth="5"
            strokeLinecap="round"
          />
        </>
      )}
      {review && (
        <>
          <path d="M35 34L70 21L105 34L96 40H44Z" fill="#759F98" />
          <path d="M66 27H74V33L70 36L66 33Z" fill="#E6F3EC" />
        </>
      )}
      {!shopping && !repair && !review && (
        <>
          <circle cx="84" cy="52" r="14" stroke="#BBD7F4" strokeWidth="4" />
          <path
            d="M94 62L104 72"
            stroke="#BBD7F4"
            strokeWidth="5"
            strokeLinecap="round"
          />
          <circle cx="84" cy="52" r="10" fill="#BBD7F4" fillOpacity=".13" />
        </>
      )}
      <rect x="54" y="88" width="32" height="26" rx="9" fill="#233446" />
      {shopping ? (
        <g
          stroke="#EFAB64"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M61 98H79L77 109H63Z" />
          <path d="M66 98V96A4 4 0 0 1 74 96V98" />
        </g>
      ) : repair ? (
        <path
          d="M77 93A6 6 0 0 0 69 101L61 109L64 112L72 104A6 6 0 0 0 80 96L76 100L73 97Z"
          fill="#EFAB64"
        />
      ) : review ? (
        <g
          stroke="#A5D4C5"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M70 92L79 95V101Q77 108 70 111Q63 108 61 101V95Z" />
          <path d="M66 101L69 104L75 98" />
        </g>
      ) : (
        <g stroke="#BBD7F4" strokeWidth="2.5" strokeLinecap="round">
          <circle cx="68" cy="99" r="5" />
          <path d="M72 103L78 109" />
        </g>
      )}
      <circle
        cx="89"
        cy="116"
        r="3"
        fill={
          rejected ? "#E68E7D" : status === "running" ? "#EFAB64" : "#709F8B"
        }
      />
    </svg>
  );
}
