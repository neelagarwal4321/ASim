const express = require('express')
const { getClient } = require('../services/redisService')
const { fetchFiltered, FALLBACK } = require('../services/newsService')
const logger = require('../services/logger')

const router = express.Router()

const CACHE_KEY = 'scenarios:suggestions'
const CACHE_TTL = 7200 // 2 hours

router.get('/suggestions', async (req, res) => {
  // Try Redis cache
  try {
    const cached = await getClient().get(CACHE_KEY)
    if (cached) {
      try {
        return res.json({ suggestions: JSON.parse(cached) })
      } catch {
        // Corrupted cache entry — delete and fall through to fetch
        await getClient().del(CACHE_KEY).catch(() => {})
      }
    }
  } catch (err) {
    logger.warn(`scenarios: Redis read failed: ${err.message}`)
  }

  // Cache miss — fetch live
  let suggestions
  try {
    suggestions = await fetchFiltered(3)
  } catch (err) {
    logger.warn(`scenarios: fetchFiltered failed: ${err.message}`)
    suggestions = FALLBACK
  }

  // Write to cache (non-blocking, failure is OK)
  try {
    await getClient().set(CACHE_KEY, JSON.stringify(suggestions), 'EX', CACHE_TTL)
  } catch (err) {
    logger.warn(`scenarios: Redis write failed: ${err.message}`)
  }

  res.json({ suggestions })
})

module.exports = router
