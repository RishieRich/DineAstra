/*
 * Indian number formatting.
 *
 * Grouping is hand-rolled rather than delegated to Intl so the output is
 * identical in every browser and in Node, and so no currency string is ever
 * assembled anywhere else in the app.
 *
 *   formatCurrency(482300)         -> "Rs 4,82,300"  (with the rupee sign)
 *   formatCompactCurrency(4820000) -> "Rs 48.20L"
 */

const RUPEE = '₹'
const LAKH = 100000
const CRORE = 10000000

/** Group an integer string the Indian way: last three, then pairs. */
function groupIndian(digits) {
  if (digits.length <= 3) return digits
  const last3 = digits.slice(-3)
  let rest = digits.slice(0, -3)
  const groups = []
  while (rest.length > 2) {
    groups.unshift(rest.slice(-2))
    rest = rest.slice(0, -2)
  }
  if (rest.length > 0) groups.unshift(rest)
  return `${groups.join(',')},${last3}`
}

/** "4,82,300" -- no currency sign, no decimals. */
export function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return '--'
  const rounded = Math.round(Math.abs(value))
  const sign = value < 0 ? '-' : ''
  return sign + groupIndian(String(rounded))
}

/** "₹4,82,300" -- the everyday figure, exact to the rupee. */
export function formatCurrency(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return '--'
  return RUPEE + formatNumber(value)
}

/** "₹48.20L" / "₹1.24Cr" -- headline figures only. Falls back to the exact
 *  form below one lakh, where an abbreviation would say less than the number. */
export function formatCompactCurrency(value) {
  if (value === null || value === undefined || Number.isNaN(value)) return '--'
  const abs = Math.abs(value)
  const sign = value < 0 ? '-' : ''
  if (abs >= CRORE) return `${sign}${RUPEE}${(abs / CRORE).toFixed(2)}Cr`
  if (abs >= LAKH) return `${sign}${RUPEE}${(abs / LAKH).toFixed(2)}L`
  return formatCurrency(value)
}

/** "61.2%" */
export function formatPercent(value, decimals = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) return '--'
  return `${value.toFixed(decimals)}%`
}

/** "+3.5 pts" / "-1.2 pts" -- percentage-point movement, always signed. */
export function formatPoints(value, decimals = 1) {
  if (value === null || value === undefined || Number.isNaN(value)) return '--'
  const sign = value > 0 ? '+' : value < 0 ? '-' : ''
  return `${sign}${Math.abs(value).toFixed(decimals)} pts`
}

/** "14 September 2026" */
export function formatDate(iso) {
  if (!iso) return '--'
  const [y, m, d] = iso.split('-').map(Number)
  const months = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
  ]
  return `${d} ${months[m - 1]} ${y}`
}

/** "14 Sep" -- for dense contexts like table rows. */
export function formatDateShort(iso) {
  if (!iso) return '--'
  const [, m, d] = iso.split('-').map(Number)
  const months = [
    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
  ]
  return `${d} ${months[m - 1]}`
}
