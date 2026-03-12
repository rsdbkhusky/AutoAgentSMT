// 单条新闻组件
import type { NewsEvent } from '../types'

const sentimentLabels: Record<string, { text: string; className: string }> = {
  positive: { text: '利好', className: 'positive' },
  negative: { text: '利空', className: 'negative' },
  neutral: { text: '中性', className: 'neutral' },
}

export default function NewsItem({ news }: { news: NewsEvent }) {
  const sentiment = sentimentLabels[news.sentiment] || sentimentLabels.neutral

  return (
    <div className="news-item">
      <div className="news-header">
        <span className={`sentiment-tag ${sentiment.className}`}>{sentiment.text}</span>
        <span className="news-time">{news.virtual_time}</span>
      </div>
      <h4 className="news-title">{news.title}</h4>
      <p className="news-content">{news.content}</p>
      {news.affected_stocks.length > 0 && (
        <div className="affected-stocks">
          {news.affected_stocks.map((code) => (
            <span key={code} className="stock-tag">{code}</span>
          ))}
        </div>
      )}
    </div>
  )
}
