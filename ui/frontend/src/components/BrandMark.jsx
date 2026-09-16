/*
 * The DineAstra mark.
 *
 * An eight-pointed star -- astra -- set inside a charger ring, so the mark
 * carries both halves of the name: the star, and the plate it sits on. The
 * eight-pointed star is a long-standing motif in Indian decorative work,
 * which suits a Bengaluru restaurant group better than an abstract glyph.
 *
 * It is drawn rather than lettered on purpose: a two-letter monogram at
 * 24px is read as whatever two letters the viewer expects, and "DA" was
 * being read as DNA.
 */

// Sixteen alternating vertices, outer radius 15.5 and inner 6.6 about a
// 48x48 box. Computed once rather than hand-placed, so the points are even.
const STAR =
  'M 24.00 8.50 L 26.53 17.90 L 34.96 13.04 L 30.10 21.47 L 39.50 24.00 ' +
  'L 30.10 26.53 L 34.96 34.96 L 26.53 30.10 L 24.00 39.50 L 21.47 30.10 ' +
  'L 13.04 34.96 L 17.90 26.53 L 8.50 24.00 L 17.90 21.47 L 13.04 13.04 ' +
  'L 21.47 17.90 Z'

function BrandMark({ size = 'md', inverse = false, title }) {
  return (
    <span
      className={`brand-mark brand-mark--${size} ${inverse ? 'brand-mark--inverse' : ''}`}
    >
      <svg
        viewBox="0 0 48 48"
        role={title ? 'img' : 'presentation'}
        aria-label={title}
        aria-hidden={title ? undefined : 'true'}
        focusable="false"
      >
        {/* the charger ring */}
        <circle className="brand-mark__ring" cx="24" cy="24" r="21" />
        {/* the star */}
        <path className="brand-mark__star" d={STAR} />
        {/* a small centre well, so the star reads as set into the plate */}
        <circle className="brand-mark__well" cx="24" cy="24" r="2.6" />
      </svg>
    </span>
  )
}

export default BrandMark
