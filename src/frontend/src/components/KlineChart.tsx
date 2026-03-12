// K线图组件 (基于 lightweight-charts)
import { useEffect, useRef } from 'react'
import { createChart, IChartApi, ISeriesApi, CandlestickData } from 'lightweight-charts'
import { useStore } from '../stores/useStore'

export default function KlineChart() {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)

  const selectedStock = useStore((s) => s.selectedStock)
  const klines = useStore((s) => s.klines[s.selectedStock] || [])

  // 创建图表
  useEffect(() => {
    if (!containerRef.current) return

    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: '#1a1a2e' },
        textColor: '#e0e0e0',
      },
      grid: {
        vertLines: { color: '#2a2a4a' },
        horzLines: { color: '#2a2a4a' },
      },
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
      },
      crosshair: {
        mode: 0,
      },
    })

    const series = chart.addCandlestickSeries({
      upColor: '#ef5350',      // 中国股市：红涨
      downColor: '#26a69a',    // 绿跌
      borderUpColor: '#ef5350',
      borderDownColor: '#26a69a',
      wickUpColor: '#ef5350',
      wickDownColor: '#26a69a',
    })

    chartRef.current = chart
    seriesRef.current = series

    const resizeObserver = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        })
      }
    })
    resizeObserver.observe(containerRef.current)

    return () => {
      resizeObserver.disconnect()
      chart.remove()
    }
  }, [])

  // 更新数据
  useEffect(() => {
    if (!seriesRef.current || klines.length === 0) return

    const data: CandlestickData[] = klines.map((bar) => ({
      time: bar.timestamp as any,
      open: bar.open,
      high: bar.high,
      low: bar.low,
      close: bar.close,
    }))

    seriesRef.current.setData(data)
    chartRef.current?.timeScale().fitContent()
  }, [klines, selectedStock])

  return <div ref={containerRef} className="kline-chart" />
}
