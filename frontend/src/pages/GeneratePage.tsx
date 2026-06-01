import { FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { downloadFile, generateApplication, GenerateResult } from '../api'
import { DownloadIcon } from '../icons'

type Phase = 'idle' | 'loading' | 'success' | 'error'

const LOADING_STEPS = ['Анализ вакансии', 'Адаптация CV и письма', 'Рендеринг PDF']

export function GeneratePage() {
  const [url, setUrl] = useState('')
  const [phase, setPhase] = useState<Phase>('idle')
  const [result, setResult] = useState<GenerateResult | null>(null)
  const [error, setError] = useState('')
  const [downloadError, setDownloadError] = useState('')
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    if (phase !== 'loading') {
      return
    }
    setElapsed(0)
    const startedAt = performance.now()
    const timer = window.setInterval(() => {
      setElapsed(Math.floor((performance.now() - startedAt) / 1000))
    }, 1000)
    return () => window.clearInterval(timer)
  }, [phase])

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    const trimmed = url.trim()
    if (!trimmed) {
      return
    }
    setPhase('loading')
    setError('')
    setResult(null)
    setDownloadError('')
    try {
      const data = await generateApplication({ url: trimmed })
      setResult(data)
      setPhase('success')
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Не удалось сгенерировать заявку.')
      setPhase('error')
    }
  }

  async function onDownload(path: string) {
    setDownloadError('')
    try {
      await downloadFile(path)
    } catch (caught) {
      setDownloadError(caught instanceof Error ? caught.message : 'Не удалось скачать файл.')
    }
  }

  const loading = phase === 'loading'

  return (
    <main className="page page-narrow">
      <div className="page-head">
        <h1>Сгенерировать заявку</h1>
        <p className="subhead">
          Вставьте ссылку на вакансию. CV и сопроводительное письмо адаптируются под неё на её языке,
          из вашего мастер-CV.
        </p>
      </div>

      <form className="generate-form" onSubmit={onSubmit}>
        <div className="field">
          <input
            id="job-url"
            className="text-input"
            type="url"
            inputMode="url"
            aria-label="Ссылка на вакансию"
            placeholder="https://example.com/jobs/12345"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            disabled={loading}
            autoComplete="off"
          />
        </div>
        <button type="submit" className="btn btn-primary" disabled={loading || url.trim() === ''}>
          {loading ? 'Генерация…' : 'Сгенерировать'}
        </button>
      </form>

      {loading && (
        <section className="loading-block" aria-live="polite">
          <div className="loading-head">
            <span className="loading-title">Генерация заявки</span>
            <span className="elapsed">{elapsed} с</span>
          </div>
          <ul className="steps">
            {LOADING_STEPS.map((step) => (
              <li key={step}>
                <span className="step-dot" />
                {step}
              </li>
            ))}
          </ul>
          <p className="loading-note">Обычно занимает 30-60 секунд. Не закрывайте вкладку.</p>
        </section>
      )}

      {phase === 'error' && (
        <section className="notice notice-error" role="alert">
          {error}
        </section>
      )}

      {phase === 'success' && result && (
        <section className="result-block" aria-live="polite">
          <h2>{result.analysis.company_name}</h2>
          <p className="position">{result.analysis.job_title}</p>
          <div className="result-actions">
            <button type="button" className="btn btn-primary" onClick={() => onDownload(result.files.cv)}>
              <DownloadIcon />
              Скачать CV
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => onDownload(result.files.cover_letter)}
            >
              <DownloadIcon />
              Скачать письмо
            </button>
          </div>
          {downloadError && <p className="inline-error">{downloadError}</p>}
          <div className="result-foot">
            <Link to="/applications">Открыть в истории</Link>
          </div>
        </section>
      )}
    </main>
  )
}
