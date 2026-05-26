import React, { useEffect, useState } from 'react'
import { useInvoiceStore } from '../stores/invoiceStore'
import SettingsModal from './SettingsModal'
import FolderScanModal from './FolderScanModal'
import TripItineraryReviewModal from './TripItineraryReviewModal'
import ImportProjectModal from './ImportProjectModal'
import { UnmatchedTripItinerary } from '../types/invoice'

type ScanResult = {
  total: number
  invoices: string[]
  trip_itineraries: string[]
  non_invoices: string[]
}

type ScanState =
  | { stage: 'idle' }
  | { stage: 'scanning'; folder: string }
  | { stage: 'ready'; folder: string; result: ScanResult }
  | { stage: 'error'; folder: string; error: string }
  | { stage: 'importing'; folder: string; result: ScanResult }

type ImportProgress = {
  phase: 'import' | 'ocr' | 'attachment' | 'done'
  done: number
  total: number
  imported: number
  skipped: number
  ocrProcessed: number
  ocrFailed: number
}

export default function TopBar(): React.JSX.Element {
  const {
    selectedIds,
    deleteSelected,
    loadInvoices,
    clearSelection,
    runOcrBatch,
    batchOcrProgress,
    projects,
    loadProjects,
    replaceProjectTagBatch
  } = useInvoiceStore()
  const [showSettings, setShowSettings] = useState(false)
  const [scanState, setScanState] = useState<ScanState>({ stage: 'idle' })
  const [showAdvancedActions, setShowAdvancedActions] = useState(false)
  const [importProgress, setImportProgress] = useState<ImportProgress | null>(null)
  const [unmatchedTripItems, setUnmatchedTripItems] = useState<UnmatchedTripItinerary[]>([])
  const [pendingImportPaths, setPendingImportPaths] = useState<string[] | null>(null)
  const [batchProjectTag, setBatchProjectTag] = useState('')
  const [batchReplaceProjectTag, setBatchReplaceProjectTag] = useState('')
  const [batchReplacingProject, setBatchReplacingProject] = useState(false)
  const [organizing, setOrganizing] = useState(false)

  useEffect(() => {
    if (selectedIds.size === 0) {
      setShowAdvancedActions(false)
      setBatchReplaceProjectTag('')
    }
  }, [selectedIds.size])

  useEffect(() => {
    const off = window.api.onImportProgress((progress) => {
      setImportProgress(progress)
    })
    return off
  }, [])

  async function handleImport(): Promise<void> {
    const paths = await window.api.selectPdfFiles()
    if (!paths.length) return
    setPendingImportPaths(paths)
  }

  async function startImport(paths: string[], projectTag: string | null): Promise<void> {
    setImportProgress({ phase: 'import', done: 0, total: paths.length, imported: 0, skipped: 0, ocrProcessed: 0, ocrFailed: 0 })
    try {
      const result = await window.api.importPdfs(paths, projectTag)
      await loadInvoices()
      alert(
        `导入完成：新增 ${result.imported} 张，跳过重复 ${result.skipped} 张\n` +
          `识别：成功 ${result.ocrProcessed} 张，失败 ${result.ocrFailed} 张`
      )
    } finally {
      setImportProgress(null)
      setPendingImportPaths(null)
    }
  }

  async function handleImportFolder(): Promise<void> {
    const folder = await window.api.selectFolder()
    if (!folder) return
    setBatchProjectTag('')
    setScanState({ stage: 'scanning', folder })
    try {
      const result = await window.api.scanFolder(folder, 'fast')
      setScanState({ stage: 'ready', folder, result })
    } catch (e) {
      setScanState({ stage: 'error', folder, error: e instanceof Error ? e.message : String(e) })
    }
  }

  async function handleScanConfirm(): Promise<void> {
    if (scanState.stage !== 'ready') return
    const { folder, result } = scanState
    setScanState({ stage: 'importing', folder, result })
    setImportProgress({
      phase: 'import',
      done: 0,
      total: result.invoices.length + result.trip_itineraries.length,
      imported: 0,
      skipped: 0,
      ocrProcessed: 0,
      ocrFailed: 0
    })
    try {
      const importResult = await window.api.importBatchFiles(
        result.invoices,
        result.trip_itineraries,
        batchProjectTag || null
      )
      await loadInvoices()
      setScanState({ stage: 'idle' })
      setBatchProjectTag('')
      setUnmatchedTripItems((importResult.unmatchedDetails || []) as UnmatchedTripItinerary[])
      alert(
        `导入完成：新增 ${importResult.imported} 张，跳过重复 ${importResult.skipped} 张\n` +
          `识别：成功 ${importResult.ocrProcessed} 张，失败 ${importResult.ocrFailed} 张\n` +
          `行程单绑定：成功 ${importResult.attachmentImported} 份，重复 ${importResult.attachmentSkipped} 份，未匹配 ${importResult.attachmentUnmatched} 份，失败 ${importResult.attachmentFailed} 份`
      )
    } catch (e) {
      setScanState({ stage: 'error', folder, error: e instanceof Error ? e.message : String(e) })
    } finally {
      setImportProgress(null)
    }
  }

  async function handleScanCancel(): Promise<void> {
    if (scanState.stage === 'scanning') {
      try {
        await window.api.cancelScan()
      } catch {
        // close modal even when the scanner has already exited
      }
    }
    setBatchProjectTag('')
    setScanState({ stage: 'idle' })
  }

  async function handleDelete(): Promise<void> {
    if (!selectedIds.size) return
    if (!confirm(`确认删除选中的 ${selectedIds.size} 张发票？此操作不可撤销。`)) return
    await deleteSelected()
  }

  async function handleBindUnmatchedTrip(filePath: string, invoiceId: string): Promise<void> {
    const result = await window.api.importInvoiceAttachments(invoiceId, [filePath])
    await loadInvoices()
    if (result.imported === 0 && result.skipped > 0) {
      alert('这份行程单已绑定或已存在，已跳过重复导入。')
    }
  }

  async function handleCreateProject(name: string, color: string): Promise<void> {
    await window.api.createProject(name, color)
    await loadProjects()
  }

  async function handleBatchReplaceProjectTag(): Promise<void> {
    if (!selectedIds.size) return
    setBatchReplacingProject(true)
    try {
      await replaceProjectTagBatch(batchReplaceProjectTag || null)
    } finally {
      setBatchReplacingProject(false)
    }
  }

  async function handleOrganizeInvoices(): Promise<void> {
    setOrganizing(true)
    try {
      const result = await window.api.organizeInvoiceFiles()
      if (result.success) {
        alert(
          `整理完成：主发票 ${result.copied || 0} 个，行程单 ${result.attachmentCopied || 0} 个，跳过 ${result.skipped || 0} 个\n` +
            `目录：${result.path}`
        )
      } else if (result.error !== '已取消') {
        alert(`整理失败：${result.error}`)
      }
    } finally {
      setOrganizing(false)
    }
  }

  const importLabel = importProgress?.phase === 'import'
    ? '导入中'
    : importProgress?.phase === 'ocr'
      ? '识别中'
      : '绑定行程单'

  return (
    <>
      <div
        className="flex items-center gap-2 px-4 py-2 bg-white border-b border-gray-200 select-none"
        style={{ WebkitAppRegion: 'drag' } as React.CSSProperties}
      >
        <div className="flex items-center gap-1" style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}>
          <button
            onClick={handleImport}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 text-white text-sm rounded-md hover:bg-blue-700 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
            导入发票
          </button>

          <button
            onClick={handleImportFolder}
            disabled={scanState.stage === 'scanning' || scanState.stage === 'importing'}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-white text-gray-700 text-sm border border-gray-300 rounded-md hover:bg-gray-50 transition-colors disabled:opacity-50"
          >
            {scanState.stage === 'scanning' ? (
              <div className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
            )}
            批量导入
          </button>

          {batchOcrProgress && (
            <>
              <div className="w-px h-5 bg-gray-300 mx-1" />
              <div className="flex items-center gap-2 px-3 py-1.5 bg-purple-50 border border-purple-200 rounded-md">
                <div className="w-3.5 h-3.5 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
                <span className="text-sm text-purple-700">
                  重新识别中 {batchOcrProgress.done}/{batchOcrProgress.total}
                </span>
              </div>
            </>
          )}

          {importProgress && importProgress.phase !== 'done' && !batchOcrProgress && (
            <>
              <div className="w-px h-5 bg-gray-300 mx-1" />
              <div className="flex items-center gap-2 px-3 py-1.5 bg-blue-50 border border-blue-200 rounded-md">
                <div className="w-3.5 h-3.5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                <span className="text-sm text-blue-700">
                  {importLabel} {importProgress.done}/{importProgress.total}
                </span>
              </div>
            </>
          )}

          {selectedIds.size > 0 && !batchOcrProgress && (
            <>
              <div className="w-px h-5 bg-gray-300 mx-1" />
              <span className="text-sm text-gray-500">已选 {selectedIds.size} 张</span>
              <button
                onClick={() => setShowAdvancedActions((value) => !value)}
                className="px-2 py-1.5 text-gray-500 text-sm hover:text-gray-700"
              >
                {showAdvancedActions ? '收起高级' : '高级'}
              </button>
              {showAdvancedActions && (
                <>
                  <button
                    onClick={runOcrBatch}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-600 text-white text-sm rounded-md hover:bg-purple-700 transition-colors"
                  >
                    重新识别
                  </button>
                  <select
                    value={batchReplaceProjectTag}
                    onChange={(e) => setBatchReplaceProjectTag(e.target.value)}
                    className="text-sm border border-gray-300 rounded-md px-3 py-1.5 bg-white text-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">清空项目绑定</option>
                    {projects.map((project) => (
                      <option key={project.id} value={project.name}>{project.name}</option>
                    ))}
                  </select>
                  <button
                    onClick={() => void handleBatchReplaceProjectTag()}
                    disabled={batchReplacingProject}
                    className="px-3 py-1.5 bg-slate-700 text-white text-sm rounded-md hover:bg-slate-800 transition-colors disabled:opacity-50"
                  >
                    {batchReplacingProject ? '替换中...' : '批量替换项目'}
                  </button>
                </>
              )}
              <button
                onClick={handleDelete}
                className="flex items-center gap-1 px-3 py-1.5 bg-red-50 text-red-600 text-sm border border-red-200 rounded-md hover:bg-red-100 transition-colors"
              >
                删除
              </button>
              <button
                onClick={clearSelection}
                className="px-2 py-1.5 text-gray-500 text-sm hover:text-gray-700"
              >
                取消
              </button>
            </>
          )}
        </div>

        <div className="flex-1" />

        <div className="flex items-center gap-1" style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}>
          <button
            onClick={handleOrganizeInvoices}
            disabled={organizing}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-green-600 text-white text-sm rounded-md hover:bg-green-700 transition-colors disabled:opacity-50"
          >
            {organizing ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
            )}
            {organizing ? '整理中...' : '整理发票'}
          </button>

          <button
            onClick={() => setShowSettings(true)}
            className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
        </div>
      </div>

      {showSettings && <SettingsModal onClose={() => setShowSettings(false)} />}
      {pendingImportPaths && (
        <ImportProjectModal
          count={pendingImportPaths.length}
          projects={projects}
          onCreateProject={handleCreateProject}
          onClose={() => setPendingImportPaths(null)}
          onConfirm={(projectTag) => {
            void startImport(pendingImportPaths, projectTag)
          }}
        />
      )}
      {unmatchedTripItems.length > 0 && (
        <TripItineraryReviewModal
          items={unmatchedTripItems}
          onBind={handleBindUnmatchedTrip}
          onClose={() => setUnmatchedTripItems([])}
        />
      )}
      {(scanState.stage === 'scanning' || scanState.stage === 'ready' || scanState.stage === 'error' || scanState.stage === 'importing') && (
        <FolderScanModal
          folderPath={scanState.folder}
          scanning={scanState.stage === 'scanning'}
          importing={scanState.stage === 'importing'}
          importProgress={importProgress}
          result={scanState.stage === 'ready' || scanState.stage === 'importing' ? scanState.result : null}
          error={scanState.stage === 'error' ? scanState.error : null}
          projects={projects}
          selectedProjectTag={batchProjectTag}
          onProjectChange={setBatchProjectTag}
          onCreateProject={handleCreateProject}
          onConfirm={handleScanConfirm}
          onCancel={handleScanCancel}
        />
      )}
    </>
  )
}
