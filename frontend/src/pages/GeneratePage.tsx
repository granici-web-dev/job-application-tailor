import { FormEvent, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ApiError,
  CONTACT_MISSING,
  downloadFile,
  generateApplication,
  GenerateInput,
  GenerateResult,
  JOB_TEXT_MISSING,
  JOB_TITLE_MISSING,
} from '../api'
import { DownloadIcon } from '../icons'

type Phase = 'idle' | 'loading' | 'success' | 'error'

const LOADING_STEPS = ['Анализ вакансии', 'Адаптация CV и письма', 'Рендеринг PDF']

export function GeneratePage() {
  const [url, setUrl] = useState('')
  const [text, setText] = useState('')
  const [showText, setShowText] = useState(false)
  const [phase, setPhase] = useState<Phase>('idle')
  const [result, setResult] = useState<GenerateResult | null>(null)
  const [error, setError] = useState('')
  const [needsJobTitle, setNeedsJobTitle] = useState(false)
  const [jobTitle, setJobTitle] = useState('')
  const [downloadError, setDownloadError] = useState('')
  const [elapsed, setElapsed] = useState(0)
  const [needsText, setNeedsText] = useState(false)
  // The title entered by hand stays for the next attempt, which asks for the recipient.
  const [manualTitle, setManualTitle] = useState<string | undefined>(undefined)
  const [needsContact, setNeedsContact] = useState(false)
  const [contactPerson, setContactPerson] = useState('')
  const [address, setAddress] = useState('')
  const textArea = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (needsText) {
      textArea.current?.focus()
    }
  }, [needsText])

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

  function onSubmit(event: FormEvent) {
    event.preventDefault()
    setNeedsJobTitle(false)
    setJobTitle('')
    setManualTitle(undefined)
    setNeedsContact(false)
    void generate()
  }

  function onSubmitJobTitle(event: FormEvent) {
    event.preventDefault()
    if (jobTitle.trim()) {
      setManualTitle(jobTitle.trim())
      void generate(jobTitle.trim())
    }
  }

  function onSubmitContact(event: FormEvent) {
    event.preventDefault()
    // Both may stay empty: the letter then greets "Sehr geehrte Damen und Herren" and names the city.
    void generate(manualTitle, { contact_person: contactPerson.trim(), address: address.trim() })
  }

  async function generate(manualJobTitle?: string, contact?: { contact_person: string; address: string }) {
    const trimmed = url.trim()
    const trimmedText = text.trim()
    // Pasted text is the posting whatever the link, so it goes without one too.
    if (!trimmed && !trimmedText) {
      return
    }
    setPhase('loading')
    setError('')
    setResult(null)
    setDownloadError('')
    setNeedsText(false)
    try {
      const payload: GenerateInput = { url: trimmed, ...contact }
      if (trimmedText) {
        payload.text = trimmedText
      }
      if (manualJobTitle) {
        payload.job_title = manualJobTitle
      }
      const data = await generateApplication(payload)
      setNeedsJobTitle(false)
      setNeedsContact(false)
      setResult(data)
      setPhase('success')
    } catch (caught) {
      setNeedsJobTitle(caught instanceof ApiError && caught.code === JOB_TITLE_MISSING)
      setNeedsContact(caught instanceof ApiError && caught.code === CONTACT_MISSING)
      if (caught instanceof ApiError && caught.code === CONTACT_MISSING) {
        const found = caught.data
        setContactPerson(typeof found.contact_person === 'string' ? found.contact_person : '')
        setAddress(typeof found.address === 'string' ? found.address : '')
      }
      if (caught instanceof ApiError && caught.code === JOB_TEXT_MISSING) {
        setShowText(true)
        setNeedsText(true)
      }
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

      <form className="generate-form" onSubmit={onSubmit} noValidate>
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
        <button type="submit" className="btn btn-primary" disabled={loading || (url.trim() === '' && text.trim() === '')}>
          {loading ? 'Генерация…' : 'Сгенерировать'}
        </button>
      </form>

      <button
        type="button"
        className="text-toggle"
        aria-expanded={showText}
        aria-controls="job-text"
        onClick={() => setShowText((open) => !open)}
        disabled={loading}
      >
        {showText ? 'Скрыть ручной ввод' : 'Сайт не открывается? Вставить описание вручную'}
      </button>

      {showText && (
        <div className="manual-text">
          <label htmlFor="job-text" className="manual-label">
            Текст вакансии
          </label>
          <p id="job-text-hint" className="manual-hint">
            Если страница не скачивается (Indeed, LinkedIn, SPA), вставьте описание вручную. Текст заменяет
            страницу по ссылке; ссылку можно не указывать, а указанная сохранится в трекере.
          </p>
          <textarea
            ref={textArea}
            id="job-text"
            className="text-area"
            rows={8}
            placeholder="Вставьте полный текст вакансии"
            value={text}
            onChange={(event) => setText(event.target.value)}
            disabled={loading}
            aria-describedby="job-text-hint"
          />
        </div>
      )}

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

      {needsJobTitle && !loading && (
        <form className="generate-form" onSubmit={onSubmitJobTitle}>
          <div className="field">
            <input
              id="job-title"
              className="text-input"
              type="text"
              aria-label="Название позиции"
              placeholder="Название позиции"
              value={jobTitle}
              onChange={(event) => setJobTitle(event.target.value)}
              autoComplete="off"
              autoFocus
            />
          </div>
          <button type="submit" className="btn btn-primary" disabled={jobTitle.trim() === ''}>
            Сгенерировать
          </button>
        </form>
      )}

      {needsContact && !loading && (
        <form className="contact-form" onSubmit={onSubmitContact}>
          <div className="field">
            <label htmlFor="contact-person" className="manual-label">
              Ansprechpartner
            </label>
            <input
              id="contact-person"
              className="text-input"
              type="text"
              placeholder="Frau Anna Müller"
              value={contactPerson}
              onChange={(event) => setContactPerson(event.target.value)}
              autoComplete="off"
              autoFocus
            />
          </div>
          <div className="field">
            <label htmlFor="contact-address" className="manual-label">
              Adresse
            </label>
            <input
              id="contact-address"
              className="text-input"
              type="text"
              placeholder="Musterstraße 1, 50667 Köln"
              value={address}
              onChange={(event) => setAddress(event.target.value)}
              autoComplete="off"
            />
          </div>
          <button type="submit" className="btn btn-primary">
            Сгенерировать
          </button>
        </form>
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
