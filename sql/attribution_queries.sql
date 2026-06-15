-- ============================================
-- Multi-Touch Attribution SQL Queries
-- Infotact Internship | Week 2
-- ============================================

-- STEP 1: user_journeys VIEW
-- ROW_NUMBER() Window Function sequences each
-- user's touchpoints before their conversion
CREATE VIEW user_journeys AS
SELECT
    t.log_id,
    t.user_id,
    t.timestamp          AS touch_time,
    t.channel,
    t.campaign,
    t.touch_seq,
    t.total_touches,
    t.touch_position,
    c.conversion_id,
    c.converted_at,
    c.revenue,
    ROUND(1.0 / t.total_touches, 6)                             AS linear_weight,
    CASE WHEN t.touch_position='first' THEN 1.0 ELSE 0.0 END   AS first_touch_weight,
    CASE WHEN t.touch_position='last'  THEN 1.0 ELSE 0.0 END   AS last_touch_weight
FROM touchpoints t
INNER JOIN conversions c
    ON  t.user_id    = c.user_id
    AND t.timestamp <= c.converted_at;

-- STEP 2: FIRST-TOUCH ATTRIBUTION
SELECT
    channel,
    SUM(revenue * first_touch_weight)                    AS attributed_revenue,
    COUNT(DISTINCT conversion_id)                        AS conversions,
    ROUND(SUM(revenue * first_touch_weight)
        / SUM(SUM(revenue * first_touch_weight)) OVER()
        * 100, 2)                                        AS pct_credit
FROM user_journeys
GROUP BY channel
ORDER BY attributed_revenue DESC;

-- STEP 3: LAST-TOUCH ATTRIBUTION
SELECT
    channel,
    SUM(revenue * last_touch_weight)                     AS attributed_revenue,
    COUNT(DISTINCT conversion_id)                        AS conversions,
    ROUND(SUM(revenue * last_touch_weight)
        / SUM(SUM(revenue * last_touch_weight)) OVER()
        * 100, 2)                                        AS pct_credit
FROM user_journeys
GROUP BY channel
ORDER BY attributed_revenue DESC;

-- STEP 4: LINEAR ATTRIBUTION
SELECT
    channel,
    ROUND(SUM(revenue * linear_weight), 2)               AS attributed_revenue,
    COUNT(DISTINCT conversion_id)                        AS conversions,
    ROUND(SUM(revenue * linear_weight)
        / SUM(SUM(revenue * linear_weight)) OVER()
        * 100, 2)                                        AS pct_credit
FROM user_journeys
GROUP BY channel
ORDER BY attributed_revenue DESC;
