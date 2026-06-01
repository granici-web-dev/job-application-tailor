import { useCallback, useEffect, useState } from 'react'
import {
  Application,
  downloadFile,
  fetchApplications,
  setApplicationStatus,
  setApplicationVisibility,
  STATUS_NOT_SENT,
  STATUS_SENT,
} from '../api'
import { DownloadIcon, ExternalLinkIcon, EyeIcon, EyeOffIcon } from '../icons'

type Tab = 'active' | 'hidden'

const EMPLOYMENT_LABELS: Record<string, string> = {
  remote: 'Удалённо',
  onsite: 'Офис',
  hybrid: 'Гибрид',
  unknown: 'н/д',
}

export function ApplicationsPage() {
  const [applications, setApplications] = useState<Application[]>([])
  const [tab, setTab] = useState<Tab>('active')
  const [loading, setLoading] = useState(true)
  const [fetchError, setFetchError] = useState('')
  const [pendingId, setPendingId] = useState<number | null>(null)
  const [toast, setToast] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setFetchError('')
    try {
      const data = await fetchApplications(true)
      setApplications(data)
    } catch (caught) {
      setFetchError(caught instanceof Error ? caught.message : 'Не удалось загрузить заявки.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (!toast) {
      return
    }
    const timer = window.setTimeout(() => setToast(''), 4000)
    return () => window.clearTimeout(timer)
  }, [toast])

  async function toggleStatus(application: Application) {
    const next = application.status === STATUS_SENT ? STATUS_NOT_SENT : STATUS_SENT
    setApplications((prev) => prev.map((row) => (row.id === application.id ? { ...row, status: next } : row)))
    setPendingId(application.id)
    try {
      await setApplicationStatus(application.id, next)
    } catch (caught) {
      setApplications((prev) =>
        prev.map((row) => (row.id === application.id ? { ...row, status: application.status } : row)),
      )
      setToast(caught instanceof Error ? caught.message : 'Не удалось сохранить статус. Изменение отменено.')
    } finally {
      setPendingId(null)
    }
  }

  async function toggleVisibility(application: Application) {
    const nextHidden = !application.hidden
    setPendingId(application.id)
    setApplications((prev) =>
      prev.map((row) => (row.id === application.id ? { ...row, hidden: nextHidden } : row)),
    )
    try {
      await setApplicationVisibility(application.id, nextHidden)
      await load()
    } catch (caught) {
      await load()
      setToast(caught instanceof Error ? caught.message : 'Не удалось сохранить. Изменение отменено.')
    } finally {
      setPendingId(null)
    }
  }

  async function onDownload(path: string) {
    try {
      await downloadFile(path)
    } catch (caught) {
      setToast(caught instanceof Error ? caught.message : 'Не удалось скачать файл.')
    }
  }

  const visible = applications.filter((row) => (tab === 'hidden' ? row.hidden : !row.hidden))

  return (
    <main className="page">
      <div className="page-head">
        <h1>Заявки</h1>
        <p className="subhead">История сгенерированных заявок. Статус синхронизируется с Excel-трекером.</p>
      </div>

      <div className="toolbar">
        <div className="segmented" role="group" aria-label="Фильтр заявок">
          <button
            type="button"
            className={tab === 'active' ? 'is-active' : ''}
            aria-pressed={tab === 'active'}
            onClick={() => setTab('active')}
          >
            Активные
          </button>
          <button
            type="button"
            className={tab === 'hidden' ? 'is-active' : ''}
            aria-pressed={tab === 'hidden'}
            onClick={() => setTab('hidden')}
          >
            Скрытые
          </button>
        </div>
      </div>

      {loading ? (
        <LoadingTable />
      ) : fetchError ? (
        <section className="notice notice-error" role="alert">
          {fetchError}{' '}
          <button type="button" className="btn btn-sm btn-ghost" onClick={() => load()}>
            Повторить
          </button>
        </section>
      ) : visible.length === 0 ? (
        <div className="state-block">
          {tab === 'hidden' ? (
            <strong>Нет скрытых заявок</strong>
          ) : (
            <>
              <strong>Заявок пока нет</strong>
              Сгенерируйте первую на странице «Сгенерировать».
            </>
          )}
        </div>
      ) : (
        <div className="table-wrap">
          <table className="app-table">
            <thead>
              <tr>
                <th>Фирма</th>
                <th>Сотрудники</th>
                <th>Вакансия</th>
                <th>Тип</th>
                <th>Должность</th>
                <th>Город</th>
                <th>Статус</th>
                <th>Дата</th>
                <th aria-label="Действия" />
              </tr>
            </thead>
            <tbody>
              {visible.map((application) => (
                <ApplicationRow
                  key={application.id}
                  application={application}
                  pending={pendingId === application.id}
                  onToggleStatus={() => toggleStatus(application)}
                  onToggleVisibility={() => toggleVisibility(application)}
                  onDownload={onDownload}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {toast && (
        <div className="toast" role="status" aria-live="polite">
          {toast}
        </div>
      )}
    </main>
  )
}

interface RowProps {
  application: Application
  pending: boolean
  onToggleStatus: () => void
  onToggleVisibility: () => void
  onDownload: (path: string) => void
}

function ApplicationRow({ application, pending, onToggleStatus, onToggleVisibility, onDownload }: RowProps) {
  const sent = application.status === STATUS_SENT
  return (
    <tr>
      <td className="company">{application.company_name}</td>
      <td>{application.employee_count || 'н/д'}</td>
      <td>
        <a className="ext-link" href={application.job_url} target="_blank" rel="noopener noreferrer">
          Открыть
          <ExternalLinkIcon />
        </a>
      </td>
      <td>{EMPLOYMENT_LABELS[application.employment_type] ?? application.employment_type}</td>
      <td className="title-cell">{application.job_title}</td>
      <td className="cell-city" title={application.location ?? undefined}>
        {application.location ?? '—'}
      </td>
      <td>
        <button
          type="button"
          className={sent ? 'pill pill-sent' : 'pill pill-unsent'}
          onClick={onToggleStatus}
          disabled={pending}
          aria-label={`Статус: ${application.status}. Нажмите, чтобы переключить.`}
        >
          <span className="pill-dot" />
          {application.status}
        </button>
      </td>
      <td className="cell-date">{formatDate(application.created_on)}</td>
      <td>
        <div className="row-actions">
          <button
            type="button"
            className="btn btn-sm btn-ghost"
            disabled={!application.files}
            title={application.files ? undefined : 'Файл недоступен. Сгенерируйте заявку заново.'}
            onClick={() => application.files && onDownload(application.files.cv)}
          >
            <DownloadIcon />
            CV
          </button>
          <button
            type="button"
            className="btn btn-sm btn-ghost"
            disabled={!application.files}
            title={application.files ? undefined : 'Файл недоступен. Сгенерируйте заявку заново.'}
            onClick={() => application.files && onDownload(application.files.cover_letter)}
          >
            <DownloadIcon />
            Письмо
          </button>
          <button
            type="button"
            className="btn btn-sm btn-ghost"
            onClick={onToggleVisibility}
            disabled={pending}
          >
            {application.hidden ? <EyeIcon /> : <EyeOffIcon />}
            {application.hidden ? 'Показать' : 'Скрыть'}
          </button>
        </div>
      </td>
    </tr>
  )
}

function LoadingTable() {
  return (
    <div className="table-wrap" aria-hidden>
      {Array.from({ length: 5 }).map((_, index) => (
        <div key={index} className="skeleton-row" />
      ))}
    </div>
  )
}

function formatDate(value: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value)
  if (!match) {
    return value
  }
  return `${match[3]}.${match[2]}.${match[1]}`
}
