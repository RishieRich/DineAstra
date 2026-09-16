/**
 * A plain ruled table. Rules, not fills; alignment, not weight.
 *
 * columns: [{ key, header, align, render, nowrap }]
 * rows:    array of objects
 * onRowClick: optional; when present rows become keyboard-reachable buttons.
 *
 * nowrap keeps short values -- references, dates, figures -- on one line, so
 * on a narrow screen the table scrolls sideways instead of squeezing an event
 * reference into three stacked lines.
 */
function DataTable({ columns, rows, onRowClick, getRowKey, emptyMessage }) {
  if (!rows || rows.length === 0) {
    return (
      <p className="py-lg text-sm text-muted">
        {emptyMessage || 'Nothing to show for this selection.'}
      </p>
    )
  }

  const alignClass = (align) =>
    align === 'right' ? 'text-right' : align === 'center' ? 'text-center' : 'text-left'

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-line">
            {columns.map((col) => (
              <th
                key={col.key}
                scope="col"
                className={`py-sm pr-md text-xs font-medium tracking-[0.12em] text-muted ${alignClass(
                  col.align,
                )} ${col.nowrap ? 'whitespace-nowrap' : ''}`}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => {
            const key = getRowKey ? getRowKey(row, rowIndex) : rowIndex
            const interactive = Boolean(onRowClick)
            return (
              <tr
                key={key}
                className="border-b border-line align-top"
                data-interactive={interactive ? 'true' : undefined}
                onClick={interactive ? () => onRowClick(row) : undefined}
                onKeyDown={
                  interactive
                    ? (event) => {
                        if (event.key === 'Enter' || event.key === ' ') {
                          event.preventDefault()
                          onRowClick(row)
                        }
                      }
                    : undefined
                }
                tabIndex={interactive ? 0 : undefined}
                role={interactive ? 'button' : undefined}
              >
                {columns.map((col) => (
                  <td
                    key={col.key}
                    className={`py-sm pr-md text-ink ${alignClass(col.align)} ${
                      col.nowrap ? 'whitespace-nowrap' : ''
                    }`}
                  >
                    {col.render ? col.render(row) : row[col.key]}
                  </td>
                ))}
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

export default DataTable
