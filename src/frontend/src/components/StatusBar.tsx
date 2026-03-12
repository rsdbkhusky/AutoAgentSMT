// 顶部状态栏
import { useStore } from '../stores/useStore'
import { pauseSimulation, resumeSimulation } from '../api'

export default function StatusBar() {
  const virtualTime = useStore((s) => s.virtualTime)
  const roundNumber = useStore((s) => s.roundNumber)
  const status = useStore((s) => s.status)

  const handleToggle = async () => {
    if (status === 'running') {
      await pauseSimulation()
      useStore.getState().setStatus('paused')
    } else {
      await resumeSimulation()
      useStore.getState().setStatus('running')
    }
  }

  return (
    <div className="status-bar">
      <div className="status-item">
        <span className="label">虚拟时间</span>
        <span className="value">{virtualTime || '--'}</span>
      </div>
      <div className="status-item">
        <span className="label">回合</span>
        <span className="value">{roundNumber}</span>
      </div>
      <div className="status-item">
        <span className={`status-dot ${status}`} />
        <span className="value">{status === 'running' ? '运行中' : status === 'paused' ? '已暂停' : '已停止'}</span>
      </div>
      <button className="control-btn" onClick={handleToggle}>
        {status === 'running' ? '暂停' : '恢复'}
      </button>
    </div>
  )
}
