// 资讯中心面板
import { useStore } from '../stores/useStore'
import NewsItem from './NewsItem'

export default function NewsPanel() {
  const news = useStore((s) => s.news)

  return (
    <div className="news-panel">
      <h2>资讯中心</h2>
      <div className="news-list">
        {news.length === 0 && <p className="empty">暂无新闻，等待生成...</p>}
        {news.map((n) => (
          <NewsItem key={n.news_id} news={n} />
        ))}
      </div>
    </div>
  )
}
