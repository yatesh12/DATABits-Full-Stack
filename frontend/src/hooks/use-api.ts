// "use client"

// import { useState, useCallback, useRef } from "react"

// // Use environment variable from window for client-side code
// const API_BASE_URL =
//   typeof window !== "undefined"
//     ? (window as any).NEXT_PUBLIC_API_URL || "http://localhost:5000/api"
//     : "http://localhost:5000/api"

// interface ApiResponse<T> {
//   success: boolean
//   data?: T
//   message: string
//   error?: string
//   timestamp: string
// }

// interface ProcessingStatus {
//   status: "idle" | "processing" | "completed" | "error"
//   progress: number
//   message: string
// }

// export function useApi() {
//   const [loading, setLoading] = useState(false)
//   const [error, setError] = useState<string | null>(null)
//   const abortControllerRef = useRef<AbortController | null>(null)

//   const apiCall = useCallback(async <T>(
//     endpoint: string,
//     options: RequestInit = {}
//   ): Promise<T> => {
//   // Cancel previous request if still pending
//   if (abortControllerRef.current) {
//     abortControllerRef.current.abort()
//   }

//   const controller = new AbortController()
//   abortControllerRef.current = controller

//   setLoading(true)
//   setError(null)

//   try {
//     const response = await fetch(`${API_BASE_URL}${endpoint}`, {
//         headers: {
//           'Content-Type': 'application/json',
//           ...options.headers,
//         },
//         signal: controller.signal,
//         ...options,
//       })

//     if (!response.ok) {
//       const errorData: ApiResponse<any> = await response.json()
//       throw new Error(errorData.error || errorData.message || `HTTP error! status: ${response.status}`)
//     }

//     const result: ApiResponse<T> = await response.json()

//     if (!result.success) {
//       throw new Error(result.error || result.message || "Operation failed")
//     }

//     return result.data as T
//   } catch (err) {
//     if (err instanceof Error && err.name === "AbortError") {
//       // Request was cancelled, don't set error
//       throw err
//     }

//     const errorMessage = err instanceof Error ? err.message : "An unknown error occurred"
//     setError(errorMessage)
//     throw err
//   } finally {
//     setLoading(false)
//     abortControllerRef.current = null
//   }
// }
// , [])

// // Polling for status updates
// const pollStatus = useCallback(
//   async (datasetId: string, onUpdate: (status: ProcessingStatus) => void): Promise<void> => {
//     const poll = async () => {
//       try {
//         const status = await apiCall<ProcessingStatus>(`/dataset/${datasetId}/status`)
//         onUpdate(status)

//         if (status.status === "processing") {
//           setTimeout(poll, 1000) // Poll every second
//         }
//       } catch (error) {
//         console.error("Error polling status:", error)
//       }
//     }

//     poll()
//   },
//   [apiCall],
// )

// // File upload with progress
// const uploadFile = useCallback(
//   async (file: File, onProgress?: (progress: number) => void) => {
//     const formData = new FormData()
//     formData.append("file", file)

//     // Cancel previous request
//     if (abortControllerRef.current) {
//       abortControllerRef.current.abort()
//     }

//     const controller = new AbortController()
//     abortControllerRef.current = controller

//     setLoading(true)
//     setError(null)

//     try {
//       const response = await fetch(`${API_BASE_URL}/upload`, {
//         method: "POST",
//         body: formData,
//         signal: controller.signal,
//       })

//       if (!response.ok) {
//         const errorData: ApiResponse<any> = await response.json()
//         throw new Error(errorData.error || errorData.message || "Upload failed")
//       }

//       const result: ApiResponse<any> = await response.json()

//       if (!result.success) {
//         throw new Error(result.error || result.message || "Upload failed")
//       }

//       return result.data
//     } catch (err) {
//       if (err instanceof Error && err.name === "AbortError") {
//         throw err
//       }

//       const errorMessage = err instanceof Error ? err.message : "Upload failed"
//       setError(errorMessage)
//       throw err
//     } finally {
//       setLoading(false)
//       abortControllerRef.current = null
//     }
//   },
//   [apiCall],
// )

// // Dataset operations with optional async processing
// const getDatasetSummary = useCallback(
//   async (datasetId: string) => {
//     return apiCall(`/dataset/${datasetId}/summary`)
//   },
//   [apiCall],
// )

// const getDatasetPreview = useCallback(
//   async (datasetId: string, page = 1, perPage = 10, type = "head") => {
//     return apiCall(`/dataset/${datasetId}/preview?page=${page}&per_page=${perPage}&type=${type}`)
//   },
//   [apiCall],
// )

