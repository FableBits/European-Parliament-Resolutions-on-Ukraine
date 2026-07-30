-- The table eukraine1 has all the votes from the 65 resolutions related to the aid to
-- Ukraine, as collected from howtheyvote.eu> With the table ukraine_votes, we will create the
-- interactive chart in python, where the user will be able to see the share of votes by 
-- political group, and filter by country and category 


DROP TABLE IF EXISTS eukraine_date;

CREATE TABLE eukraine_date AS
SELECT * FROM eukraine1;

ALTER TABLE eukraine_date 
ADD COLUMN date_col DATE;

UPDATE eukraine_date 
SET date_col = STR_TO_DATE(
	SUBSTRING_INDEX(pr_key, ' · ', 1),
	'%b %d %Y'
);

UPDATE eukraine_date
SET date_col = STR_TO_DATE(
    regexp_substr(pr_key, '^[A-Za-z]{3} [0-9]{1,2}, [0-9]{4}'),
    '%b %d, %Y'
);

UPDATE eukraine_date
SET `member.group.label`  = CASE `member.group.label`
WHEN "European Peopleβ€™s Party"
THEN "European People's Party"
WHEN "Progressive Alliance of Socialists and Democrats"
THEN "Socialists and Democrats"
WHEN "The Left in the European Parliament"
THEN "The Left"
ELSE `member.group.label`
END;

SELECT
    date_col,
    `member.group.label`,
    ROUND(
        100 * SUM(CASE WHEN position = 'VotePosition.FOR' THEN 1 ELSE 0 END) / COUNT(*),
        2
    ) AS pct_for
FROM eukraine_date
GROUP BY date_col, `member.group.label`
ORDER BY `member.group.label`, date_col asc;

SELECT
    REGR_SLOPE(pct_for, date_num) AS slope,
    REGR_INTERCEPT(pct_for, date_num) AS intercept
FROM (
    SELECT
        DATEDIFF(date_col, MIN(date_col) OVER ()) AS date_num,
        ROUND(
            100 * SUM(CASE WHEN position = 'VotePosition.FOR' THEN 1 ELSE 0 END) / COUNT(*),
            2
        ) AS pct_for
    FROM eukraine_date
    WHERE `member.group.code` = 'SD'
    GROUP BY date_col
) AS t;

SELECT
    (SUM(date_num * pct_for) - SUM(date_num) * SUM(pct_for) / COUNT(*))
    /
    (SUM(date_num * date_num) - SUM(date_num) * SUM(date_num) / COUNT(*))
    AS slope
FROM (
    SELECT
        DATEDIFF(date_col, (SELECT MIN(date_col) FROM eukraine_date)) AS date_num,
        ROUND(
            100 * SUM(CASE WHEN position = 'VotePosition.FOR' THEN 1 ELSE 0 END) / COUNT(*),
            2
        ) AS pct_for
    FROM eukraine_date
    WHERE `member.group.label` = 'Non-attached Members'
    GROUP BY date_col
) AS t;


-- We will build a trend table that will include the resolutions with the same date seperately
-- and we will add the vote_id column so we can connect the howtheyvote urls frpom the table all_cotes
-- which is taken from the European Parliament's Github repository. The table all_votes has the vote_id 
-- and the pr_key, so we will join it with the eukraine_date table to get the vote_id for each resolution.

DROP TABLE IF exists good_votes

CREATE TABLE good_votes AS
SELECT * FROM all_votes
WHERE is_main = '"TRUE"';

DROP TABLE IF EXISTS eukraine_trend2;

CREATE TABLE eukraine_trend2 AS
SELECT
    e.date_col,
    e.pr_key,
    v.id AS vote_id,
    e.`member.group.label`,
    COUNT(*) AS total_votes,
    ROUND(
        100 * SUM(CASE WHEN e.position = 'VotePosition.FOR' THEN 1 ELSE 0 END) / COUNT(*),
        2
    ) AS pct_for
FROM eukraine_date e
LEFT JOIN good_votes v ON e.pr_key = v.pr_key
GROUP BY e.date_col, e.pr_key, v.id, e.`member.group.label`
ORDER BY e.`member.group.label`, e.date_col ASC;

SELECT * FROM eukraine_trend2
ORDER BY date_col ASC, pr_key asc;

DELETE FROM eukraine_trend2 
WHERE date_col = '2021-02-10';

SELECT count(DISTINCT date_col) FROM eukraine_trend2
UNION all
SELECT count(DISTINCT pr_key) FROM eukraine_trend2
UNION ALL
SELECT count(DISTINCT vote_id) FROM eukraine_trend2
UNION ALL
SELECT count(DISTINCT vote_url) FROM eukraine_trend2;

SELECT DISTINCT e.pr_key
FROM eukraine_date e
LEFT JOIN all_votes v ON e.pr_key = v.pr_key
WHERE v.pr_key IS NULL;

UPDATE eukraine_trend2
SET vote_id = 150459
WHERE pr_key = 'Nov 23, 2022 · RC-B9-0482/2022';

SELECT pr_key, count(DISTINCT vote_id)
FROM eukraine_trend2
GROUP BY pr_key
HAVING count(DISTINCT vote_id) != 1;

DELETE FROM eukraine_trend2 
WHERE date_col = '2025-11-25'
AND vote_id = '181879';

ALTER TABLE eukraine_trend2 
ADD COLUMN vote_url VARCHAR(255);

UPDATE eukraine_trend2
SET vote_url = CONCAT('https://howtheyvote.eu/votes/', vote_id);

SELECT * FROM eukraine_trend2;

DROP TABLE IF EXISTS eukraine_trend_bkp;

CREATE TABLE eukraine_trend_bkp AS
SELECT * FROM eukraine_trend2;

SELECT `member.group.label`, COUNT(DISTINCT `member.group.code`) AS n_codes
FROM eukraine_date
GROUP BY `member.group.label`
HAVING n_codes > 1;

ALTER TABLE eukraine_trend2 ADD COLUMN group_code VARCHAR(20);


-- We will create a column with short names for the political groups, 
-- so we can use them in the interactive chart.

UPDATE eukraine_trend2 t
JOIN (
    SELECT DISTINCT `member.group.label`, `member.group.code`
    FROM eukraine_date
) AS lookup ON t.`member.group.label` = lookup.`member.group.label`
SET t.group_code = lookup.`member.group.code`;

SELECT * FROM eukraine_trend2 WHERE group_code IS NULL;

SELECT DISTINCT group_code FROM eukraine_trend2;

UPDATE eukraine_trend2
SET group_code = CASE group_code
WHEN 'GREEN_EFA'
THEN 'GRE'
WHEN 'RENEW'
THEN 'REN'
WHEN 'GUE_NGL'
THEN 'LEF'
ELSE group_code 
END;