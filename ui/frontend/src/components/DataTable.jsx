/**
 * A plain ruled table. Rules, not fills; alignment, not weight.
 *
 * columns: [{ key, header, align, render }]
 * rows:    array of objects
 * onRowClick: optional; when present rows become keyboard-reachable buttons.
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
                )}`}
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
                className={`border-b border-line align-top ${
                  interactive ? 'cursor-pointer hover:bg-line' : ''
                }`}
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
                    className={`py-sm pr-md text-ink ${alignClass(col.align)}`}
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
