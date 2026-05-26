import { dialog } from 'electron'
import path from 'path'
import fs from 'fs'
import { getDb } from './dbHandler'

interface Invoice {
  id: string
  vendor: string | null
  amount: number | null
  total: number | null
  category: string | null
  file_path: string
}

interface InvoiceAttachment {
  invoice_id: string
  file_path: string
}

interface OrganizeResult {
  success: boolean
  path?: string
  copied?: number
  attachmentCopied?: number
  skipped?: number
  error?: string
}

const ORGANIZED_FOLDER_NAME = '整理发票'
const RESERVED_WINDOWS_NAMES = /^(con|prn|aux|nul|com[1-9]|lpt[1-9])$/i

function getInvoices(): Invoice[] {
  const db = getDb()
  const result = db.exec(
    `SELECT id, vendor, amount, total, category, file_path
     FROM invoices
     ORDER BY category ASC, date ASC, created_at ASC`
  )
  if (!result.length || !result[0].values.length) return []

  return result[0].values.map((row) => ({
    id: row[0] as string,
    vendor: row[1] as string | null,
    amount: row[2] as number | null,
    total: row[3] as number | null,
    category: row[4] as string | null,
    file_path: row[5] as string
  }))
}

function getAttachmentsByInvoiceIds(invoiceIds: string[]): Map<string, InvoiceAttachment[]> {
  if (!invoiceIds.length) return new Map()

  const db = getDb()
  const ids = invoiceIds.map((id) => `'${id.replace(/'/g, "''")}'`).join(',')
  const result = db.exec(
    `SELECT invoice_id, file_path
     FROM invoice_attachments
     WHERE invoice_id IN (${ids})
     ORDER BY created_at ASC`
  )

  const map = new Map<string, InvoiceAttachment[]>()
  if (!result.length || !result[0].values.length) return map

  result[0].values.forEach((row) => {
    const attachment: InvoiceAttachment = {
      invoice_id: row[0] as string,
      file_path: row[1] as string
    }
    const list = map.get(attachment.invoice_id) || []
    list.push(attachment)
    map.set(attachment.invoice_id, list)
  })

  return map
}

function sanitizePathPart(value: string, fallback: string): string {
  const cleaned = value
    .replace(/[\x00-\x1f<>:"/\\|?*]/g, '_')
    .replace(/\s+/g, ' ')
    .replace(/[. ]+$/g, '')
    .trim()
    .slice(0, 120)

  if (!cleaned || RESERVED_WINDOWS_NAMES.test(cleaned)) return fallback
  return cleaned
}

function formatAmount(invoice: Invoice): string {
  const amount = invoice.total ?? invoice.amount
  return typeof amount === 'number' && Number.isFinite(amount)
    ? `${amount.toFixed(2)}元`
    : '未知金额'
}

function getFileExtension(filePath: string): string {
  return path.extname(filePath).toLowerCase() || '.pdf'
}

function getUniqueDestination(dir: string, stem: string, ext: string, usedNames: Set<string>): string {
  let index = 1
  let fileName = `${stem}${ext}`

  while (usedNames.has(fileName.toLowerCase()) || fs.existsSync(path.join(dir, fileName))) {
    index += 1
    fileName = `${stem}_${index}${ext}`
  }

  usedNames.add(fileName.toLowerCase())
  return path.join(dir, fileName)
}

function assertSafeOrganizedRoot(parentDir: string, organizedRoot: string): void {
  const resolvedParent = path.resolve(parentDir)
  const resolvedRoot = path.resolve(organizedRoot)
  if (path.dirname(resolvedRoot) !== resolvedParent || path.basename(resolvedRoot) !== ORGANIZED_FOLDER_NAME) {
    throw new Error('整理目录校验失败，已取消操作')
  }
}

export async function organizeInvoiceFiles(): Promise<OrganizeResult> {
  const selection = await dialog.showOpenDialog({
    properties: ['openDirectory'],
    title: '选择整理发票的保存目录'
  })
  const parentDir = selection.filePaths[0]
  if (selection.canceled || !parentDir) return { success: false, error: '已取消' }

  try {
    const organizedRoot = path.resolve(parentDir, ORGANIZED_FOLDER_NAME)
    assertSafeOrganizedRoot(parentDir, organizedRoot)

    fs.rmSync(organizedRoot, { recursive: true, force: true })
    fs.mkdirSync(organizedRoot, { recursive: true })

    const invoices = getInvoices()
    const attachmentsByInvoice = getAttachmentsByInvoiceIds(invoices.map((invoice) => invoice.id))
    const usedNamesByDir = new Map<string, Set<string>>()
    let copied = 0
    let attachmentCopied = 0
    let skipped = 0

    for (const invoice of invoices) {
      const category = sanitizePathPart(invoice.category || '未分类', '未分类')
      const categoryDir = path.join(organizedRoot, category)
      fs.mkdirSync(categoryDir, { recursive: true })

      const usedNames = usedNamesByDir.get(categoryDir) || new Set<string>()
      usedNamesByDir.set(categoryDir, usedNames)

      const vendor = sanitizePathPart(invoice.vendor || '未知商家', '未知商家')
      const amount = sanitizePathPart(formatAmount(invoice), '未知金额')
      const stem = `${vendor}_${amount}`

      if (fs.existsSync(invoice.file_path)) {
        const dest = getUniqueDestination(categoryDir, stem, getFileExtension(invoice.file_path), usedNames)
        fs.copyFileSync(invoice.file_path, dest)
        copied += 1
      } else {
        skipped += 1
      }

      const attachments = attachmentsByInvoice.get(invoice.id) || []
      attachments.forEach((attachment, index) => {
        if (!fs.existsSync(attachment.file_path)) {
          skipped += 1
          return
        }

        const attachmentStem = `${stem}_行程单_${index + 1}`
        const dest = getUniqueDestination(
          categoryDir,
          attachmentStem,
          getFileExtension(attachment.file_path),
          usedNames
        )
        fs.copyFileSync(attachment.file_path, dest)
        attachmentCopied += 1
      })
    }

    return {
      success: true,
      path: organizedRoot,
      copied,
      attachmentCopied,
      skipped
    }
  } catch (err) {
    return { success: false, error: err instanceof Error ? err.message : String(err) }
  }
}
