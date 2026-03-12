// Agent 持仓排行表
import { useStore } from '../stores/useStore'

export default function PositionTable() {
  const positions = useStore((s) => s.positions)

  // 按总资产降序排列
  const sorted = [...positions].sort((a, b) => b.total_value - a.total_value)

  return (
    <div className="position-table">
      <h3>Agent 资产排行</h3>
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>排名</th>
              <th>名称</th>
              <th>类型</th>
              <th>总资产</th>
              <th>盈亏</th>
              <th>持仓</th>
            </tr>
          </thead>
          <tbody>
            {sorted.slice(0, 20).map((p, i) => (
              <tr key={p.agent_id}>
                <td>{i + 1}</td>
                <td>{p.agent_name}</td>
                <td><span className={`type-tag ${p.agent_type}`}>{p.agent_type}</span></td>
                <td>¥{p.total_value.toLocaleString(undefined, { minimumFractionDigits: 0 })}</td>
                <td className={p.pnl_pct >= 0 ? 'up' : 'down'}>
                  {p.pnl_pct >= 0 ? '+' : ''}{p.pnl_pct.toFixed(2)}%
                </td>
                <td className="positions-cell">
                  {Object.entries(p.positions).map(([code, qty]) => (
                    <span key={code} className="pos-tag">{code}:{qty}</span>
                  ))}
                  {Object.keys(p.positions).length === 0 && <span className="no-pos">空仓</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