// const handleMissingValues = useCallback(
//   async (datasetId: string, strategy: string, columns?: string[], asyncParam = false) => {
//     return apiCall(`/dataset/${datasetId}/missing-values`, {
//       method: "POST",
//       body: JSON.stringify({ strategy, columns, async: asyncParam }),
//     })
//   },
//   [apiCall],
// )

// // Add new methods for missing values and normalization
// const handleMissingValuesAdvanced = useCallback(
//   async (datasetId: string, strategy: string, columns?: string[], fillValue?: string) => {
//     return apiCall(`/dataset/${datasetId}/missing-values`, {
//       method: "POST",
//       body: JSON.stringify({ strategy, columns, fill_value: fillValue }),
//     })
//   },
//   [apiCall],
// )

// const normalizeData = useCallback(
//   async (datasetId: string, method: string, columns?: string[], asyncParam = false) => {
//     return apiCall(`/dataset/${datasetId}/normalize`, {
//       method: "POST",
//       body: JSON.stringify({ method, columns, async: asyncParam }),
//     })
//   },
//   [apiCall],
// )

// const normalizeDataAdvanced = useCallback(
//   async (datasetId: string, method: string, columns?: string[]) => {
//     return apiCall(`/dataset/${datasetId}/normalize`, {
//       method: "POST",
//       body: JSON.stringify({ method, columns }),
//     })
//   },
//   [apiCall],
// )

// const encodeCategorical = useCallback(
//   async (datasetId: string, method: string, columns?: string[], asyncParam = false) => {
//     return apiCall(`/dataset/${datasetId}/encode`, {
//       method: "POST",
//       body: JSON.stringify({ method, columns, async: asyncParam }),
//     })
//   },
//   [apiCall],
// )

// const encodeCategoricalAdvanced = useCallback(
//   async (datasetId: string, method: string, columns?: string[]) => {
//     return apiCall(`/dataset/${datasetId}/encode`, {
//       method: "POST",
//       body: JSON.stringify({ method, columns }),
//     })
//   },
//   [apiCall],
// )

// const removeOutliers = useCallback(
//   async (datasetId: string, method: string, columns?: string[], threshold = 1.5, asyncParam = false) => {
//     return apiCall(`/dataset/${datasetId}/outliers`, {
//       method: "POST",
//       body: JSON.stringify({ method, columns, threshold, async: asyncParam }),
//     })
//   },
//   [apiCall],
// )

// const removeDuplicates = useCallback(
//   async (datasetId: string) => {
//     return apiCall(`/dataset/${datasetId}/duplicates`, {
//       method: "DELETE",
//     })
//   },
//   [apiCall],
// )

// const getCorrelationAnalysis = useCallback(
//   async (datasetId: string) => {
//     return apiCall(`/dataset/${datasetId}/correlation`)
//   },
//   [apiCall],
// )

// const exportDataset = useCallback(async (datasetId: string) => {
//   const response = await fetch(`${API_BASE_URL}/dataset/${datasetId}/export`)
//   if (!response.ok) {
//     throw new Error("Export failed")
//   }
//   return response.blob()
// }, [])

// const resetDataset = useCallback(
//   async (datasetId: string) => {
//     return apiCall(`/dataset/${datasetId}/reset`, {
//       method: "POST",
//     })
//   },
//   [apiCall],
// )

// const getProcessingHistory = useCallback(
//   async (datasetId: string) => {
//     return apiCall(`/dataset/${datasetId}/history`)
//   },
//   [apiCall],
// )

// // Add refresh random sample method
// const refreshRandomSample = useCallback(
//   async (datasetId: string) => {
//     return apiCall(`/dataset/${datasetId}/refresh-random`, {
//       method: "POST",
//     })
//   },
//   [apiCall],
// )

// const cancelRequest = useCallback(() => {
//   if (abortControllerRef.current) {
//     abortControllerRef.current.abort()
//   }
// }, [])

// // Update the return statement to include new methods
// return {
//     loading,
//     error,
//     uploadFile,
//     getDatasetSummary,
//     getDatasetPreview,
//     handleMissingValues,
//     handleMissingValuesAdvanced,
//     normalizeData,
//     normalizeDataAdvanced,
//     encodeCategorical,
//     encodeCategoricalAdvanced,
//     removeOutliers,
//     removeDuplicates,
//     getCorrelationAnalysis,
//     exportDataset,
//     resetDataset,
//     getProcessingHistory,
//     refreshRandomSample,
//     pollStatus,
//     cancelRequest,
//   }
// }

// useApi.ts (client)
"use client";

import { useCallback, useRef, useState } from "react";

/** Environment variable (client-side safe) */
const API_BASE_URL =
  typeof window !== "undefined"
    ? (window as any).NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"
    : "http://localhost:8000/api/v1";

/** Generic API response shape */
interface ApiResponse<T> {
  success: boolean;
  data?: T;
  message?: string;
  error?: string;
  timestamp?: string;
}

