import { useState, useEffect, useRef } from 'react'

// ─── PDF sample claims ───────────────────────────────────────────────────────
// Place the 4 generated PDFs in your project's /public/samples/ folder.
// Each entry maps a display name → the expected routing outcome (for mock fallback)
// and the PDF filename served from /public/samples/.
const PDF_SAMPLES = [
  {
    name: 'Fast Track',
    file: 'ROUTE1_FastTrack.pdf',
    mockKey: 'Fast Track',
  },
  {
    name: 'Investigation Flag',
    file: 'ROUTE3_InvestigationFlag.pdf',
    mockKey: 'Investigation Flag',
  },
  {
    name: 'Specialist Queue',
    file: 'ROUTE4_SpecialistQueue.pdf',
    mockKey: 'Specialist Queue',
  },
  {
    name: 'Manual Review',
    file: 'ROUTE2_ManualReview.pdf',
    mockKey: 'Manual Review',
  },
]

// ─── Routing colour palette ───────────────────────────────────────────────────
const routeColors = {
  'Fast-track': { bg: '#ecfdf5', border: '#86efac', text: '#15803d', badge: '#bbf7d0', badgeText: '#166534' },
  'Standard Review': { bg: '#eff6ff', border: '#93c5fd', text: '#1d4ed8', badge: '#bfdbfe', badgeText: '#1e40af' },
  'Investigation Flag': { bg: '#fef2f2', border: '#fca5a5', text: '#b91c1c', badge: '#fecaca', badgeText: '#991b1b' },
  'Specialist Queue': { bg: '#fefce8', border: '#fde047', text: '#854d0e', badge: '#fef08a', badgeText: '#713f12' },
  'Manual Review': { bg: '#fff7ed', border: '#fdba74', text: '#c2410c', badge: '#fed7aa', badgeText: '#9a3412' },
}
function getRouteColor(route) {
  return routeColors[route] || routeColors['Standard Review']
}

