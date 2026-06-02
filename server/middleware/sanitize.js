// Module-level compiled patterns — O(1) per check, patterns don't reallocate
const INJECTION_PATTERNS = [
  /system:/i,
  /\[INST\]/i,
  /<<SYS>>/i,
  /ignore (?:previous|above|all) instructions/i,
  /you are now (?:a|an) /i,
  /disregard (?:your|all) (?:previous|prior)/i,
];

function sanitizeScenario(req, res, next) {
  const scenario = req.body?.scenario;
  if (!scenario) return next();
  const stripped = scenario.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '');
  if (stripped.length > 2000) {
    return res.status(422).json({ error: 'Scenario exceeds 2000 character limit', code: 'VALIDATION_ERROR' });
  }
  for (const pattern of INJECTION_PATTERNS) {
    if (pattern.test(stripped)) {
      return res.status(422).json({ error: 'Scenario contains disallowed content', code: 'VALIDATION_ERROR' });
    }
  }
  req.body.scenario = stripped.trim();
  next();
}

module.exports = { sanitizeScenario };
