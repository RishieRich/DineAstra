import fs from 'node:fs/promises'
import { fileURLToPath } from 'node:url'
import { SpreadsheetFile, Workbook } from '@oai/artifact-tool'

const outputDir = new URL('../../outputs/dineastra-demo/', import.meta.url)
const publicDir = new URL('../../ui/frontend/public/samples/', import.meta.url)

await fs.mkdir(outputDir, { recursive: true })
await fs.mkdir(publicDir, { recursive: true })

const workbook = Workbook.create()
const sheet = workbook.worksheets.add('Daily Operations')
sheet.showGridLines = false
sheet.tabColor = '#651D37'

sheet.getRange('A2:I2').merge()
sheet.getRange('A2').values = [['DineAstra daily operations upload']]
sheet.getRange('A3:I3').merge()
sheet.getRange('A3').values = [[
  'Add one row per outlet and business date. Keep the column names unchanged, then upload this workbook in Data Studio.',
]]
sheet.getRange('A5:I5').merge()
sheet.getRange('A5').values = [['Required fields are marked in gold. Percentages are entered as whole values, such as 31.5.']]

sheet.getRange('A7:I11').values = [
  ['date', 'outlet', 'net_sales', 'covers', 'food_cost_pct', 'labour_cost_pct', 'checklist_total', 'checklist_signed_off', 'notes'],
  [new Date(Date.UTC(2026, 8, 15)), 'Astra House - Bengaluru', 487500, 612, 31.8, 24.6, 34, 34, 'Dinner demand above plan'],
  [new Date(Date.UTC(2026, 8, 16)), 'Astra House - Bengaluru', 452800, 571, 32.4, 25.1, 34, 33, 'One closing check pending'],
  [new Date(Date.UTC(2026, 8, 15)), 'Astra Terrace - Indiranagar', 328400, 398, 30.9, 26.2, 28, 28, 'Terrace event included'],
  [new Date(Date.UTC(2026, 8, 16)), 'Astra Terrace - Indiranagar', 301600, 362, 31.4, 26.8, 28, 27, 'Bar checklist follow-up'],
]

sheet.getRange('K2:N2').merge()
sheet.getRange('K2').values = [['How the import works']]
sheet.getRange('K3:N7').values = [
  ['Step', 'What to do', 'Required', 'Example'],
  ['1', 'Keep one row per outlet and date', 'Yes', '2026-09-16'],
  ['2', 'Use numeric values without currency symbols', 'Yes', '452800'],
  ['3', 'Reuse the same date and outlet to create a new version', 'Optional', 'Updated sales'],
  ['4', 'Upload through Data Studio', 'Yes', 'Excel, CSV or TXT'],
]

sheet.getRange('A2:I2').format = {
  font: { name: 'Arial', size: 16, bold: true, color: '#21171B' },
  verticalAlignment: 'center',
}
sheet.getRange('A3:I3').format = {
  font: { name: 'Arial', size: 10, color: '#756970' },
  verticalAlignment: 'center',
}
sheet.getRange('A5:I5').format = {
  fill: '#F3E8ED',
  font: { name: 'Arial', size: 10, italic: true, color: '#651D37' },
  verticalAlignment: 'center',
}
sheet.getRange('A7:I7').format = {
  fill: '#2B0B1D',
  font: { name: 'Arial', size: 10, bold: true, color: '#FFFFFF' },
  horizontalAlignment: 'center',
  verticalAlignment: 'center',
  borders: { preset: 'inside', style: 'thin', color: '#FFFFFF' },
}
sheet.getRange('A8:H11').format.fill = '#FFF2D8'
sheet.getRange('I8:I11').format.fill = '#FBF8F4'
sheet.getRange('A8:I11').format.font = { name: 'Arial', size: 10, color: '#21171B' }
sheet.getRange('A8:I11').format.verticalAlignment = 'center'
sheet.getRange('A8:I11').format.borders = {
  insideHorizontal: { style: 'thin', color: '#E8DED7' },
  bottom: { style: 'thin', color: '#E8DED7' },
}
sheet.getRange('A8:A11').format.numberFormat = 'yyyy-mm-dd'
sheet.getRange('C8:C11').format.numberFormat = '#,##0'
sheet.getRange('D8:D11').format.numberFormat = '#,##0'
sheet.getRange('E8:F11').format.numberFormat = '0.0'
sheet.getRange('G8:H11').format.numberFormat = '#,##0'