/** Processing status type */
export interface ProcessingStatus {
  status: "idle" | "processing" | "completed" | "error";
  progress: number;
  message?: string;
}

/** Hook return type (partial, inferred by TS from implementation) */
export function useApi() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // AbortController for fetch-based requests
  const abortControllerRef = useRef<AbortController | null>(null);
  // XHR ref for upload progress (so we can abort uploads)
  const uploadXhrRef = useRef<XMLHttpRequest | null>(null);

  /**
   * Generic API caller using fetch.
   * Cancels the previous fetch (if any) before making a new one.
   */
  const apiCall = useCallback(
    async <T>(endpoint: string, options: RequestInit = {}): Promise<T> => {
      // Cancel previous request if pending
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      const controller = new AbortController();
      abortControllerRef.current = controller;

      setLoading(true);
      setError(null);

      try {
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
          headers: { "Content-Type": "application/json", ...(options.headers ?? {}) },
          signal: controller.signal,
          ...options,
        });

        if (!response.ok) {
          // Try to parse JSON error body
          let errorData: ApiResponse<any> | null = null;
          try {
            errorData = await response.json();
          } catch {
            // ignore parse error
          }
          throw new Error(errorData?.error ?? errorData?.message ?? `HTTP error: ${response.status}`);
        }

        const result: ApiResponse<T> = await response.json();

        if (!result.success) {
          throw new Error(result.error ?? result.message ?? "Operation failed");
        }

        return result.data as T;
      } catch (err) {
        // If aborted, rethrow the AbortError so caller can handle if needed
        if (err instanceof Error && (err as any).name === "AbortError") {
          throw err;
        }
        const errorMessage = err instanceof Error ? err.message : "An unknown error occurred";
        setError(errorMessage);
        throw err;
      } finally {
        setLoading(false);
        abortControllerRef.current = null;
      }
    },
    []
  );

  /**
   * Poll dataset processing status.
   * Calls `onUpdate` with the latest ProcessingStatus until it is not "processing".
   */
  const pollStatus = useCallback(
    async (datasetId: string, onUpdate: (status: ProcessingStatus) => void): Promise<void> => {
      // Recursive poll using setTimeout to avoid blocking the main thread with loops
      const poll = async () => {
        try {
          const status = await apiCall<ProcessingStatus>(`/dataset/${datasetId}/status`);
          onUpdate(status);

          if (status.status === "processing") {
            // schedule next poll
            setTimeout(poll, 1000);
          }
        } catch (err) {
          // log but don't throw (caller may want to continue)
          // you can expose this error via onUpdate or other mechanism if needed
          // console.error("Error polling status:", err);
        }
      };

      poll();
    },
    [apiCall]
  );

  /**
   * Upload file with progress callback using XMLHttpRequest.
   * Returns the response.data on success.
   */
  const uploadFile = useCallback(
    (file: File, onProgress?: (percentage: number) => void): Promise<any> => {
      // Cancel any in-progress fetch or XHR
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      if (uploadXhrRef.current) {
        uploadXhrRef.current.abort();
      }

      setLoading(true);
      setError(null);

      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        uploadXhrRef.current = xhr;

        xhr.open("POST", `${API_BASE_URL}/upload`, true);

        xhr.upload.onprogress = (ev) => {
          if (ev.lengthComputable && onProgress) {
            const percent = Math.round((ev.loaded / ev.total) * 100);
            onProgress(percent);
          }
        };

        xhr.onreadystatechange = () => {
          if (xhr.readyState !== XMLHttpRequest.DONE) return;

          setLoading(false);
          uploadXhrRef.current = null;

          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              const parsed = JSON.parse(xhr.responseText) as ApiResponse<any>;
              if (!parsed.success) {
                const msg = parsed.error ?? parsed.message ?? "Upload failed";
                setError(msg);
                reject(new Error(msg));
                return;
              }
              resolve(parsed.data);
            } catch (e) {
              const errMsg = "Invalid JSON response from upload";
              setError(errMsg);
              reject(new Error(errMsg));
            }
          } else {
            // Try parse error body
            try {
              const parsed = JSON.parse(xhr.responseText) as ApiResponse<any>;
              const errMsg = parsed.error ?? parsed.message ?? `Upload failed: ${xhr.status}`;
              setError(errMsg);
              reject(new Error(errMsg));
            } catch {
              const errMsg = `Upload failed: ${xhr.status}`;
              setError(errMsg);
              reject(new Error(errMsg));
            }
          }
        };

        xhr.onerror = () => {
          setLoading(false);
          uploadXhrRef.current = null;
          const errMsg = "Network error during upload";
          setError(errMsg);
          reject(new Error(errMsg));
        };

        xhr.onabort = () => {
          setLoading(false);
          uploadXhrRef.current = null;
          reject(new DOMException("Upload aborted", "AbortError"));
        };

        const form = new FormData();
        form.append("file", file);
        xhr.send(form);
      });
    },
    []
  );

  // Dataset operations (all use apiCall)
  const getDatasetSummary = useCallback(
    (datasetId: string) => apiCall(`/dataset/${datasetId}/summary`),
    [apiCall]
  );

  const getDatasetPreview = useCallback(
    (datasetId: string, page = 1, perPage = 10, type = "head") =>
      apiCall(`/dataset/${datasetId}/preview?page=${page}&per_page=${perPage}&type=${type}`),
    [apiCall]
  );

  const handleMissingValues = useCallback(
    (datasetId: string, strategy: string, columns?: string[], asyncParam = false) =>
      apiCall(`/dataset/${datasetId}/missing-values`, {
        method: "POST",
        body: JSON.stringify({ strategy, columns, async: asyncParam }),
      }),
    [apiCall]
  );

  const handleMissingValuesAdvanced = useCallback(
    (datasetId: string, strategy: string, columns?: string[], fillValue?: string) =>
      apiCall(`/dataset/${datasetId}/missing-values`, {
        method: "POST",
        body: JSON.stringify({ strategy, columns, fill_value: fillValue }),
      }),
    [apiCall]
  );

  const normalizeData = useCallback(
    (datasetId: string, method: string, columns?: string[], asyncParam = false) =>
      apiCall(`/dataset/${datasetId}/normalize`, {
        method: "POST",
        body: JSON.stringify({ method, columns, async: asyncParam }),
      }),
    [apiCall]
  );

  const normalizeDataAdvanced = useCallback(
    (datasetId: string, method: string, columns?: string[]) =>
      apiCall(`/dataset/${datasetId}/normalize`, {
        method: "POST",
        body: JSON.stringify({ method, columns }),
      }),
    [apiCall]
  );

  const encodeCategorical = useCallback(
    (datasetId: string, method: string, columns?: string[], asyncParam = false) =>
      apiCall(`/dataset/${datasetId}/encode`, {
        method: "POST",
        body: JSON.stringify({ method, columns, async: asyncParam }),
      }),
    [apiCall]
  );

  const encodeCategoricalAdvanced = useCallback(
    (datasetId: string, method: string, columns?: string[]) =>
      apiCall(`/dataset/${datasetId}/encode`, {
        method: "POST",
        body: JSON.stringify({ method, columns }),
      }),
    [apiCall]
  );

  const removeOutliers = useCallback(
    (datasetId: string, method: string, columns?: string[], threshold = 1.5, asyncParam = false) =>
      apiCall(`/dataset/${datasetId}/outliers`, {
        method: "POST",
        body: JSON.stringify({ method, columns, threshold, async: asyncParam }),
      }),
    [apiCall]
  );

  const removeDuplicates = useCallback(
    (datasetId: string) => apiCall(`/dataset/${datasetId}/duplicates`, { method: "DELETE" }),
    [apiCall]
  );

  const getCorrelationAnalysis = useCallback(
    (datasetId: string) => apiCall(`/dataset/${datasetId}/correlation`),
    [apiCall]
  );

  const exportDataset = useCallback(async (datasetId: string) => {
    const resp = await fetch(`${API_BASE_URL}/dataset/${datasetId}/export`);
    if (!resp.ok) throw new Error("Export failed");
    return resp.blob();
  }, []);

  const resetDataset = useCallback(
    (datasetId: string) => apiCall(`/dataset/${datasetId}/reset`, { method: "POST" }),
    [apiCall]
  );

  const getProcessingHistory = useCallback(
    (datasetId: string) => apiCall(`/dataset/${datasetId}/history`),
    [apiCall]
  );

  const refreshRandomSample = useCallback(
    (datasetId: string) => apiCall(`/dataset/${datasetId}/refresh-random`, { method: "POST" }),
    [apiCall]
  );

  const cancelRequest = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    if (uploadXhrRef.current) {
      uploadXhrRef.current.abort();
      uploadXhrRef.current = null;
    }
  }, []);

  return {
    loading,
    error,
    apiCall,
    uploadFile,
    getDatasetSummary,
    getDatasetPreview,
    handleMissingValues,
    handleMissingValuesAdvanced,
    normalizeData,
    normalizeDataAdvanced,
    encodeCategorical,
    encodeCategoricalAdvanced,
    removeOutliers,
    removeDuplicates,
    getCorrelationAnalysis,
    exportDataset,
    resetDataset,
    getProcessingHistory,
    refreshRandomSample,
    pollStatus,
    cancelRequest,
  };
}