const PROCESSING_STEPS = [
  'Extracting document fields',
  'Checking for inconsistencies',
  'Running fraud signals',
  'Determining routing',
  'Finalising report',
]
const MIN_ANIM_MS = 2000

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// ─── Main component ───────────────────────────────────────────────────────────
export default function App() {
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [stepIndex, setStepIndex] = useState(0)
  const [showResult, setShowResult] = useState(false)

  const stepRef = useRef(null)
  const startTimeRef = useRef(null)
  const resultRef = useRef(null)

  useEffect(() => {
    if (!loading) return
    setStepIndex(0)
    const interval = setInterval(() => {
      setStepIndex(prev => Math.min(prev + 1, PROCESSING_STEPS.length - 1))
    }, MIN_ANIM_MS / PROCESSING_STEPS.length)
    stepRef.current = interval
    return () => clearInterval(interval)
  }, [loading])

  const processFile = async (selectedFile, mockKey) => {
    setResult(null)
    setShowResult(false)
    setLoading(true)
    startTimeRef.current = Date.now()

    const formData = new FormData()
    formData.append('file', selectedFile)

    let data = null
    try {
      const response = await fetch(`${API_BASE_URL}/process-claim`, {
        method: 'POST',
        body: formData,
      })
      data = await response.json()
    } catch {
      console.error('Error processing file')
    }

    resultRef.current = data
    const elapsed = Date.now() - startTimeRef.current
    const wait = Math.max(0, MIN_ANIM_MS - elapsed)

    setTimeout(() => {
      clearInterval(stepRef.current)
      setLoading(false)
      setResult(data)
      setTimeout(() => setShowResult(true), 30)
    }, wait)
  }

  const handleUpload = () => {
    if (!file) return
    processFile(file, file._mockKey || file.name)
  }

  // Fetch a PDF from /public/samples/ and submit it as if the user uploaded it
  const trySamplePDF = async (sample) => {
    try {
      const res = await fetch(`/samples/${sample.file}`)
      const blob = await res.blob()
      const f = new File([blob], sample.file, { type: 'application/pdf' })
      f._mockKey = sample.mockKey
      setFile(f)
      processFile(f, sample.mockKey)
    } catch {
      // If the PDF file isn't hosted yet, fall straight to mock
      const f = new File([new Blob([''])], sample.file, { type: 'application/pdf' })
      f._mockKey = sample.mockKey
      setFile(f)
      processFile(f, sample.mockKey)
    }
  }

  const rc = result ? getRouteColor(result.recommendedRoute) : {}

  return (
    <>
      <div style={{
        background: 'linear-gradient(135deg, #2563eb 0%, #4f46e5 100%)',
        padding: '48px',
        color: '#fff',
        position: 'relative',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        boxShadow: '0 25px 60px rgba(37,99,235,0.25)',
      }}>
        <div style={{ position: 'absolute', left: -70, bottom: -70, width: 180, height: 180, borderRadius: '50%', background: 'rgba(255,255,255,0.05)', textAlign: 'center' }} />
        <div style={{ position: 'relative', zIndex: 1 }}>
          <h1 style={{ margin: 0, fontSize: 28, fontWeight: 700, lineHeight: 1.3, color: '#ffffff', textAlign: 'center' }}>
            Autonomous Insurance Claims Processing Agent
          </h1>
          <p style={{ marginTop: 18, fontSize: 20, opacity: 0.92, lineHeight: 1.7, maxWidth: 760, textAlign: 'center' }}>
            Intelligent FNOL document extraction, routing, inconsistency detection, and automated claim workflow classification.
          </p>
          <div style={{ display: 'flex', gap: 16, marginTop: 32, flexWrap: 'wrap', justifyContent: 'center' }}>
            {['PDF & TXT Support', 'Fraud Detection', 'Real-time Routing'].map(label => (
              <div key={label} style={{
                background: 'rgba(255,255,255,0.12)',
                backdropFilter: 'blur(10px)',
                padding: '14px 18px',
                borderRadius: 16,
                fontSize: 14,
                fontWeight: 600,
                textAlign: 'center'
              }}>
                {label}
              </div>
            ))}
          </div>
        </div>
      </div>
      <div style={{
        minHeight: '100vh',
        background: '#f1f5f9',
        fontFamily: 'Poppins, sans-serif',
        padding: '32px',
      }}>
        <div style={{ maxWidth: 1440, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 24 }}>

          {/* UPLOAD CARD */}
          <div style={card}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 24, gap: 12 }}>
              <div>
                <h2 style={{ margin: 0, fontSize: 28, fontWeight: 700, color: '#0f172a' }}>Upload FNOL Document</h2>
                <p style={{ margin: '8px 0 0', fontSize: 14, color: '#64748b' }}>Upload a PDF claim document or try one of the sample FNOLs below</p>
              </div>
              <span style={{ background: '#eff6ff', color: '#2563eb', padding: '10px 16px', borderRadius: 14, fontSize: 14, fontWeight: 600, whiteSpace: 'nowrap', flexShrink: 0 }}>
                Supported: PDF / TXT
              </span>
            </div>

            {/* DROP ZONE */}
            <div style={{
              border: '2px dashed #60a5fa',
              borderRadius: 24,
              padding: '52px 30px 40px',
              background: '#f8fbff',
              textAlign: 'center',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: 0,
            }}>
              <h3 style={{ margin: 0, fontSize: 28, fontWeight: 700, color: '#0f172a' }}>Drag & Drop Your File Here</h3>
              <p style={{ margin: '12px 0 0', fontSize: 16, color: '#64748b' }}>Upload claim documents for automated processing</p>

              <input
                id="file-input"
                type="file"
                accept=".txt,.pdf"
                onChange={e => {
                  const f = e.target.files[0]
                  if (f) setFile(f)
                }}
                style={{ display: 'none' }}
              />

              <label
                htmlFor="file-input"
                style={{
                  marginTop: 28,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 8,
                  background: '#ffffff',
                  border: '2px solid #2563eb',
                  color: '#2563eb',
                  padding: '14px 28px',
                  borderRadius: 16,
                  fontWeight: 700,
                  fontSize: 15,
                  cursor: 'pointer',
                  fontFamily: 'Poppins, sans-serif',
                  transition: 'background 0.15s',
                }}
                onMouseEnter={e => { e.currentTarget.style.background = '#eff6ff' }}
                onMouseLeave={e => { e.currentTarget.style.background = '#ffffff' }}
              >
                Choose File
              </label>

              {file && (
                <div style={{
                  marginTop: 16,
                  display: 'inline-flex', alignItems: 'center', gap: 6,
                  background: '#dbeafe', color: '#1d4ed8',
                  padding: '10px 16px', borderRadius: 12,
                  fontSize: 14, fontWeight: 600,
                }}>
                  📎 {file.name}
                </div>
              )}

              <button
                onClick={handleUpload}
                disabled={loading || !file}
                style={{
                  marginTop: 18,
                  background: loading || !file ? '#94a3b8' : 'linear-gradient(135deg, #2563eb 0%, #4f46e5 100%)',
                  color: '#fff',
                  border: 'none',
                  padding: '16px 36px',
                  borderRadius: 16,
                  cursor: loading || !file ? 'not-allowed' : 'pointer',
                  fontWeight: 700,
                  fontSize: 15,
                  fontFamily: 'Poppins, sans-serif',
                  boxShadow: loading || !file ? 'none' : '0 12px 24px rgba(37,99,235,0.25)',
                  display: 'flex', alignItems: 'center', gap: 8,
                }}
              >
                {loading ? (
                  <>
                    <span style={{
                      width: 15, height: 15, border: '2px solid rgba(255,255,255,0.4)',
                      borderTopColor: '#fff', borderRadius: '50%',
                      display: 'inline-block',
                      animation: 'spin 0.7s linear infinite',
                    }} />
                    Processing…
                  </>
                ) : 'Process Claim'}
              </button>
            </div>

            {/* SAMPLE PDF BUTTONS */}
            {/* SAMPLE PDF CARDS (CLEAN + COLORED) */}
            <div style={{ marginTop: 20 }}>
              <p style={{
                margin: '0 0 12px',
                fontSize: 13,
                fontWeight: 600,
                color: '#64748b',
                textAlign: 'center',
                letterSpacing: '0.04em',
                textTransform: 'uppercase'
              }}>
                Try sample FNOL documents
              </p>

              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                gap: 14
              }}>
                {PDF_SAMPLES.map(sample => {
                  const route =
                    sample.mockKey === 'Fast Track'
                      ? 'Fast-track'
                      : sample.mockKey === 'Investigation Flag'
                        ? 'Investigation Flag'
                        : sample.mockKey === 'Specialist Queue'
                          ? 'Specialist Queue'
                          : 'Manual Review'

                  const rc2 = getRouteColor(route)

                  return (
                    <div
                      key={sample.name}
                      style={{
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 12,
                        padding: '16px',
                        borderRadius: 16,
                        border: `1px solid ${rc2.border}`,
                        background: rc2.bg,
                        boxShadow: '0 6px 18px rgba(15,23,42,0.04)',
                      }}
                    >
                      {/* Title */}
                      <div style={{
                        fontSize: 14,
                        fontWeight: 800,
                        color: rc2.text
                      }}>
                        {sample.name}
                      </div>

                      {/* Buttons */}
                      <div style={{
                        display: 'flex',
                        gap: 10
                      }}>
                        {/* TRY */}
                        <button
                          onClick={() => trySamplePDF(sample)}
                          disabled={loading}
                          style={{
                            flex: 1,
                            background: '#fff',
                            color: rc2.text,
                            border: `1px solid ${rc2.border}`,
                            padding: '10px 12px',
                            borderRadius: 10,
                            fontSize: 12,
                            fontWeight: 700,
                            cursor: loading ? 'not-allowed' : 'pointer'
                          }}
                        >
                          Try
                        </button>

                        {/* DOWNLOAD (same style as Try) */}
                        <button
                          onClick={() => {
                            const link = document.createElement('a')
                            link.href = `/samples/${sample.file}`
                            link.download = sample.file
                            link.click()
                          }}
                          style={{
                            flex: 1,
                            background: '#fff',
                            color: rc2.text,
                            border: `1px solid ${rc2.border}`,
                            padding: '10px 12px',
                            borderRadius: 10,
                            fontSize: 12,
                            fontWeight: 700,
                            cursor: 'pointer'
                          }}
                        >
                          Download
                        </button>
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>

          {/* PROCESSING ANIMATION */}
          {loading && (
            <div style={{
              ...card,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              padding: '56px 32px',
              gap: 32,
            }}>
              <div style={{ position: 'relative', width: 72, height: 72 }}>
                <div style={{
                  position: 'absolute', inset: 0,
                  border: '3px solid #e2e8f0',
                  borderTopColor: '#2563eb',
                  borderRadius: '50%',
                  animation: 'spin 0.8s linear infinite',
                }} />
                <div style={{
                  position: 'absolute', inset: 10,
                  border: '2px solid transparent',
                  borderTopColor: '#4f46e5',
                  borderRadius: '50%',
                  animation: 'spin 1.2s linear infinite reverse',
                }} />
              </div>

              <div style={{ textAlign: 'center' }}>
                <p style={{ margin: 0, fontSize: 20, fontWeight: 700, color: '#0f172a' }}>
                  {PROCESSING_STEPS[stepIndex]}
                </p>
                <p style={{ margin: '6px 0 0', fontSize: 14, color: '#64748b' }}>
                  Step {stepIndex + 1} of {PROCESSING_STEPS.length}
                </p>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 10, width: '100%', maxWidth: 400 }}>
                {PROCESSING_STEPS.map((step, i) => {
                  const done = i < stepIndex
                  const active = i === stepIndex
                  return (
                    <div key={step} style={{
                      display: 'flex', alignItems: 'center', gap: 14,
                      padding: '14px 18px',
                      borderRadius: 16,
                      background: active ? '#eff6ff' : done ? '#f0fdf4' : '#f8fafc',
                      border: `1px solid ${active ? '#bfdbfe' : done ? '#bbf7d0' : '#e2e8f0'}`,
                      boxShadow: active ? '0 4px 14px rgba(37,99,235,0.1)' : 'none',
                      transition: 'all 0.3s',
                    }}>
                      <div style={{
                        width: 24, height: 24, borderRadius: '50%', flexShrink: 0,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        background: active ? '#2563eb' : done ? '#16a34a' : '#e2e8f0',
                        animation: active ? 'pulse 1.2s ease-in-out infinite' : 'none',
                      }}>
                        {done
                          ? <span style={{ color: '#fff', fontSize: 13, fontWeight: 700 }}>✓</span>
                          : active
                            ? <span style={{ color: '#fff', fontSize: 10 }}>●</span>
                            : null}
                      </div>
                      <span style={{
                        fontSize: 14,
                        fontWeight: active ? 700 : 400,
                        color: active ? '#1e40af' : done ? '#15803d' : '#94a3b8',
                        transition: 'color 0.3s',
                      }}>
                        {step}
                      </span>
                      {done && (
                        <span style={{
                          marginLeft: 'auto', fontSize: 11, color: '#16a34a',
                          background: '#dcfce7', padding: '3px 10px', borderRadius: 8, fontWeight: 600,
                        }}>Done</span>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* RESULTS */}
          {result && !loading && (
            <div style={{
              display: 'flex', flexDirection: 'column', gap: 20,
              opacity: showResult ? 1 : 0,
              transform: showResult ? 'translateY(0)' : 'translateY(12px)',
              transition: 'opacity 0.4s ease, transform 0.4s ease',
            }}>
              {/* TOP ROW */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 20 }}>
                {/* Route */}
                <div style={{ ...card, background: rc.bg, border: `1px solid ${rc.border}`, padding: '24px', display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: rc.text, opacity: 0.7 }}>
                    Recommended Route
                  </span>
                  <span style={{ fontSize: 24, fontWeight: 800, color: rc.text, lineHeight: 1.2 }}>
                    {result.recommendedRoute}
                  </span>
                  <span style={{ display: 'inline-flex', width: 'fit-content', background: rc.badge, color: rc.badgeText, fontSize: 12, fontWeight: 700, padding: '4px 12px', borderRadius: 8 }}>
                    Routed
                  </span>
                </div>

                {/* Reasoning */}
                <div style={{ ...card, padding: '24px', display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: '#000000' }}>
                    Routing Reasoning
                  </span>
                  <p style={{ margin: 0, fontSize: 14, color: '#374151', lineHeight: 1.7 }}>
                    {result.reasoning}
                  </p>
                </div>

                {/* Missing Fields */}
                <div style={{ ...card, padding: '24px', display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: '#000000' }}>
                    Missing Fields
                  </span>
                  {result.missingFields.length === 0 ? (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, background: '#f0fdf4', border: '1px solid #bbf7d0', borderRadius: 10, padding: '10px 14px', fontSize: 13, fontWeight: 600, color: '#15803d' }}>
                      ✓ All fields present
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                      {result.missingFields.map(f => (
                        <div key={f} style={{ background: '#fef2f2', border: '1px solid #fecaca', color: '#b91c1c', padding: '8px 12px', borderRadius: 8, fontSize: 12, fontWeight: 600, textTransform: 'capitalize' }}>
                          ✕ {f.replace(/_/g, ' ')}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              {/* INCONSISTENCIES */}
              {result.inconsistencies && result.inconsistencies.length > 0 && (
                <div style={{ ...card, padding: '24px', border: '1px solid #fca5a5', background: '#fef2f2' }}>
                  <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: '#b91c1c', opacity: 0.8, display: 'block', marginBottom: 12 }}>
                    ⚠ Inconsistencies Detected
                  </span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {result.inconsistencies.map((inc, i) => (
                      <div key={i} style={{ background: '#fff', border: '1px solid #fecaca', color: '#b91c1c', padding: '10px 14px', borderRadius: 10, fontSize: 13, fontWeight: 600 }}>
                        {inc}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* EXTRACTED FIELDS */}
              <div style={card}>
                <div style={{ marginBottom: 24 }}>
                  <h2 style={{ margin: 0, fontSize: 28, fontWeight: 700, color: '#0f172a' }}>Extracted Fields</h2>
                  <p style={{ margin: '6px 0 0', fontSize: 14, color: '#64748b' }}>
                    {Object.keys(result.extractedFields).length} fields extracted from document
                  </p>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  {[
                    { title: 'Policy Information', keys: ['policy_number', 'policyholder_name', 'effective_dates'] },
                    { title: 'Incident Information', keys: ['incident_date', 'incident_time', 'location', 'description'] },
                    { title: 'Involved Parties', keys: ['claimant', 'third_parties', 'contact_details'] },
                    { title: 'Asset Details', keys: ['asset_type', 'asset_id', 'estimated_damage'] },
                    { title: 'Other Mandatory Fields', keys: ['claim_type', 'attachments', 'initial_estimate'] },
                  ].map((group, gi, arr) => {
                    const presentEntries = group.keys
                      .map(k => [k, result.extractedFields[k]])
                      .filter(([, v]) => v !== undefined && v !== null && v !== '')
                    const missingKeys = group.keys.filter(k =>
                      (result.missingFields && result.missingFields.includes(k)) ||
                      result.extractedFields[k] === undefined
                    )
                    const allRows = [
                      ...presentEntries.map(([k, v]) => ({ key: k, value: String(v), missing: false })),
                      ...missingKeys.map(k => ({ key: k, value: null, missing: true })),
                    ]
                    return (
                      <div key={group.title} style={{ paddingBottom: gi < arr.length - 1 ? 20 : 0, borderBottom: gi < arr.length - 1 ? '1px solid #e2e8f0' : 'none', marginBottom: gi < arr.length - 1 ? 4 : 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
                          <span style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                            {group.title}
                          </span>
                          {missingKeys.length > 0 && (
                            <span style={{ fontSize: 11, fontWeight: 700, color: '#b91c1c', background: '#fecaca', padding: '2px 10px', borderRadius: 6 }}>
                              {missingKeys.length} missing
                            </span>
                          )}
                        </div>
                        <div>
                          {allRows.map(({ key, value, missing }, i) => (
                            <div key={key} style={{ display: 'flex', alignItems: 'baseline', padding: '8px 0', borderBottom: i < allRows.length - 1 ? '1px solid #f1f5f9' : 'none' }}>
                              <span style={{ width: 180, flexShrink: 0, fontSize: 13, color: missing ? '#f87171' : '#64748b', textTransform: 'capitalize' }}>
                                {key.replace(/_/g, ' ')}
                              </span>
                              {missing ? (
                                <span style={{ fontSize: 13, color: '#f87171', fontStyle: 'italic' }}>— missing</span>
                              ) : (
                                <span style={{ fontSize: 13, fontWeight: 600, color: '#0f172a', lineHeight: 1.5 }}>{value}</span>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* JSON */}
              <div style={card}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                  <span style={{ width: 32, height: 32, background: '#0f172a', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, flexShrink: 0 }}>
                    <span style={{ color: '#4ade80', fontWeight: 700 }}>{'{}'}</span>
                  </span>
                  <span style={{ fontSize: 18, fontWeight: 700, color: '#0f172a' }}>API Response (JSON)</span>
                </div>
                <pre style={{
                  background: '#0f172a', color: '#4ade80', padding: '20px', borderRadius: 12,
                  overflowX: 'auto', fontSize: 12, lineHeight: 1.7,
                  fontFamily: "'JetBrains Mono', 'Fira Code', monospace", margin: 0,
                }}>
                  {JSON.stringify(result, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>

        <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.5; } }
      `}</style>
      </div>
    </>
  )
}

const card = {
  background: '#ffffff',
  borderRadius: 24,
  padding: '28px',
  boxShadow: '0 10px 30px rgba(15,23,42,0.06)',
  border: '1px solid #e2e8f0',
  boxSizing: 'border-box',
}