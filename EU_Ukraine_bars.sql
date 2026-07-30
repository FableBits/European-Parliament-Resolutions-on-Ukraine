-- The table eukraine_big_file has all the votes from the 65 resolutions related to the aid to
-- Ukraine, as collected from howtheyvote.eu> With the table ukraine_votes, we will create the
-- interactive chart in python, where the user will be able to see the share of votes by 
-- political group, and filter by country and category 


DROP TABLE IF EXISTS eukraine_big_file;

SELECT * FROM eukraine_big_file;

SELECT DISTINCT `KEY` FROM eukraine_big_file
GROUP BY `key`
HAVING count(*) = 1;

DROP TABLE IF EXISTS eukraine1;

CREATE TABLE eukraine1 AS
SELECT * FROM eukraine_big_file;

SELECT * FROM eukraine1;

SELECT DISTINCT pr_key FROM eukraine1;

DROP TABLE IF EXISTS ukraine_votes;

CREATE TABLE ukraine_votes AS
WITH
positions AS (
    SELECT 'VotePosition.FOR' AS position
    UNION ALL SELECT 'VotePosition.AGAINST'
    UNION ALL SELECT 'VotePosition.ABSTENTION'
    UNION ALL SELECT 'VotePosition.DID_NOT_VOTE'
),
base AS (
    SELECT DISTINCT
        `pr_key`,
        `member.group.label` AS political_group,
        `Category`,
        `member.country.label` AS country
    FROM eukraine1
),
counts AS (
    SELECT
        `pr_key`,
        `member.group.label` AS political_group,
        `Category`,
        `member.country.label` AS country,
        `position`,
        COUNT(*) AS cnt
    FROM eukraine1
    GROUP BY
        `pr_key`,
        `member.group.label`,
        `Category`,
        `member.country.label`,
        `position`
),
full_grid AS (
    SELECT
        b.`pr_key`,
        b.political_group,
        b.`Category`,
        b.country,
        p.position
    FROM base b
    CROSS JOIN positions p
)
SELECT
    g.`pr_key`,
    g.political_group,
    g.`Category`,
    g.country,
    g.position,
    COALESCE(c.cnt, 0) AS position_count,
    SUM(COALESCE(c.cnt, 0)) OVER (
        PARTITION BY g.`pr_key`, g.political_group, g.`Category`, g.country
    ) AS total_count
FROM full_grid g
LEFT JOIN counts c
  ON c.`pr_key` = g.`pr_key`
 AND c.political_group = g.political_group
 AND c.`Category` = g.`Category`
 AND c.country = g.country
 AND c.position = g.position
ORDER BY
    g.`pr_key`, g.political_group, g.`Category`, g.country, g.position;
    
SELECT * FROM ukraine_votes;
SELECT * FROM eukraine4;

-- Sanity Checks

WITH agg_from_new AS (
    SELECT
        political_group,
        position,
        ROUND(100.0 * SUM(position_count) / NULLIF(SUM(total_count), 0), 4) AS avg_pct_new
    FROM ukraine_votes
    GROUP BY political_group, position
)
SELECT
    a.political_group,
    a.position,
    a.avg_pct_new,
    e4.avg_position_pct_across_resolutions AS avg_pct_eukraine4,
    ROUND(a.avg_pct_new - e4.avg_position_pct_across_resolutions, 4) AS diff
FROM agg_from_new a
JOIN eukraine4 e4
  ON e4.political_group = a.political_group
 AND e4.position = a.position
ORDER BY ABS(diff) DESC;

WITH per_resolution AS (
    SELECT
        pr_key,
        political_group,
        position,
        SUM(position_count) AS pos_count,
        SUM(total_count) AS tot_count
    FROM ukraine_votes
    GROUP BY pr_key, political_group, position
),
per_resolution_pct AS (
    SELECT
        pr_key,
        political_group,
        position,
        100.0 * pos_count / NULLIF(tot_count, 0) AS position_pct
    FROM per_resolution
),
agg_from_new AS (
    SELECT
        political_group,
        position,
        ROUND(AVG(position_pct), 4) AS avg_pct_new
    FROM per_resolution_pct
    GROUP BY political_group, position
)
SELECT
    a.political_group,
    a.position,
    a.avg_pct_new,
    e4.avg_position_pct_across_resolutions AS avg_pct_eukraine4,
    ROUND(a.avg_pct_new - e4.avg_position_pct_across_resolutions, 4) AS diff
FROM agg_from_new a
JOIN eukraine4 e4
  ON e4.political_group = a.political_group
 AND e4.position = a.position
ORDER BY ABS(diff) DESC;

UPDATE ukraine_votes
SET political_group = CASE political_group
WHEN "European Peopleβ€™s Party"
THEN "European People's Party"
WHEN "Progressive Alliance of Socialists and Democrats"
THEN "Socialists and Democrats"
WHEN "The Left in the European Parliament"
THEN "The Left"
ELSE political_group 
END;
