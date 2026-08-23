import { useState } from 'react'

function App() {
  const [file, setFile] = useState<File | null>(null)
  const [message, setMessage] = useState('')
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = event.target.files?.[0]

    if (!selectedFile) return

    setFile(selectedFile)
    setMessage('')

    if (selectedFile.type.startsWith('image/')) {
      const url = URL.createObjectURL(selectedFile)
      setPreviewUrl(url)
    } else {
      setPreviewUrl(null)
    }
  }

  const handleUpload = async () => {
    if (!file) {
      setMessage('Please select a blueprint first.')
      return
    }

    const formData = new FormData()
    formData.append('file', file)

    setUploading(true)
    setMessage('Uploading...')

    try {
      const response = await fetch(
        'http://127.0.0.1:8000/blueprints/upload',
        {
          method: 'POST',
          body: formData,
        },
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Upload failed')
      }

      setMessage(`Uploaded successfully: ${data.filename}`)
    } catch (error) {
      console.error(error)
      setMessage('Upload failed. Check that the backend is running.')
    } finally {
      setUploading(false)
    }
  }

  return (
    <main
      style={{
        maxWidth: '900px',
        margin: '0 auto',
        padding: '40px 20px',
        fontFamily: 'Arial, sans-serif',
      }}
    >
      <h1>SIH Building Intelligence</h1>

      <p>
        Upload a 2D building blueprint to begin the processing pipeline.
      </p>

      <div style={{ marginTop: '30px' }}>
        <input
          type="file"
          accept=".png,.jpg,.jpeg,.pdf"
          onChange={handleFileChange}
        />
      </div>

      {file && (
        <p>
          Selected: <strong>{file.name}</strong>
        </p>
      )}

      <button
        onClick={handleUpload}
        disabled={!file || uploading}
        style={{
          marginTop: '10px',
          padding: '10px 18px',
          cursor: !file || uploading ? 'not-allowed' : 'pointer',
        }}
      >
        {uploading ? 'Uploading...' : 'Upload Blueprint'}
      </button>

      {message && (
        <p style={{ marginTop: '20px' }}>
          {message}
        </p>
      )}

      {previewUrl && (
        <section style={{ marginTop: '30px' }}>
          <h2>Blueprint Preview</h2>

          <img
            src={previewUrl}
            alt="Uploaded blueprint preview"
            style={{
              maxWidth: '100%',
              border: '1px solid #ccc',
              borderRadius: '8px',
            }}
          />
        </section>
      )}
    </main>
  )
}

export default App