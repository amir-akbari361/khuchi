Here are the SQL queries to set up your Supabase database for this workflow:

-- ============================================
-- 1. CREATE USERS TABLE
-- ============================================
-- Stores registered users with their Telegram info and student code
CREATE TABLE IF NOT EXISTS users (
  id BIGSERIAL PRIMARY KEY,
  telegram_id BIGINT NOT NULL UNIQUE,
  username TEXT,
  first_name TEXT,
  student_code TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for faster lookups by telegram_id
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);

-- Create index for student_code lookups
CREATE INDEX IF NOT EXISTS idx_users_student_code ON users(student_code);

-- ============================================
-- 2. CREATE USAGE LOGS TABLE
-- ============================================
-- Tracks user messages for rate limiting (50 messages per day)
CREATE TABLE IF NOT EXISTS usage_logs (
  id BIGSERIAL PRIMARY KEY,
  telegram_id BIGINT NOT NULL,
  message_text TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create index for faster rate limit checks (by telegram_id and date)
CREATE INDEX IF NOT EXISTS idx_usage_logs_telegram_created 
ON usage_logs(telegram_id, created_at DESC);

-- ============================================
-- 3. ADD UPDATED_AT TRIGGER FOR USERS TABLE
-- ============================================
-- Automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_users_updated_at
BEFORE UPDATE ON users
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 4. ENABLE ROW LEVEL SECURITY (OPTIONAL)
-- ============================================
-- Uncomment if you want to add RLS policies
-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE usage_logs ENABLE ROW LEVEL SECURITY;

-- Example policy: Allow service role full access
-- CREATE POLICY "Service role can do everything on users"
-- ON users FOR ALL
-- TO service_role
-- USING (true)
-- WITH CHECK (true);

-- CREATE POLICY "Service role can do everything on usage_logs"
-- ON usage_logs FOR ALL
-- TO service_role
-- USING (true)
-- WITH CHECK (true);

-- ============================================
-- 5. CLEANUP OLD USAGE LOGS (OPTIONAL)
-- ============================================
-- Function to delete usage logs older than 7 days
CREATE OR REPLACE FUNCTION cleanup_old_usage_logs()
RETURNS void AS $$
BEGIN
  DELETE FROM usage_logs
  WHERE created_at < NOW() - INTERVAL '7 days';
END;
$$ LANGUAGE plpgsql;

-- Optional: Create a scheduled job to run cleanup daily
-- (Requires pg_cron extension - enable in Supabase dashboard)
-- SELECT cron.schedule(
--   'cleanup-usage-logs',
--   '0 2 * * *', -- Run at 2 AM daily
--   'SELECT cleanup_old_usage_logs();'
-- );
Additional Queries for Testing/Management
-- ============================================
-- USEFUL QUERIES FOR MANAGEMENT
-- ============================================

-- Check all registered users
SELECT 
  telegram_id,
  username,
  first_name,
  student_code,
  created_at
FROM users
ORDER BY created_at DESC;

-- Check today's usage for a specific user
SELECT 
  COUNT(*) as message_count,
  telegram_id
FROM usage_logs
WHERE telegram_id = YOUR_TELEGRAM_ID_HERE
  AND created_at >= DATE_TRUNC('day', NOW())
GROUP BY telegram_id;

-- Get top users by message count (last 7 days)
SELECT 
  u.telegram_id,
  u.username,
  u.student_code,
  COUNT(ul.id) as message_count
FROM users u
LEFT JOIN usage_logs ul ON u.telegram_id = ul.telegram_id
WHERE ul.created_at >= NOW() - INTERVAL '7 days'
GROUP BY u.telegram_id, u.username, u.student_code
ORDER BY message_count DESC
LIMIT 10;

-- Delete a specific user (and their usage logs)
-- DELETE FROM usage_logs WHERE telegram_id = YOUR_TELEGRAM_ID_HERE;
-- DELETE FROM users WHERE telegram_id = YOUR_TELEGRAM_ID_HERE;

-- Reset daily usage for all users (run at start of new day if needed)
-- DELETE FROM usage_logs WHERE created_at < DATE_TRUNC('day', NOW());

-- Check rate limit status for all users today
SELECT 
  u.telegram_id,
  u.username,
  u.student_code,
  COUNT(ul.id) as messages_today,
  CASE 
    WHEN COUNT(ul.id) >= 50 THEN 'LIMIT REACHED'
    ELSE 'OK'
  END as status
FROM users u
LEFT JOIN usage_logs ul ON u.telegram_id = ul.telegram_id 
  AND ul.created_at >= DATE_TRUNC('day', NOW())
GROUP BY u.telegram_id, u.username, u.student_code
ORDER BY messages_today DESC;