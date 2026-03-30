import { useEffect, useRef } from 'react'
import { useKnowledgeStore } from '../stores/knowledgeStore'

export default function KnowledgeExplorer() {
  const {
    namespaces, selectedNamespace, searchResults, searchQuery, searching, loading, searchError,
    uploadMessage, fetch, select, search, setSearchQuery, upload, clearUploadMessage,
  } = useKnowledgeStore()
  const fileRef = useRef<HTMLInputElement>(null)

  useEffect(() => { fetch() }, [fetch])

  const selected = namespaces.find((ns) => ns.name === selectedNamespace)

  const handleSearch = () => {
    if (searchQuery.trim()) search(searchQuery)
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      upload(file)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  return (
    <div className="flex gap-6 h-full">
      {/* Left panel — Namespaces */}
      <div className="w-80 shrink-0 flex flex-col">
        <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-4">Knowledge Base</p>

        {loading && <p className="text-sm text-text-muted">Loading...</p>}

        <div className="flex-1 overflow-auto space-y-1">
          {namespaces.map((ns) => (
            <button
              key={ns.name}
              onClick={() => select(ns.name)}
              className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition border ${
                selectedNamespace === ns.name
                  ? 'bg-primary/5 border-primary/30 text-text'
                  : 'bg-white border-border hover:bg-elevated/50 text-text'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium">{ns.name}</span>
                <span className="text-xs text-text-muted bg-elevated border border-border px-1.5 py-0.5 rounded">
                  {ns.vector_count != null ? ns.vector_count.toLocaleString() : '—'}
                </span>
              </div>
              {ns.assigned_roles.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-1.5">
                  {ns.assigned_roles.map((role) => (
                    <span key={role} className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-purple-50 border border-purple-200 text-purple-700">
                      {role}
                    </span>
                  ))}
                </div>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Right panel — Search & Upload */}
      <div className="flex-1 min-w-0 overflow-y-auto">
        {!selectedNamespace ? (
          <div className="flex items-center justify-center h-full text-text-muted">
            Select a namespace to explore
          </div>
        ) : (
          <div className="max-w-2xl space-y-6">
            <div>
              <h2 className="text-xl font-semibold text-text">{selectedNamespace}</h2>
              {selected && selected.vector_count != null && (
                <p className="text-sm text-text-muted mt-1">
                  {selected.vector_count.toLocaleString()} vectors
                </p>
              )}
            </div>

            {/* Search */}
            <div>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="Search this namespace..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
                  className="flex-1 px-3 py-2 rounded-lg bg-white border border-border text-sm text-text placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-primary"
                />
                <button
                  onClick={handleSearch}
                  disabled={searching || !searchQuery.trim()}
                  className="px-4 py-2 rounded-lg text-sm font-medium bg-primary text-white hover:bg-primary-hover disabled:opacity-50"
                >
                  {searching ? 'Searching...' : 'Search'}
                </button>
              </div>

              {searchError && (
                <p className="text-sm text-amber-600 mt-2">{searchError}</p>
              )}

              {searchResults.length > 0 && (
                <div className="mt-4 space-y-3">
                  {searchResults.map((result) => (
                    <div key={result.id} className="bg-card border border-border rounded-xl p-4">
                      <div className="flex items-center gap-3 mb-2">
                        <div className="flex-1 h-1.5 bg-elevated rounded-full overflow-hidden">
                          <div
                            className="h-full bg-primary rounded-full"
                            style={{ width: `${Math.round(result.score * 100)}%` }}
                          />
                        </div>
                        <span className="text-xs font-mono text-text-muted shrink-0">
                          {(result.score * 100).toFixed(1)}%
                        </span>
                      </div>
                      <p className="text-sm text-text leading-relaxed">{result.text_preview}</p>
                      {Object.keys(result.metadata).length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-2">
                          {Object.entries(result.metadata).map(([k, v]) => (
                            <span key={k} className="px-1.5 py-0.5 rounded text-[10px] bg-elevated border border-border text-text-muted">
                              {k}: {v}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Upload */}
            <div>
              <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-2">Upload</p>
              <div className="border-2 border-dashed border-border rounded-xl p-6 text-center hover:border-primary/30 transition">
                <p className="text-sm text-text-muted mb-2">Upload a file to this namespace</p>
                <p className="text-xs text-text-muted/60 mb-3">PDF, TXT, or Markdown</p>
                <input
                  ref={fileRef}
                  type="file"
                  accept=".pdf,.txt,.md"
                  onChange={handleFileChange}
                  className="text-sm text-text-muted"
                />
              </div>
              {uploadMessage && (
                <div className="mt-3 bg-amber-50 border border-amber-200 rounded-lg p-3 flex items-start justify-between">
                  <p className="text-sm text-amber-700">{uploadMessage}</p>
                  <button onClick={clearUploadMessage} className="text-amber-400 hover:text-amber-600 ml-2 shrink-0">&times;</button>
                </div>
              )}
            </div>

            {/* Assigned Agents */}
            {selected && selected.assigned_roles.length > 0 && (
              <div>
                <p className="text-xs font-bold tracking-wider uppercase text-text-muted mb-2">Assigned Agents</p>
                <div className="flex flex-wrap gap-1.5">
                  {selected.assigned_roles.map((role) => (
                    <span key={role} className="px-2.5 py-1 rounded-full text-xs font-medium bg-purple-50 border border-purple-200 text-purple-700">
                      {role}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
