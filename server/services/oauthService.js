const passport = require('passport');
const { Strategy: GoogleStrategy } = require('passport-google-oauth20');
const { Strategy: GitHubStrategy } = require('passport-github2');
const { query } = require('../db/client');
const { signAccess, signRefresh } = require('./jwtService');

function setupOAuth(app) {
  app.use(passport.initialize());

  if (process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET) {
    passport.use(new GoogleStrategy({
      clientID: process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET,
      callbackURL: `${process.env.OAUTH_CALLBACK_BASE}/api/v1/auth/oauth/google/callback`,
    }, async (accessToken, refreshToken, profile, done) => {
      try {
        const user = await findOrCreateOAuthUser('google', profile.id, profile.emails[0].value, profile.displayName);
        done(null, user);
      } catch (err) { done(err); }
    }));
  }

  if (process.env.GITHUB_CLIENT_ID && process.env.GITHUB_CLIENT_SECRET) {
    passport.use(new GitHubStrategy({
      clientID: process.env.GITHUB_CLIENT_ID,
      clientSecret: process.env.GITHUB_CLIENT_SECRET,
      callbackURL: `${process.env.OAUTH_CALLBACK_BASE}/api/v1/auth/oauth/github/callback`,
    }, async (accessToken, refreshToken, profile, done) => {
      try {
        const email = profile.emails?.[0]?.value || `${profile.username}@github.local`;
        const user = await findOrCreateOAuthUser('github', profile.id, email, profile.displayName || profile.username);
        done(null, user);
      } catch (err) { done(err); }
    }));
  }
}

async function findOrCreateOAuthUser(provider, providerUserId, email, displayName) {
  // Check if oauth account exists
  const existing = await query(
    'SELECT u.* FROM users u JOIN oauth_accounts oa ON u.id = oa.user_id WHERE oa.provider=$1 AND oa.provider_user_id=$2',
    [provider, String(providerUserId)]
  );
  if (existing.rows.length) return existing.rows[0];

  // Check if user exists by email
  let user;
  const byEmail = await query('SELECT * FROM users WHERE email=$1 AND deleted_at IS NULL', [email]);
  if (byEmail.rows.length) {
    user = byEmail.rows[0];
  } else {
    const created = await query(
      'INSERT INTO users(email, display_name) VALUES($1,$2) RETURNING *',
      [email, displayName]
    );
    user = created.rows[0];
  }

  await query(
    'INSERT INTO oauth_accounts(user_id, provider, provider_user_id) VALUES($1,$2,$3) ON CONFLICT DO NOTHING',
    [user.id, provider, String(providerUserId)]
  );
  return user;
}

module.exports = { setupOAuth };
