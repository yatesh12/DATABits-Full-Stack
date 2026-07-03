import type React from "react"
import { useState, useEffect, useCallback } from "react"
import { LeftSidebar } from "./Left-sidebar.tsx"
import { MainContent } from "./Main-content.tsx"
import { RightSidebar } from "./Right-sidebar.tsx"
import { TopNavbar } from "./Top-navbar.tsx"
import { LoadingOverlay } from "../components/ui/loading-overlay.tsx"
import { useApi } from "../hooks/use-api.ts"
import { toast } from "sonner"

export type LogEntry = {
  title: string
  date: string
  details: string
  type?: "info" | "warning" | "error"
}

interface ProcessingStatus {
  status: "idle" | "processing" | "completed" | "error"
  progress: number
  message: string
}

export function DataPreprocessingApp() {
  const [datasetId, setDatasetId] = useState<string | null>(null)
  const [fileName, setFileName] = useState<string>("")
  const [tableData, setTableData] = useState<any[]>([])
  const [activeTab, setActiveTab] = useState<"Head" | "Tail" | "Random Sample">("Head")
  const [technique, setTechnique] = useState({
    column: "No data loaded",
    count: "0",
    missing: "0",
    mean: "0",
    categories: "0",
  })
  const [analysisMode, setAnalysisMode] = useState<
    "overview" | "visualization" | "summary" | "correlation" | "missing-values" | "normalization"
  >("overview")
  const [summaryData, setSummaryData] = useState<any>(null)
  const [correlationData, setCorrelationData] = useState<any>(null)
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [processingStatus, setProcessingStatus] = useState<ProcessingStatus>({
    status: "idle",
    progress: 0,
    message: "",
  })

  // Add ref to prevent multiple API calls
  const [isLoading, setIsLoading] = useState(false)
  const [lastActiveTab, setLastActiveTab] = useState<string>("")

  const api = useApi()

  const addLog = useCallback((log: LogEntry) => {
    setLogs((prev) => [log, ...prev.slice(0, 49)]) // Keep only last 50 logs
  }, [])

  const updateDataFromSummary = useCallback((summary: any) => {
    if (!summary) return

    const columns = summary.columns || []
    const missingValues = summary.missing_values || {}
    const totalMissing = Object.values(missingValues).reduce((sum: number, val: any) => sum + val, 0)

    // Calculate stats for technique panel
    const categoricalColumns = Object.entries(summary.dtypes || {}).filter(([_, dtype]) =>
      (dtype as string).includes("object"),
    ).length

    // Calculate mean for first numeric column
    let meanValue = "0"
    if (summary.numerical_stats) {
      const firstNumericCol = Object.keys(summary.numerical_stats)[0]
      if (firstNumericCol && summary.numerical_stats[firstNumericCol]?.mean) {
        meanValue = summary.numerical_stats[firstNumericCol].mean.toFixed(2)
      }
    }

    setTechnique({
      column: columns.length > 0 ? `${columns[0]} / ${columns.length}` : "No columns",
      count: summary.shape?.[0]?.toLocaleString() || "0",
      missing: totalMissing.toLocaleString(),
      mean: meanValue,
      categories: categoricalColumns.toString(),
    })
  }, [])

  const refreshPreviewData = useCallback(async () => {
    if (!datasetId || isLoading) return

    // Prevent multiple calls for the same tab
    if (lastActiveTab === activeTab) return

    try {
      setIsLoading(true)
      setLastActiveTab(activeTab)

      // Fix the view type mapping
      let viewType = activeTab.toLowerCase()
      if (viewType === "random sample") {
        viewType = "random" // Use 'random' instead of 'randomsample'
      }

      console.log(`Loading ${viewType} data for dataset ${datasetId}`)

      const previewData = await api.getDatasetPreview(datasetId, 1, 10, viewType) as { data?: any[] }
      setTableData(previewData.data || [])

      // Log the action
      addLog({
        title: `${activeTab} Data Loaded`,
        date: new Date().toLocaleString(),
        details: `Loaded ${previewData.data?.length || 0} rows for ${activeTab} view`,
        type: "info",
      })
    } catch (error) {
      console.error("Error refreshing preview:", error)
      toast.error("Failed to load preview data")
    } finally {
      setIsLoading(false)
    }
  }, [datasetId, activeTab, api, addLog, isLoading, lastActiveTab])

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Reset state
    setDatasetId(null)
    setTableData([])
    setSummaryData(null)
    setCorrelationData(null)
    setAnalysisMode("overview")
    setActiveTab("Head")
    setLastActiveTab("")

    try {
      setProcessingStatus({ status: "processing", progress: 0, message: "Uploading file..." })

      const result = await api.uploadFile(file, (progress) => {
        setProcessingStatus({ status: "processing", progress, message: "Uploading file..." })
      })

      setDatasetId(result.dataset_id)
      setFileName(result.filename)
      setTableData(result.sample_data || [])

      updateDataFromSummary(result.summary)

      setProcessingStatus({ status: "completed", progress: 100, message: "File uploaded successfully" })

      addLog({
        title: "File Uploaded",
        date: new Date().toLocaleString(),
        details: `File "${result.filename}" uploaded successfully. ${result.summary?.shape?.[0] || 0} rows loaded.`,
        type: "info",
      })

      toast.success("File uploaded successfully!")

      // Reset processing status after a delay
      setTimeout(() => {
        setProcessingStatus({ status: "idle", progress: 0, message: "" })
      }, 2000)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Upload failed"

      setProcessingStatus({ status: "error", progress: 0, message: errorMessage })

      addLog({
        title: "Upload Error",
        date: new Date().toLocaleString(),
        details: errorMessage,
        type: "error",
      })

      toast.error(errorMessage)

      // Reset processing status after a delay
      setTimeout(() => {
        setProcessingStatus({ status: "idle", progress: 0, message: "" })
      }, 3000)
    }
  }

  const handleProcessingOperation = async (
    operation: () => Promise<any>,
    operationName: string,
    successMessage: string,
  ) => {
    if (!datasetId) {
      toast.error("No dataset loaded")
      return
    }

    try {
      setProcessingStatus({ status: "processing", progress: 0, message: `Starting ${operationName}...` })

      // Start polling for status updates
      api.pollStatus(datasetId, (status) => {
        setProcessingStatus({
          ...status,
          message: status.message ?? ""
        })
      })

      const result = await operation()

      if (result.summary) {
        updateDataFromSummary(result.summary)
      }

      // Reset tab tracking to force refresh
      setLastActiveTab("")

      // Refresh preview data
      await refreshPreviewData()

      addLog({
        title: operationName,
        date: new Date().toLocaleString(),
        details: result.message || successMessage,
        type: "info",
      })

      toast.success(successMessage)

      setProcessingStatus({ status: "completed", progress: 100, message: successMessage })

      // Reset processing status after a delay
      setTimeout(() => {
        setProcessingStatus({ status: "idle", progress: 0, message: "" })
      }, 2000)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : `${operationName} failed`

      setProcessingStatus({ status: "error", progress: 0, message: errorMessage })

      addLog({
        title: `${operationName} Error`,
        date: new Date().toLocaleString(),
        details: errorMessage,
        type: "error",
      })

      toast.error(errorMessage)

      // Reset processing status after a delay
      setTimeout(() => {
        setProcessingStatus({ status: "idle", progress: 0, message: "" })
      }, 3000)
    }
  }

  const handleImputeMissingValues = () => {
    handleProcessingOperation(
      () => api.handleMissingValues(datasetId!, "mean"),
      "Missing Values Imputation",
      "Missing values handled successfully!",
    )
  }

  const handleVisualizationClick = () => {
    if (!datasetId) {
      toast.error("No dataset loaded")
      return
    }

    setAnalysisMode("visualization")
    addLog({
      title: "Visualization Mode",
      date: new Date().toLocaleString(),
      details: "Switched to advanced visualization mode.",
      type: "info",
    })
  }

  const handleDataSummaryClick = async () => {
    if (!datasetId) {
      toast.error("No dataset loaded")
      return
    }

    try {
      setProcessingStatus({ status: "processing", progress: 50, message: "Generating data summary..." })

      const summaryRaw = await api.getDatasetSummary(datasetId)
      // Add a type assertion to ensure summary is typed
      const summary = summaryRaw as {
        shape?: [number, number]
        memory_usage?: string
        columns?: string[]
        dtypes?: { [key: string]: string }
        missing_values?: { [key: string]: number }
        numerical_stats?: { [key: string]: any }
        categorical_stats?: { [key: string]: { top_values?: { [key: string]: number } } }
      }

      // Transform backend summary to frontend format
      const transformedSummary = {
        overview: {
          totalRows: summary.shape?.[0] || 0,
          totalColumns: summary.shape?.[1] || 0,
          memoryUsage: summary.memory_usage || "0 KB",
        },
        columns:
          summary.columns?.map((colName: string) => {
            const dtype = summary.dtypes?.[colName] || "object"
            const missingCount = summary.missing_values?.[colName] || 0
            const isNumeric = dtype.includes("int") || dtype.includes("float")

            let stats: any = {
              count: (summary.shape?.[0] || 0) - missingCount,
              missing: missingCount,
              missingPercentage: ((missingCount / (summary.shape?.[0] || 1)) * 100).toFixed(1),
              unique: 0,
              uniquePercentage: "0",
            }

            if (isNumeric && summary.numerical_stats?.[colName]) {
              const numStats = summary.numerical_stats[colName]
              stats = {
                ...stats,
                mean: numStats.mean?.toFixed(2) || "0",
                median: numStats["50%"]?.toFixed(2) || "0",
                std: numStats.std?.toFixed(2) || "0",
                min: numStats.min?.toFixed(2) || "0",
                max: numStats.max?.toFixed(2) || "0",
                q25: numStats["25%"]?.toFixed(2) || "0",
                q75: numStats["75%"]?.toFixed(2) || "0",
              }
            } else if (summary.categorical_stats?.[colName]) {
              const catStats = summary.categorical_stats[colName]
              stats.topValues = Object.entries(catStats.top_values || {}).map(([value, count]) => ({
                value,
                count,
                percentage: (((count as number) / (summary.shape?.[0] || 1)) * 100).toFixed(1),
              }))
            }

            return {
              name: colName,
              dataType: isNumeric ? "numeric" : "categorical",
              isNumeric,
              isBoolean: false,
              isDate: false,
              stats,
              sampleValues: [],
            }
          }) || [],
      }

      setSummaryData(transformedSummary)
      setAnalysisMode("summary")

      setProcessingStatus({ status: "completed", progress: 100, message: "Data summary generated!" })

      addLog({
        title: "Data Summary Generated",
        date: new Date().toLocaleString(),
        details: `Generated comprehensive summary for ${summary.shape?.[0] || 0} rows and ${summary.shape?.[1] || 0} columns.`,
        type: "info",
      })

      toast.success("Data summary generated!")

      // Reset processing status after a delay
      setTimeout(() => {
        setProcessingStatus({ status: "idle", progress: 0, message: "" })
      }, 2000)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Summary generation failed"

      setProcessingStatus({ status: "error", progress: 0, message: errorMessage })

      addLog({
        title: "Summary Error",
        date: new Date().toLocaleString(),
        details: errorMessage,
        type: "error",
      })

      toast.error(errorMessage)

      // Reset processing status after a delay
      setTimeout(() => {
        setProcessingStatus({ status: "idle", progress: 0, message: "" })
      }, 3000)
    }
  }

  const handleCorrelationAnalysisClick = async () => {
    if (!datasetId) {
      toast.error("No dataset loaded")
      return
    }

    try {
      setProcessingStatus({ status: "processing", progress: 50, message: "Analyzing correlations..." })

      const correlationRaw = await api.getCorrelationAnalysis(datasetId)
      const correlation = correlationRaw as { numericalColumns?: any[] }
      setCorrelationData(correlation)
      setAnalysisMode("correlation")

      setProcessingStatus({ status: "completed", progress: 100, message: "Correlation analysis completed!" })

      addLog({
        title: "Correlation Analysis Complete",
        date: new Date().toLocaleString(),
        details: `Analyzed correlations between ${correlation.numericalColumns?.length || 0} numerical variables.`,
        type: "info",
      })

      toast.success("Correlation analysis completed!")

      // Reset processing status after a delay
      setTimeout(() => {
        setProcessingStatus({ status: "idle", progress: 0, message: "" })
      }, 2000)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Correlation analysis failed"

      setProcessingStatus({ status: "error", progress: 0, message: errorMessage })

      addLog({
        title: "Correlation Error",
        date: new Date().toLocaleString(),
        details: errorMessage,
        type: "error",
      })

      toast.error(errorMessage)

      // Reset processing status after a delay
      setTimeout(() => {
        setProcessingStatus({ status: "idle", progress: 0, message: "" })
      }, 3000)
    }
  }

  const handleBackToOverview = () => {
    setAnalysisMode("overview")
    addLog({
      title: "Overview Mode",
      date: new Date().toLocaleString(),
      details: "Returned to data overview mode.",
      type: "info",
    })
  }

  const handleExportFile = async () => {
    if (!datasetId) {
      toast.error("No dataset loaded")
      return
    }

    try {
      setProcessingStatus({ status: "processing", progress: 50, message: "Preparing export..." })

      const blob = await api.exportDataset(datasetId)

      // Create download link
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `processed_${fileName || "data"}.csv`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)

      setProcessingStatus({ status: "completed", progress: 100, message: "File exported successfully!" })

      addLog({
        title: "File Exported",
        date: new Date().toLocaleString(),
        details: `Processed data exported successfully as processed_${fileName || "data"}.csv`,
        type: "info",
      })

      toast.success("File exported successfully!")

      // Reset processing status after a delay
      setTimeout(() => {
        setProcessingStatus({ status: "idle", progress: 0, message: "" })
      }, 2000)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Export failed"

      setProcessingStatus({ status: "error", progress: 0, message: errorMessage })

      addLog({
        title: "Export Error",
        date: new Date().toLocaleString(),
        details: errorMessage,
        type: "error",
      })

      toast.error(errorMessage)

      // Reset processing status after a delay
      setTimeout(() => {
        setProcessingStatus({ status: "idle", progress: 0, message: "" })
      }, 3000)
    }
  }

  // Refresh preview data when activeTab changes - with debouncing
  useEffect(() => {
    if (datasetId && processingStatus.status === "idle") {
      const timeoutId = setTimeout(() => {
        refreshPreviewData()
      }, 300) // 300ms debounce

      return () => clearTimeout(timeoutId)
    }
  }, [activeTab, datasetId, processingStatus.status, refreshPreviewData])

  // Handle cancellation
  const handleCancelOperation = () => {
    api.cancelRequest()
    setProcessingStatus({ status: "idle", progress: 0, message: "" })
    toast.info("Operation cancelled")
  }

  // Add new handlers
  const handleMissingValuesClick = () => {
    if (!datasetId) {
      toast.error("No dataset loaded")
      return
    }

    setAnalysisMode("missing-values")
    addLog({
      title: "Missing Values Panel",
      date: new Date().toLocaleString(),
      details: "Opened advanced missing values handling panel.",
      type: "info",
    })
  }

  const handleNormalizationClick = () => {
    if (!datasetId) {
      toast.error("No dataset loaded")
      return
    }

    setAnalysisMode("normalization")
    addLog({
      title: "Normalization Panel",
      date: new Date().toLocaleString(),
      details: "Opened normalization and encoding panel.",
      type: "info",
    })
  }

  const handleMissingValuesApply = (strategy: string, columns: string[], fillValue?: string) => {
    handleProcessingOperation(
      () => api.handleMissingValuesAdvanced(datasetId!, strategy, columns, fillValue),
      "Advanced Missing Values Handling",
      `Missing values handled using ${strategy} strategy for ${columns.length} columns`,
    )
  }

  const handleNormalizationApply = (method: string, columns: string[]) => {
    handleProcessingOperation(
      () => api.normalizeDataAdvanced(datasetId!, method, columns),
      "Data Normalization",
      `Data normalized using ${method} method for ${columns.length} columns`,
    )
  }

  const handleEncodingApply = (method: string, columns: string[]) => {
    handleProcessingOperation(
      () => api.encodeCategoricalAdvanced(datasetId!, method, columns),
      "Categorical Encoding",
      `Categorical variables encoded using ${method} method for ${columns.length} columns`,
    )
  }

  // Add handler for refreshing random sample
  const handleRefreshRandomSample = async () => {
    if (!datasetId || activeTab !== "Random Sample") return

    try {
      const response = await fetch(`http://localhost:8000/api/v1/dataset/${datasetId}/refresh-random`, {
        method: "POST",
      })

      if (response.ok) {
        const result = await response.json()
        if (result.success) {
          setTableData(result.data.data || [])
          toast.success("Random sample refreshed!")

          addLog({
            title: "Random Sample Refreshed",
            date: new Date().toLocaleString(),
            details: `Generated new random sample with ${result.data.sample_size || 0} rows`,
            type: "info",
          })
        }
      }
    } catch (error) {
      console.error("Error refreshing random sample:", error)
      toast.error("Failed to refresh random sample")
    }
  }

  return (
    <div className="flex flex-col h-screen bg-[#121212] text-white overflow-hidden">
      <TopNavbar handleExportFile={handleExportFile} />
      <div className="flex flex-1 overflow-hidden">
        <LeftSidebar
          handleFileUpload={handleFileUpload}
          handleImputeMissingValues={handleImputeMissingValues}
          onVisualizationClick={handleVisualizationClick}
          onDataSummaryClick={handleDataSummaryClick}
          onCorrelationAnalysisClick={handleCorrelationAnalysisClick}
          onMissingValuesClick={handleMissingValuesClick}
          onNormalizationClick={handleNormalizationClick}
          disabled={processingStatus.status === "processing"}
        />
        <MainContent
          tableData={tableData}
          activeTab={activeTab}
          setActiveTab={setActiveTab}
          technique={technique}
          fileName={fileName}
          analysisMode={analysisMode}
          onBackToOverview={handleBackToOverview}
          summaryData={summaryData}
          correlationData={correlationData}
          disabled={processingStatus.status === "processing"}
          onMissingValuesApply={handleMissingValuesApply}
          onNormalizationApply={handleNormalizationApply}
          onEncodingApply={handleEncodingApply}
          onRefreshRandomSample={handleRefreshRandomSample}
        />
        <RightSidebar logs={logs} />
      </div>

      <LoadingOverlay
        isVisible={processingStatus.status === "processing"}
        title="Processing Data"
        message={processingStatus.message}
        progress={processingStatus.progress}
        canCancel={true}
        onCancel={handleCancelOperation}
      />
    </div>
  )
}
