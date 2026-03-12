// 交易终端面板
import StockSelector from './StockSelector'
import KlineChart from './KlineChart'
import OrderBookPanel from './OrderBookPanel'
import PositionTable from './PositionTable'

export default function TradeTerminal() {
  return (
    <div className="trade-terminal">
      <StockSelector />
      <div className="terminal-grid">
        <div className="chart-area">
          <KlineChart />
        </div>
        <div className="side-area">
          <OrderBookPanel />
        </div>
      </div>
      <PositionTable />
    </div>
  )
}
