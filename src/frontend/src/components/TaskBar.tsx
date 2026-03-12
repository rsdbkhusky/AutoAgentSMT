// 底部任务栏 - 切换三个面板
import { useStore, PanelType } from '../stores/useStore'

const panels: { key: PanelType; label: string }[] = [
  { key: 'trade', label: '交易终端' },
  { key: 'chat', label: '交流群' },
  { key: 'news', label: '资讯中心' },
]

export default function TaskBar() {
  const activePanel = useStore((s) => s.activePanel)

  return (
    <div className="task-bar">
      {panels.map((p) => (
        <button
          key={p.key}
          className={`task-btn ${activePanel === p.key ? 'active' : ''}`}
          onClick={() => useStore.getState().setActivePanel(p.key)}
        >
          {p.label}
        </button>
      ))}
    </div>
  )
}
