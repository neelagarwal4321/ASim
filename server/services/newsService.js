const axios = require('axios')
const logger = require('./logger')

const FALLBACK = [
  { scenario: 'Universal Basic Income mandate', source: null },
  { scenario: 'AGI released to the public', source: null },
  { scenario: 'Private car ownership banned in cities', source: null },
]

const BLOCKLIST = [
  'sport', 'celebrity', 'entertainment', 'stock market', 'earnings', 'weather',
  'obituary', 'fashion', 'recipe', 'box office', 'nfl', 'nba', 'fifa',
]

const KEYWORDS = [
  'ban', 'crisis', 'debate', 'law', 'policy', 'mandate', 'rights', 'protest',
  'vote', ' ai ', 'artificial intelligence', 'climate', 'tax', 'war', 'conflict',
  'reform', 'shortage', 'pandemic', 'regulation', 'court', 'election',
  'surveillance', 'inequality', 'collapse', 'sanction', 'treaty', 'strike',
  'immigration', 'censorship', 'privacy', 'monopoly', 'nuclear', 'genocide',
  'discrimination', 'healthcare', 'housing', 'inflation', 'unemployment',
]

function scoreArticle(article) {
  const text = ((article.title || '') + ' ' + (article.description || '')).toLowerCase()
  if (BLOCKLIST.some(w => text.includes(w))) return -Infinity
  return KEYWORDS.filter(w => text.includes(w)).length
}

function cleanHeadline(title) {
  // NewsAPI appends " - Source Name" to titles
  return title.replace(/\s*-\s*[^-]+$/, '').trim()
}

async function fetchFiltered(count = 3) {
  const key = process.env.NEWS_API_KEY
  if (!key) {
    logger.warn('NEWS_API_KEY not set — returning fallback suggestions')
    return FALLBACK.slice(0, count)
  }

  const categories = ['politics', 'technology', 'science', 'health', 'general']
  const allArticles = []

  for (const category of categories) {
    try {
      const res = await axios.get('https://newsapi.org/v2/top-headlines', {
        params: { category, language: 'en', pageSize: 10 },
        headers: { 'X-Api-Key': key },
        timeout: 8000,
      })
      if (res.data?.articles) allArticles.push(...res.data.articles)
    } catch (err) {
      logger.warn(`newsService: failed fetching category ${category}: ${err.message}`)
    }
  }

  if (!allArticles.length) {
    logger.warn('newsService: no articles fetched — returning fallback')
    return FALLBACK.slice(0, count)
  }

  const scored = allArticles
    .filter(a => a.title && a.title !== '[Removed]')
    .map(a => ({ article: a, score: scoreArticle(a) }))
    .filter(({ score }) => score > 0)
    .sort((a, b) => b.score - a.score)

  const results = scored.slice(0, count).map(({ article }) => ({
    scenario: cleanHeadline(article.title),
    source: article.source?.name || null,
  }))

  // Pad with fallback if not enough qualifying articles
  const fallbackNeeded = count - results.length
  if (fallbackNeeded > 0) {
    results.push(...FALLBACK.slice(0, fallbackNeeded))
  }

  return results
}

module.exports = { fetchFiltered, FALLBACK }
