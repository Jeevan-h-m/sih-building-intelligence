import { useState } from 'react'

function App() {
  const [file, setFile] = useState<File | null>(null)
  const [originalPreview, setOriginalPreview] = useState<string | null>(null)
  const [processedPreview, setProcessedPreview] = useState<string | null>(null)
  const [message, setMessage] = useState('')
  const [processing, setProcessing] = useState(false)

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0]

    if (!selectedFile) return

    setFile(selectedFile)
    setProcessedPreview(null)
    setMessage('')

    if (selectedFile.type.startsWith('image/')) {
      setOriginalPreview(URL.createObjectURL(selectedFile))
    } else {
      setOriginalPreview(null)
    }
  }

  const handleProcess = async () => {
    if (!file) {
      setMessage('Please select a PNG or JPEG blueprint.')
      return
    }

    const formData = new FormData()
    formData.append('file', file)

    setProcessing(true)
    setMessage('Processing blueprint...')

    try {
      const response = await fetch(
        'http://127.0.0.1:8000/blueprints/process',
        {
          method: 'POST',
          body: formData,
        },
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Processing failed')
      }

      const processedUrl =
        `http://127.0.0.1:8000${data.processed_url}`

      setProcessedPreview(processedUrl)
      setMessage('Blueprint processed successfully.')
    } catch (error) {
      console.error(error)
      setMessage('Processing failed. Check the backend.')
    } finally {
      setProcessing(false)
    }
  }

  return (
    <main
      style={{
        maxWidth: '1200px',
        margin: '0 auto',
        padding: '40px 20px',
        fontFamily: 'Arial, sans-serif',
      }}
    >
      <h1>SIH Building Intelligence</h1>

      <p>
        2D Blueprint → Preprocessing
      </p>

      <input
        type="file"
        accept=".png,.jpg,.jpeg"
        onChange={handleFileChange}
      />

      {file && (
        <p>
          Selected: <strong>{file.name}</strong>
        </p>
      )}

      <button
        onClick={handleProcess}
        disabled={!file || processing}
        style={{
          padding: '10px 18px',
          marginTop: '10px',
        }}
      >
        {processing ? 'Processing...' : 'Process Blueprint'}
      </button>

      {message && <p>{message}</p>}

      {(originalPreview || processedPreview) && (
        <section
          style={{
            display: 'flex',
            gap: '30px',
            marginTop: '30px',
            alignItems: 'flex-start',
          }}
        >
          {originalPreview && (
            <div style={{ flex: 1 }}>
              <h2>Original Blueprint</h2>

              <img
                src={originalPreview}
                alt="Original blueprint"
                style={{
                  width: '100%',
                  border: '1px solid #ccc',
                }}
              />
            </div>
          )}

          {processedPreview && (
            <div style={{ flex: 1 }}>
              <h2>Processed Blueprint</h2>

              <img
                src={processedPreview}
                alt="Processed blueprint"
                style={{
                  width: '100%',
                  border: '1px solid #ccc',
                }}
              />
            </div>
          )}
        </section>
      )}
    </main>
  )
}

export default App