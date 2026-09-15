function BrandMark({ size = 'md', inverse = false }) {
  return (
    <span
      className={`brand-mark brand-mark--${size} ${inverse ? 'brand-mark--inverse' : ''}`}
      aria-hidden="true"
    >
      <span>DA</span>
    </span>
  )
}

export default BrandMark