sheet.getRange('K2:N2').format = {
  fill: '#651D37',
  font: { name: 'Arial', size: 11, bold: true, color: '#F1D88A' },
  verticalAlignment: 'center',
}
sheet.getRange('K3:N3').format = {
  fill: '#EAD9AF',
  font: { name: 'Arial', size: 10, bold: true, color: '#2B0B1D' },
  horizontalAlignment: 'center',
  verticalAlignment: 'center',
}
sheet.getRange('K4:N7').format.font = { name: 'Arial', size: 10, color: '#21171B' }
sheet.getRange('K4:N7').format.verticalAlignment = 'center'
sheet.getRange('K3:N7').format.borders = {
  insideHorizontal: { style: 'thin', color: '#E8DED7' },
  bottom: { style: 'thin', color: '#E8DED7' },
}

sheet.getRange('A2:N11').format.font.name = 'Arial'
sheet.getRange('A2:N11').format.wrapText = false
sheet.getRange('A2:N11').format.rowHeight = 24
sheet.getRange('A2:I2').format.rowHeight = 30
sheet.getRange('A3:I3').format.rowHeight = 26
sheet.getRange('A5:I5').format.rowHeight = 28
sheet.getRange('A:A').format.columnWidth = 13
sheet.getRange('B:B').format.columnWidth = 28
sheet.getRange('C:C').format.columnWidth = 15
sheet.getRange('D:D').format.columnWidth = 11
sheet.getRange('E:F').format.columnWidth = 17
sheet.getRange('G:H').format.columnWidth = 19
sheet.getRange('I:I').format.columnWidth = 28
sheet.getRange('J:J').format.columnWidth = 3
sheet.getRange('K:K').format.columnWidth = 8
sheet.getRange('L:L').format.columnWidth = 31
sheet.getRange('M:M').format.columnWidth = 11
sheet.getRange('N:N').format.columnWidth = 18
sheet.freezePanes.freezeRows(7)

sheet.getRange('E8:F1000').dataValidation = {
  rule: { type: 'decimal', operator: 'between', formula1: 0, formula2: 100 },
}
sheet.getRange('C8:H1000').conditionalFormats.addCustom('=AND(C8<>"",NOT(ISNUMBER(C8)))', {
  fill: '#FAE9E9',
  font: { bold: true, color: '#A63E43' },
})

const table = sheet.tables.add('A7:I11', true, 'DailyOperationsUpload')
table.style = 'TableStyleMedium2'
table.showBandedColumns = false
table.showFilterButton = true

workbook.recalculate()

const inspect = await workbook.inspect({
  kind: 'table',
  range: 'Daily Operations!A2:N11',
  include: 'values,formulas',
  tableMaxRows: 12,
  tableMaxCols: 14,
})
console.log(inspect.ndjson)

const errors = await workbook.inspect({
  kind: 'match',
  searchTerm: '#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',
  options: { useRegex: true, maxResults: 100 },
  summary: 'final formula error scan',
})
console.log(errors.ndjson)

const preview = await workbook.render({
  sheetName: 'Daily Operations',
  range: 'A1:N12',
  scale: 1.5,
  format: 'png',
})
await fs.writeFile(new URL('dineastra_daily_operations_template.png', outputDir), new Uint8Array(await preview.arrayBuffer()))

const xlsx = await SpreadsheetFile.exportXlsx(workbook)
const finalPath = fileURLToPath(new URL('dineastra_daily_operations_template.xlsx', outputDir))
const publicPath = fileURLToPath(new URL('dineastra_daily_operations_template.xlsx', publicDir))
await xlsx.save(finalPath)
await fs.copyFile(finalPath, publicPath)
console.log(`saved ${finalPath}`)
