import { useState, useEffect } from 'react';
import './index.css';

const API_BASE = 'http://localhost:8000';

function App() {
  const [projectId, setProjectId] = useState<string | null>(null);
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobStatus, setJobStatus] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  // 1. Fetch or create a default project
  useEffect(() => {
    async function initProject() {
      try {
        const res = await fetch(`${API_BASE}/projects/`);
        const data = await res.json();
        if (data && data.length > 0) {
          setProjectId(data[0].id);
        } else {
          // Create default project
          const createRes = await fetch(`${API_BASE}/projects/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: 'Demo Project', owner_id: 'user_123' })
          });
          const newProj = await createRes.json();
          setProjectId(newProj.id);
        }
      } catch (err) {
        console.error(err);
        setError("Failed to connect to backend API.");
      }
    }
    initProject();
  }, []);

  // 2. Poll job status
  useEffect(() => {
    let interval: number;
    if (jobId && jobStatus?.state !== 'succeeded' && jobStatus?.state !== 'failed') {
      interval = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE}/jobs/${jobId}`);
          const data = await res.json();
          setJobStatus(data);
        } catch (err) {
          console.error(err);
        }
      }, 2000) as unknown as number;
    }
    return () => clearInterval(interval);
  }, [jobId, jobStatus]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projectId || !url) return;
    setLoading(true);
    setError(null);
    setJobStatus(null);
    setJobId(null);

    try {
      // Create source
      const srcRes = await fetch(`${API_BASE}/sources/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: projectId, type: 'youtube', uri: url })
      });
      if (!srcRes.ok) throw new Error("Failed to create source");
      const source = await srcRes.json();

      // Trigger pipeline
      const jobRes = await fetch(`${API_BASE}/jobs/process`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ project_id: projectId, source_id: source.id })
      });
      if (!jobRes.ok) throw new Error("Failed to start pipeline");
      const job = await jobRes.json();
      
      setJobId(job.id);
      setJobStatus(job);
    } catch (err: any) {
      setError(err.message || "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container flex-col gap-6 fade-in">
      <header className="text-center" style={{ marginBottom: '2rem' }}>
        <h1 className="gradient-text">Clipper AI</h1>
        <p className="text-secondary" style={{ marginTop: '0.5rem', fontSize: '1.1rem' }}>
          Intelligent Long-form to Short-form Engine
        </p>
      </header>

      <main className="flex-col gap-6" style={{ maxWidth: '600px', margin: '0 auto', width: '100%' }}>
        <div className="glass-panel">
          <h2 style={{ marginBottom: '1.5rem', fontSize: '1.25rem' }}>Upload Media</h2>
          {error && (
            <div style={{ padding: '12px', background: 'rgba(239, 68, 68, 0.1)', color: 'var(--error)', borderRadius: '8px', marginBottom: '16px' }}>
              {error}
            </div>
          )}
          
          <form onSubmit={handleSubmit} className="flex gap-4">
            <input 
              type="url" 
              className="input-field" 
              placeholder="Paste YouTube URL here..." 
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
              disabled={loading || !!jobId}
            />
            <button 
              type="submit" 
              className="btn btn-primary" 
              disabled={loading || !projectId || !!jobId}
              style={{ minWidth: '120px' }}
            >
              {loading ? (
                <span className="flex items-center gap-2">
                  <svg className="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" strokeOpacity="0.25" />
                    <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="4" strokeLinecap="round" />
                  </svg>
                  Starting
                </span>
              ) : 'Generate'}
            </button>
          </form>
        </div>

        {jobStatus && (
          <div className="glass-panel fade-in">
            <div className="flex justify-between items-center" style={{ marginBottom: '1rem' }}>
              <h2 style={{ fontSize: '1.25rem' }}>Processing Status</h2>
              <span style={{ 
                padding: '4px 12px', 
                borderRadius: '999px', 
                fontSize: '0.875rem', 
                fontWeight: 600,
                background: jobStatus.state === 'succeeded' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(139, 92, 246, 0.1)',
                color: jobStatus.state === 'succeeded' ? 'var(--success)' : 'var(--accent-primary)'
              }}>
                {jobStatus.state.toUpperCase()}
              </span>
            </div>
            
            <div style={{ background: 'rgba(0,0,0,0.3)', padding: '16px', borderRadius: '8px', fontFamily: 'monospace', fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
              <div><strong style={{ color: 'var(--text-primary)' }}>Stage:</strong> {jobStatus.stage}</div>
              <div><strong style={{ color: 'var(--text-primary)' }}>Job ID:</strong> {jobStatus.id}</div>
              {jobStatus.metadata?.chain_id && (
                <div><strong style={{ color: 'var(--text-primary)' }}>Celery Chain:</strong> {jobStatus.metadata.chain_id}</div>
              )}
            </div>

            {jobStatus.state === 'succeeded' && (
              <div style={{ marginTop: '1.5rem', textAlign: 'center' }}>
                <p style={{ color: 'var(--success)', marginBottom: '1rem' }}>✨ Pipeline completed successfully!</p>
                <button 
                  className="btn btn-secondary"
                  onClick={() => {
                    setJobId(null);
                    setJobStatus(null);
                    setUrl('');
                  }}
                >
                  Process Another Video
                </button>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
