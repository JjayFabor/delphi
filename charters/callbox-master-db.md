# Callbox Master Database Reference

> Living document — append queries as they are discovered or requested.
> **Location:** `~/JjayFiles/claude-command-center/charters/callbox-master-db.md`
> **Last updated:** 2026-04-23

---

## Infrastructure

### Databases

| Name | Engine | Host | Port | Database | Notes |
|---|---|---|---|---|---|
| **DW2 (Data Warehouse)** | MySQL | 192.168.50.26 | 3306 | `callbox_dw2` | Lead/contact source of truth |
| **BigBox (Local PG)** | PostgreSQL | /var/run/postgresql (socket) | 5432 | `callbox_bigbox` | App persistence — reports, users, ICP |
| **Supabase PG** | PostgreSQL | aws-1-ap-southeast-1.pooler.supabase.com | 5432 | `postgres` | Cloud mirror |
| **Pipeline DB** | MySQL | 192.168.50.65 | 3306 | — | User auth, pipeline users |
| **Admin Divs DB** | MySQL | (same as DW2 pool) | — | — | `admin_divs` table — state/region names |

### Connection Strings (from ai-api .env)
```
LOCAL_PG_URL=postgresql://callbox:CallboxPG@2026@/callbox_bigbox?host=/var/run/postgresql
SUPABASE_PG_URL=postgresql://postgres.ynlpbhtztwzdktfyguwq:...@aws-1-ap-southeast-1.pooler.supabase.com:5432/postgres
```

### Quick psql Access (devbox)
```bash
# Local BigBox
PGPASSWORD='CallboxPG@2026' psql -U callbox -d callbox_bigbox -h /var/run/postgresql

# Run a one-liner
PGPASSWORD='CallboxPG@2026' psql -U callbox -d callbox_bigbox -h /var/run/postgresql -c "SELECT ..."
```

---

## PostgreSQL — callbox_bigbox

### Tables

| Table | Purpose |
|---|---|
| `datamine_reports` | Saved ICP/DW2/Apollo reports — slug, filters, counts, metadata |
| `icp_run_ids` | `(slug, target_detail_id)` — contacts belonging to an ICP run |
| `apollo_contacts` | Apollo search results per slug |
| `datahub_users` | DataHub Pro user accounts + tg_id + role |
| `datamine_export_log` | CSV export history per slug |
| `report_audit_log` | Access/view audit trail |
| `datamine_debug_log` | Debug info per slug |
| `datamine_filter_registry` | Saved filter presets |
| `icp_runs` | ICP run metadata (parallel to icp_run_ids) |
| `datamine_enrichment_sessions` | Enrichment session tracking |
| `datamine_contact_enrichments` | Per-contact enrichment results |
| `datamine_data_sources` | Enrichment data source registry |

### Useful Queries

#### Reports — count by source
```sql
SELECT source, COUNT(*) FROM datamine_reports GROUP BY source ORDER BY source;
```

#### Reports — temp vs saved
```sql
SELECT is_temp, COUNT(*) FROM datamine_reports GROUP BY is_temp;
```

#### Reports — expired
```sql
SELECT COUNT(*) FROM datamine_reports WHERE expires_at < NOW();
```

#### Reports — size breakdown
```sql
SELECT
  tablename,
  pg_size_pretty(pg_total_relation_size('public.'||tablename)) AS size
FROM pg_tables WHERE schemaname = 'public'
ORDER BY pg_total_relation_size('public.'||tablename) DESC;
```

#### Reports — find by slug
```sql
SELECT slug, agent, source, total_count, unique_company_count, deduped_contact_count,
       requested_by_name, is_temp, created_at, saved_at
FROM datamine_reports
WHERE slug = 'SLUG_HERE';
```

#### Reports — list recent saved (not temp)
```sql
SELECT slug, slug_title, source, total_count, requested_by_name, created_at
FROM datamine_reports
WHERE is_temp = FALSE
ORDER BY created_at DESC
LIMIT 20;
```

#### Reports — clean temp + expired
```sql
DELETE FROM datamine_reports WHERE is_temp = TRUE OR expires_at < NOW();
```

#### Reports — clean by date range
```sql
DELETE FROM datamine_reports WHERE created_at < '2026-04-18 00:00:00';
```

#### ICP Run IDs — count per slug
```sql
SELECT slug, COUNT(*) AS contact_count
FROM icp_run_ids
GROUP BY slug
ORDER BY contact_count DESC
LIMIT 20;
```

#### ICP Run IDs — total rows
```sql
SELECT COUNT(*) FROM icp_run_ids;
```

#### Apollo contacts — count per slug
```sql
SELECT slug, COUNT(*) FROM apollo_contacts GROUP BY slug ORDER BY COUNT(*) DESC LIMIT 20;
```

#### Users — list all
```sql
SELECT username, role, tg_id, pipeline_user_id, pipeline_username
FROM datahub_users ORDER BY username;
```

#### Users — find by username
```sql
SELECT * FROM datahub_users WHERE username = 'USERNAME_HERE';
```

#### Export log — recent exports
```sql
SELECT slug, user_name, row_count, export_type, exported_at
FROM datamine_export_log
ORDER BY exported_at DESC
LIMIT 20;
```

#### Full cascade delete of a report
```sql
BEGIN;
DELETE FROM icp_run_ids           WHERE slug = 'SLUG';
DELETE FROM apollo_contacts       WHERE slug = 'SLUG';
DELETE FROM datamine_export_log   WHERE slug = 'SLUG';
DELETE FROM report_audit_log      WHERE slug = 'SLUG';
DELETE FROM datamine_debug_log    WHERE slug = 'SLUG';
DELETE FROM datamine_reports      WHERE slug = 'SLUG';
COMMIT;
```

---

## MySQL — callbox_dw2 (Data Warehouse)

> Access via ai-api Python code (aiomysql) or direct MySQL client on devbox.

### Key Tables

| Table | Purpose |
|---|---|
| `target_details` | Main contact/lead table — names, titles, company, country, state |
| `companies` | Company records — name, industry, employee size |
| `admin_divs` | State/region names — `admin_div_id`, `admin_div` (abbreviated, leading spaces) |
| `countries` | Country reference — `country_id`, `country` |
| `industries` | Industry reference |

### Useful Queries

#### Count contacts by country
```sql
SELECT country, COUNT(*) AS cnt
FROM target_details
GROUP BY country
ORDER BY cnt DESC
LIMIT 20;
```

#### Count contacts by state (US)
```sql
SELECT ad.admin_div AS state, COUNT(*) AS cnt
FROM target_details td
JOIN admin_divs ad ON ad.admin_div_id = td.admin_div_id
WHERE td.country = 'United States'
GROUP BY ad.admin_div
ORDER BY cnt DESC;
```

#### Sample contacts for an ICP
```sql
SELECT td.first_name, td.last_name, td.position, c.company_name, td.country
FROM target_details td
JOIN companies c ON c.company_id = td.company_id
WHERE td.country IN ('United States', 'Canada')
  AND td.position LIKE '%VP%'
LIMIT 20;
```

#### admin_divs — check state abbreviations
```sql
SELECT admin_div_id, TRIM(admin_div) AS state FROM admin_divs LIMIT 50;
```

---

## Notes

- `admin_divs.admin_div` stores raw abbreviations with **leading whitespace** — always `TRIM()` in queries
- `datamine_reports.filters` is stored as JSONB — use `->` / `->>` operators or `json.loads()` in Python
- `icp_run_ids` is the source of truth for ICP report contacts — not `datamine_contacts` (dropped)
- `datamine_record_cache` and `datamine_chosen_ids` were dropped 2026-04-23 (replaced by ICP path)
- All new ICP runs go through `icp_run_ids`, not the old DW2 query engine

---

## Append queries below as needed

---

## Pipeline / Incentive Queries

### MTD Agent Total Points
**Purpose:** Month-to-date points breakdown per agent — appointments, leads, profiles, webinars, regular points, split (half) points, client/sub-client grouping, campaign settings.
**Database:** DW2 MySQL (`callbox_dw2`)
**Parameters to change:**
- `date_contacted BETWEEN '2025-04-01' AND '2025-04-30'` — swap for target month range
- `ca.client_id IN (22056, 22282, 22056)` — swap for target client IDs
- `lkp.user_id = 1255054` — swap for target agent user_id (remove line to get all agents)
- `cs.month = MONTH('$date_to') AND cs.year = YEAR('$date_to')` — date_to = last day of target month

```sql
SELECT * FROM (SELECT 
                txn.event_tm_ob_txn_id,
                half.event_tm_ob_txn_id as half_event_tm_ob_txn_id,
                ca.hierarchy_tree_id AS cluster_id, 
                ht3.parent_id as agent_cluster_id,
                ht3.hierarchy_tree_id as agent_team_id, 
                date_contacted, 
                ca.teamid as team_id,
                ca.qa_assigned,
                CONCAT_WS(' ', e2.first_name, e2.last_name) as qa_name,
                e2.hierarchy_tree_id AS qa_hierarchy_tree_id,
                
                IF(txn.event_state_lkp_id = 19, ptxn.points,0) AS appt_points, 
                IF(txn.event_state_lkp_id = 18, ptxn.points,0) AS lead_points,
                IF(txn.event_state_lkp_id = 589, ptxn.points,0) AS profile_points,  
                IF(txn.event_state_lkp_id = 645, ptxn.points,0) AS webinar_points,
                IF(emp.employee_state_lkp_id = 2, ptxn.points,0) AS regular_points,

                IF(cl.list LIKE 'CL_%' OR cl.list LIKE 'CP_%', 1, 0) AS has_client_list,
                
                -- Split points
                IF(txn.event_state_lkp_id = 19 AND half.points IS NOT NULL, half.points,0) AS half_appt_points, 
                IF(txn.event_state_lkp_id = 18 AND half.points IS NOT NULL, half.points,0) AS half_lead_points,
                IF(txn.event_state_lkp_id = 589 AND half.points IS NOT NULL, half.points,0) AS half_profile_points,  
                IF(txn.event_state_lkp_id = 645 AND half.points IS NOT NULL, half.points,0) AS half_webinar_points,
                IF(half.employee_state_lkp_id = 2 AND half.points IS NOT NULL, half.points,0) AS half_regular_points,
                IF(half.points IS NOT NULL, half.points,0) AS half_total_points,
                half.employee_state_lkp_id as half_employee_state_lkp_id,
                half.hierarchy_tree_id as half_team_id,
                half.team AS half_team,
                half.leader AS half_leader,
                half.hr_position as half_position,
                half.employee_state as half_employee_state,
                
                ptxn.points as total_points, 

                tl.upline_name as leader, 
                ht3.node as team, 
                lkp.user_id, 
                half.user_id as half_user_id,
                CONCAT(emp.first_name,' ', emp.last_name) as agent_name, 
                CONCAT(half.first_name,' ', half.last_name) as half_agent_name,
                GROUP_CONCAT(DISTINCT rd.role_lkp_id) as roles, 
                emp.employee_state_lkp_id,
                txn.event_state_lkp_id,
                hpl.hr_position as position, 
                esl.employee_state, 
                ca.client_account_id,

                -- Campaign settings
                IF(cs.amount > 0, cs.amount, 0) AS contract_price,
                IF(cs.duration > 0, cs.duration, 0) AS contract_duration,
                cs.seat,
                cs.start_date AS date_started,
                cs.end_date AS date_ended,               
                
                -- Client group / sub-client
                IF(cg.client_group_id IS NOT NULL AND cg.client_id != ca.client_id, cg.client_id, null) AS group_client_id,
                IF(cg.client_group_id IS NOT NULL AND cg.client_id != ca.client_id, ca.client_id, null) AS sub_client_id,
                IF(cg.client_group_id IS NOT NULL AND cg.client_id != ca.client_id, c.campaign_name, null) AS sub_campaign_name,
                IF(cg.client_group_id IS NOT NULL AND cg.client_id != ca.client_id, ca.teamid, null) AS sub_team_id,
                IF(cg.client_group_id IS NOT NULL AND cg.client_id != ca.client_id, ht3.node, null) AS sub_team,
                IF(cg.client_group_id IS NOT NULL AND cg.client_id != ca.client_id, tl.upline_name, null) AS sub_leader,
                IF(txn.event_state_lkp_id = 19 AND cg.client_group_id IS NOT NULL AND cg.client_id != ca.client_id, ptxn.points, 0) AS sub_appt_points, 
                IF(txn.event_state_lkp_id = 18 AND cg.client_group_id IS NOT NULL AND cg.client_id != ca.client_id, ptxn.points,0) AS sub_lead_points,
                IF(txn.event_state_lkp_id = 589 AND cg.client_group_id IS NOT NULL AND cg.client_id != ca.client_id, ptxn.points,0) AS sub_profile_points,  
                IF(txn.event_state_lkp_id = 645 AND cg.client_group_id IS NOT NULL AND cg.client_id != ca.client_id, ptxn.points,0) AS sub_webinar_points,
                IF(half.employee_state_lkp_id = 2 AND cg.client_group_id IS NOT NULL AND cg.client_id != ca.client_id, ptxn.points,0) AS sub_regular_points,
                IF(cg.client_group_id IS NOT NULL AND cg.client_id != ca.client_id, ptxn.points, 0) AS sub_total_points,
                
                CASE WHEN cg.client_group_id IS NOT NULL THEN cg.client_id ELSE ca.client_id
                END AS client_id,
                
                CASE WHEN cg.client_group_id IS NOT NULL 
                     THEN (SELECT GROUP_CONCAT(campaign_name) FROM clients WHERE FIND_IN_SET(client_id, cg.client_ids)) 
                     ELSE c.campaign_name
                END AS campaign_name
                           
                FROM events_tm_ob_lkp lkp
                INNER JOIN events_tm_ob_txn txn USING (event_tm_ob_lkp_id)
                INNER JOIN events_incentive_txn ptxn USING(event_tm_ob_txn_id)
                INNER JOIN client_lists cl ON lkp.client_list_id = cl.client_list_id
                INNER JOIN client_job_orders cjo ON (cl.client_job_order_id = cjo.client_job_order_id)
                INNER JOIN client_accounts ca USING(client_account_id)
                LEFT OUTER JOIN clients AS c ON ca.client_id = c.client_id
                INNER JOIN hierarchy_tree ht ON (ca.teamid = ht.hierarchy_tree_id)
                LEFT JOIN employees emp ON lkp.user_id = emp.user_id
                LEFT JOIN role_details rd ON emp.user_id = rd.user_id AND rd.x = 'active'
                LEFT JOIN hr_positions_lkp hpl ON hpl.hr_position_lkp_id = emp.hr_position_lkp_id
                LEFT JOIN employee_states_lkp esl ON emp.employee_state_lkp_id = esl.employee_state_lkp_id
                LEFT JOIN hierarchy_tree_details as hd ON emp.user_id = hd.user_id AND hd.x = 'active'
                LEFT OUTER JOIN hierarchy_tree ht3 ON (ht3.hierarchy_tree_id = hd.hierarchy_tree_id)
                LEFT OUTER JOIN team_leaders tl ON ht3.hierarchy_tree_id = tl.team_id
                LEFT OUTER JOIN (
                    SELECT e.first_name, e.last_name, e.user_id, ht.node, ht.hierarchy_tree_id
                    FROM employees e
                    INNER JOIN hierarchy_tree_details as hd ON e.user_id = hd.user_id AND hd.x = 'active'
                    INNER JOIN hierarchy_tree AS ht ON hd.hierarchy_tree_id = ht.hierarchy_tree_id
                ) AS e2 ON ca.qa_assigned = e2.user_id
                LEFT OUTER JOIN (
                    SELECT 
                        plkp.user_id, 
                        ptxn.points, 
                        emp.employee_state_lkp_id, 
                        event_tm_ob_txn_id, 
                        emp.first_name, 
                        emp.last_name, 
                        hpl.hr_position,
                        employee_state,
                        hd.hierarchy_tree_id, 
                        ht3.node as team, 
                        tl.upline_name as leader
                    FROM events_incentive_txn ptxn
                    INNER JOIN events_incentive_lkp plkp USING(event_incentive_lkp_id)
                    INNER JOIN employees emp ON plkp.user_id = emp.user_id
                    INNER JOIN hierarchy_tree_details as hd ON emp.user_id = hd.user_id AND hd.x = 'active'
                    INNER JOIN hr_positions_lkp AS hpl USING(hr_position_lkp_id)
                    INNER JOIN employee_states_lkp USING(employee_state_lkp_id)
                    LEFT OUTER JOIN hierarchy_tree ht3 ON (ht3.hierarchy_tree_id = hd.hierarchy_tree_id)
                    LEFT OUTER JOIN team_leaders tl ON ht3.hierarchy_tree_id = tl.team_id
                    WHERE plkp.x = 'active' 
                    AND ptxn.x = 'active'
                ) AS half ON half.event_tm_ob_txn_id = txn.event_tm_ob_txn_id AND half.user_id != lkp.user_id
                
                -- Client groups
                LEFT OUTER JOIN client_groups cg ON FIND_IN_SET(ca.client_id, cg.client_ids)

                -- Campaign settings
                LEFT OUTER JOIN campaign_settings cs 
                    ON cs.client_id = 
                        CASE 
                            WHEN cg.client_group_id IS NOT NULL THEN cg.client_id 
                            ELSE ca.client_id 
                        END
                    AND cs.month = MONTH('$date_to') 
                    AND cs.year = YEAR('$date_to')
                                           
                WHERE lkp.date_contacted BETWEEN '2025-04-01' AND '2025-04-30'  -- ← change date range
                AND ptxn.x = 'active'
                AND lkp.x = 'active'
                AND txn.x = 'active'
                AND txn.event_state_lkp_id IN (18, 19, 589, 645)
                AND ca.client_id IN (22056, 22282)              -- ← change client IDs
                AND lkp.user_id = 1255054                       -- ← change or remove for all agents
                GROUP BY txn.event_tm_ob_txn_id
) AS REP
ORDER BY date_contacted;
```

**event_state_lkp_id reference:**
| ID | Type |
|---|---|
| 18 | Lead |
| 19 | Appointment |
| 589 | Profile |
| 645 | Webinar |

---

## Client List Queries

### Get Contacts from a Client List
**Purpose:** Retrieve all active contacts in a specific client list with full details — name, email, company, address, city, state, phone number, DNC flag, campaign info.
**Database:** DW2 MySQL (`callbox_dw2`)
**Parameters to change:**
- `cld.client_list_id = 206094` — swap for target client list ID

```sql
SELECT
    td.target_detail_id,
    ca.account_number,
    c.campaign_name,
    CONCAT(cons.first_name, ' ', cons.last_name) AS contact_name,
    elkp.email,
    comp.company,
    loc.address,
    cit.city,
    adm.admin_div,
    t.target AS number,
    t.global_dnc,
    cl.list
FROM client_list_details AS cld
INNER JOIN target_details AS td       ON td.target_detail_id = cld.target_detail_id
INNER JOIN client_lists AS cl         ON cl.client_list_id = cld.client_list_id
INNER JOIN client_job_orders AS cjo   ON cjo.client_job_order_id = cl.client_job_order_id
INNER JOIN client_accounts AS ca      ON ca.client_account_id = cjo.client_account_id
INNER JOIN clients AS c               ON c.client_id = ca.client_id
INNER JOIN comp_details AS cd         ON cd.comp_detail_id = td.comp_detail_id
INNER JOIN companies AS comp          ON comp.company_id = cd.company_id
INNER JOIN contacts AS cons           ON cons.contact_id = td.contact_id
LEFT OUTER JOIN localities AS loc     ON loc.locality_id = cd.locality_id
LEFT OUTER JOIN cities AS cit         ON cit.city_id = loc.city_id
LEFT OUTER JOIN admin_divs AS adm     ON adm.admin_div_id = cit.admin_div_id
LEFT OUTER JOIN countries AS coun     ON coun.country_id = adm.country_id
LEFT OUTER JOIN targets AS t          ON t.target_id = td.target_id
LEFT OUTER JOIN emails_lkp AS elkp    ON elkp.email_lkp_id = td.email_lkp_id
WHERE cld.client_list_id = 206094     -- ← change client_list_id
  AND cld.x = 'active';
```

**Notes:**
- `cld.x = 'active'` filters out soft-deleted/inactive list entries
- `adm.admin_div` stores state abbreviations with leading whitespace — use `TRIM(adm.admin_div)` if needed
- `t.global_dnc` — 1 means on global Do Not Call list
- `cl.list` — list name/code (e.g. `CL_XXXXX` = client list, `CP_XXXXX` = campaign list)

---

### Agent Points — Per Transaction (Detailed)
**Purpose:** Per-txn points breakdown per agent with redundant data adjustment, campaign info, list, and contact date.
**Database:** DW2 MySQL (`callbox_dw2`)
**Parameters to change:**
- `etol.date_contacted BETWEEN '...' AND '...'` — target date range
- `etol.user_id IN (1255054)` — agent user_id(s), comma-separated; remove for all agents
- `etxn.event_state_lkp_id IN (645, 18, 19, 589)` — event types to include

```sql
SELECT
    etol.user_id,
    CONCAT(first_name, ' ', last_name) AS agent_name,
    IF(redundant_data != '', SUM(itxn.points) - 1, SUM(itxn.points)) AS adjusted_points,
    redundant_data,
    etol.date_contacted,
    etxn.time_contacted,
    c.campaign_name,
    c.client_id,
    ca.client_account_id,
    etxn.event_tm_ob_txn_id,
    etol.user_id,
    cl.list,
    etol.client_list_id,
    cl.client_job_order_id
FROM client_accounts AS ca
INNER JOIN client_job_orders AS cjo     ON cjo.client_account_id = ca.client_account_id
INNER JOIN client_lists AS cl           ON cl.client_job_order_id = cjo.client_job_order_id
INNER JOIN events_tm_ob_lkp AS etol     ON etol.client_list_id = cl.client_list_id
INNER JOIN events_tm_ob_txn AS etxn     ON etxn.event_tm_ob_lkp_id = etol.event_tm_ob_lkp_id
LEFT OUTER JOIN events_incentive_txn AS itxn  ON itxn.event_tm_ob_txn_id = etxn.event_tm_ob_txn_id
LEFT OUTER JOIN events_incentive_lkp AS ilkp  ON ilkp.event_incentive_lkp_id = itxn.event_incentive_lkp_id
INNER JOIN employees AS emp             ON emp.user_id = etol.user_id
INNER JOIN clients AS c                 ON c.client_id = ca.client_id
WHERE etol.date_contacted BETWEEN '2025-04-01' AND '2025-04-30'  -- ← date range
  AND etxn.event_state_lkp_id IN (645, 18, 19, 589)
  AND etol.user_id IN (1255054)                                   -- ← agent user_id(s)
  AND itxn.x = 'active'
  AND etxn.x = 'active'
  AND itxn.points IS NOT NULL
GROUP BY etxn.event_tm_ob_txn_id
ORDER BY ilkp.redundant_data DESC;
```

---

### Agent Points — Total Summary (Rolled Up)
**Purpose:** Same logic as above but rolled up to one row per agent — total adjusted points for the period.
**Database:** DW2 MySQL (`callbox_dw2`)
**Parameters to change:** Same as above.

```sql
SELECT
    user_id,
    agent_name,
    SUM(adjusted_points) AS total_points
FROM (
    SELECT
        etol.user_id,
        CONCAT(first_name, ' ', last_name) AS agent_name,
        IF(redundant_data != '', SUM(itxn.points) - 1, SUM(itxn.points)) AS adjusted_points
    FROM client_accounts AS ca
    INNER JOIN client_job_orders AS cjo     ON cjo.client_account_id = ca.client_account_id
    INNER JOIN client_lists AS cl           ON cl.client_job_order_id = cjo.client_job_order_id
    INNER JOIN events_tm_ob_lkp AS etol     ON etol.client_list_id = cl.client_list_id
    INNER JOIN events_tm_ob_txn AS etxn     ON etxn.event_tm_ob_lkp_id = etol.event_tm_ob_lkp_id
    LEFT OUTER JOIN events_incentive_txn AS itxn  ON itxn.event_tm_ob_txn_id = etxn.event_tm_ob_txn_id
    LEFT OUTER JOIN events_incentive_lkp AS ilkp  ON ilkp.event_incentive_lkp_id = itxn.event_incentive_lkp_id
    INNER JOIN employees AS emp             ON emp.user_id = etol.user_id
    INNER JOIN clients AS c                 ON c.client_id = ca.client_id
    WHERE etol.date_contacted BETWEEN '2025-04-01' AND '2025-04-30'  -- ← date range
      AND etxn.event_state_lkp_id IN (645, 18, 19, 589)
      AND etol.user_id IN (1255054)                                   -- ← agent user_id(s)
      AND itxn.x = 'active'
      AND etxn.x = 'active'
    GROUP BY etxn.event_tm_ob_txn_id
) AS txn_summary
GROUP BY user_id;
```

**Notes:**
- `redundant_data != ''` — when a transaction is flagged as redundant, subtract 1 point
- Both queries use the same WHERE/JOIN structure — use detailed version to investigate, summary version for reports
- To run for all agents: remove the `AND etol.user_id IN (...)` line

---

## Activity / Audit Queries

### Check Activity Log for a Subject
**Purpose:** Inspect recent activity log entries for a specific record (agent, contact, etc.) — useful for debugging or auditing changes.
**Database:** DW2 MySQL (`callbox_dw2`)
**Parameters to change:**
- `subject_id = 1252979` — the ID of the record you're inspecting (e.g. user_id, contact_id)

```sql
SELECT * FROM activity_log
WHERE subject_id = 1252979   -- ← change to target subject_id
ORDER BY id DESC
LIMIT 4;
```

**Notes:**
- Test txn ob ID reference: `219767424` (dossier/event_tm_ob_txn_id used for testing)
- Increase `LIMIT` as needed — default 4 shows most recent entries only
- `subject_id` maps to different entities depending on context (user, contact, transaction, etc.) — check `subject_type` column to confirm

---

## Contact / List Queries

### Get All Contacts Under a Client Account (with full details)
**Purpose:** Extract all contacts with their account number, campaign, company, address, phone, email, and latest event state. Useful for reporting or exporting contacts under specific client accounts.
**Database:** DW2 MySQL (`callbox_dw2`)
**Parameters to change:**
- `ca.client_id IN(22201, 19799)` — replace with target client_id(s)

```sql
SELECT td.target_detail_id, ca.account_number, c.campaign_name,
       CONCAT(cons.first_name,' ',cons.last_name) AS contact_name,
       elkp.email, comp.company, loc.address, cit.city, adm.admin_div,
       t.target AS number, t.global_dnc, cl.list, cjo.job_order,
       etol.date_contacted, etxn.event_state_lkp_id, esl.event_state
FROM client_accounts AS ca
INNER JOIN client_job_orders  AS cjo  ON cjo.client_account_id  = ca.client_account_id
INNER JOIN client_lists       AS cl   ON cl.client_job_order_id = cjo.client_job_order_id
INNER JOIN clients            AS c    ON c.client_id            = ca.client_id
LEFT OUTER JOIN events_tm_ob_lkp    AS etol ON etol.client_list_id         = cl.client_list_id
LEFT OUTER JOIN events_tm_ob_txn    AS etxn ON etxn.event_tm_ob_lkp_id     = etol.event_tm_ob_lkp_id
INNER JOIN client_list_details      AS cld  ON cld.client_list_detail_id   = etxn.client_list_detail_id
INNER JOIN target_details           AS td   ON td.target_detail_id         = cld.target_detail_id
LEFT OUTER JOIN event_states_lkp    AS esl  ON esl.event_state_lkp_id      = etxn.event_state_lkp_id
INNER JOIN comp_details             AS cd   ON cd.comp_detail_id           = td.comp_detail_id
INNER JOIN companies                AS comp ON comp.company_id              = cd.company_id
INNER JOIN contacts                 AS cons ON cons.contact_id              = td.contact_id
LEFT OUTER JOIN localities          AS loc  ON loc.locality_id             = cd.locality_id
LEFT OUTER JOIN cities              AS cit  ON cit.city_id                 = loc.city_id
LEFT OUTER JOIN admin_divs          AS adm  ON adm.admin_div_id            = cit.admin_div_id
LEFT OUTER JOIN countries           AS coun ON coun.country_id             = adm.country_id
LEFT OUTER JOIN targets             AS t    ON t.target_id                 = td.target_id
LEFT OUTER JOIN emails_lkp          AS elkp ON elkp.email_lkp_id           = td.email_lkp_id
WHERE ca.client_id IN(22201, 19799)   -- ← target client_id(s)
GROUP BY cld.target_detail_id
ORDER BY etol.date_contacted DESC;
```

**Notes:**
- `GROUP BY cld.target_detail_id` — deduplicates contacts that appear in multiple lists
- `event_state_lkp_id` reference: 18=Lead, 19=Appt, 589=Profile, 645=Webinar
- `t.global_dnc` — check this before using numbers for outbound
- To filter by list: add `AND cl.client_list_id = X`
- To filter by event state: add `AND etxn.event_state_lkp_id IN (18, 19)`

---

## Mailer / Blast Queries

### Get Blast Records Grouped by Mailer Template + Client Account
**Purpose:** Get active mailer blasts with GROUP_CONCAT of client account IDs, grouped by template and account. Useful for auditing which accounts are attached to which blast templates.
**Database:** DW2 MySQL (`callbox_dw2` + cross-DB join to `callbox_mailing_system`)
**Parameters to change:**
- `ca.client_account_id IN(20526, 21341, 21342)` — replace with target client_account_id(s)

```sql
SELECT
    ANY_VALUE(c.campaign_name) AS campaign_name,
    GROUP_CONCAT(DISTINCT ca.client_account_id ORDER BY ca.client_account_id) AS client_account_ids,
    ca.client_id,
    ma.client_ids AS ma_client_id,
    mt.client_ids AS mt_client_ids,
    ma.mailer_account_id,
    ma.name,
    me.mailer_template_id,
    me.mailing_list_blast_id AS me_mlbid,
    mlb.mailing_list_blast_id AS mlb_mlbid,
    COUNT(DISTINCT me.mailer_event_id) AS total_blast_records
FROM mailer_templates AS mt
INNER JOIN mailer_events AS me
    ON me.mailer_template_id = mt.mailer_template_id
INNER JOIN callbox_mailing_system.mailing_list_blasts AS mlb
    ON mlb.mailer_template_id = me.mailer_template_id
    AND mlb.mailing_list_blast_id = me.mailing_list_blast_id
INNER JOIN client_accounts AS ca
    ON FIND_IN_SET(ca.client_id, mt.client_ids)
INNER JOIN clients AS c
    ON c.client_id = ca.client_id
INNER JOIN mailer_accounts AS ma
    ON ma.mailer_account_id = mt.mailer_account_id
WHERE mlb.x = 'active'
  AND mt.x = 'active'
  AND ca.x = 'active'
  AND ca.client_account_id IN(20526, 21341, 21342)   -- ← target client_account_id(s)
GROUP BY me.mailer_template_id, ca.client_account_id;
```

---

### Get Blast Records with Team Name (hierarchy_tree join)
**Purpose:** Same as above but includes the Team name from `hierarchy_tree`, grouped by client. Use when you need to see which team each blast account belongs to.
**Database:** DW2 MySQL (`callbox_dw2` + `callbox_mailing_system`)
**Parameters to change:**
- `ca.client_account_id IN(20526, 21341, 21342)` — replace with target client_account_id(s)

```sql
SELECT
    ht.node AS Team,
    ANY_VALUE(c.campaign_name) AS campaign_name,
    ca.client_id,
    ma.client_ids AS ma_client_id,
    mt.client_ids AS mt_client_ids,
    ma.mailer_account_id,
    ma.name,
    me.mailer_template_id,
    me.mailing_list_blast_id AS me_mlbid,
    mlb.mailing_list_blast_id AS mlb_mlbid,
    COUNT(DISTINCT me.mailer_event_id) AS total_blast_records
FROM mailer_templates AS mt
INNER JOIN mailer_events AS me
    ON me.mailer_template_id = mt.mailer_template_id
INNER JOIN callbox_mailing_system.mailing_list_blasts AS mlb
    ON mlb.mailer_template_id = me.mailer_template_id
    AND mlb.mailing_list_blast_id = me.mailing_list_blast_id
INNER JOIN client_accounts AS ca
    ON FIND_IN_SET(ca.client_id, mt.client_ids)
INNER JOIN clients AS c
    ON c.client_id = ca.client_id
INNER JOIN mailer_accounts AS ma
    ON ma.mailer_account_id = mt.mailer_account_id
INNER JOIN hierarchy_tree AS ht
    ON ht.hierarchy_tree_id = ca.teamid
WHERE mlb.x = 'active'
  AND mt.x = 'active'
  AND ca.x = 'active'
  AND ca.client_account_id IN(20526, 21341, 21342)   -- ← target client_account_id(s)
GROUP BY ca.client_id;
```

**Notes (both blast queries):**
- `mt.client_ids` is a comma-separated string — `FIND_IN_SET` is used to join it to `client_accounts`
- `callbox_mailing_system.mailing_list_blasts` — cross-database join; ensure the DB user has SELECT on `callbox_mailing_system`
- `total_blast_records` = count of distinct mailer events (individual blast sends) per group
- `ht.node` = team name from `hierarchy_tree`; `ca.teamid` maps to `hierarchy_tree_id`
- First query: finer grouping (per template + account) — use for template-level audit
- Second query: coarser grouping (per client) + team label — use for team/campaign-level overview

---

## Points / Share Day Queries

### Share Day — Probationary & Regular Agents with Production Points
**Purpose:** Get agent production points for a specific date (share day), filtered by team. Includes QA rating, employee state (probationary/regular), and event state. Used for share day computations and agent point breakdowns.
**Database:** DW2 MySQL (`callbox_dw2`)
**Parameters to change:**
- `etol.date_contacted BETWEEN '2026-01-06' AND '2026-01-06'` — set target date (can be a range)
- `ca.teamid IN(152)` — replace with target team ID(s)
- `htd.hierarchy_tree_id = 152` — same team ID as above

```sql
SELECT
    CONCAT(first_name,' ',last_name) AS agent_name,
    SUM(points) AS points,
    c.campaign_name,
    c.client_id,
    ca.client_account_id,
    etxn.event_tm_ob_txn_id,
    etol.user_id,
    cl.list,
    etol.client_list_id,
    cl.client_job_order_id,
    ca.hierarchy_tree_id,
    etxn.event_state_lkp_id,
    etol.date_contacted,
    etxn.time_contacted,
    etxn.x,
    qaob.rating,
    htd.hierarchy_tree_id,
    emp.employee_state_lkp_id
FROM client_accounts AS ca
INNER JOIN client_job_orders AS cjo    ON cjo.client_account_id    = ca.client_account_id
INNER JOIN client_lists AS cl          ON cl.client_job_order_id   = cjo.client_job_order_id
INNER JOIN events_tm_ob_lkp AS etol    ON etol.client_list_id      = cl.client_list_id
INNER JOIN events_tm_ob_txn AS etxn    ON etxn.event_tm_ob_lkp_id  = etol.event_tm_ob_lkp_id
INNER JOIN qa_ob_events_txn AS qaob    ON qaob.event_tm_ob_txn_id  = etxn.event_tm_ob_txn_id
LEFT OUTER JOIN events_incentive_txn AS itxn ON itxn.event_tm_ob_txn_id   = etxn.event_tm_ob_txn_id
LEFT OUTER JOIN events_incentive_lkp AS ilkp ON ilkp.event_incentive_lkp_id = itxn.event_incentive_lkp_id
INNER JOIN clients AS c                ON c.client_id              = ca.client_id
INNER JOIN employees AS emp            ON emp.user_id              = etol.user_id
INNER JOIN hierarchy_tree_details AS htd ON htd.user_id            = etol.user_id
WHERE etol.date_contacted BETWEEN '2026-01-06' AND '2026-01-06'   -- ← share day / date range
  AND etxn.event_state_lkp_id IN (18, 19, 589, 645)
  AND ca.teamid IN(152)                                            -- ← team ID(s)
  AND ilkp.x = 'active'
  AND etxn.x = 'active'
  AND htd.hierarchy_tree_id = 152                                  -- ← same team ID
GROUP BY ilkp.user_id
ORDER BY points ASC;
```

**Notes:**
- `emp.employee_state_lkp_id` — use this to distinguish probationary vs. regular employees
- `qaob.rating` — QA rating attached to each transaction
- `GROUP BY ilkp.user_id` — rolls up all transactions per agent (via incentive lkp)
- `event_state_lkp_id` reference: 18=Lead, 19=Appt, 589=Profile, 645=Webinar
- `htd.hierarchy_tree_id = 152` — filters agents who belong to the team directly; must match `ca.teamid`
- `ilkp.x = 'active'` — only count active incentive rules (excludes expired point schemes)


---

## Appointment / QA Queries

### Get Appointment Feedback (with QA, Agent, Contact, Client details)
**Purpose:** Pull appointment feedback records with full context — client, contact, agent, QA reviewer, rating, interest level, comments, expiry, and status. Used for appointment quality reporting and client feedback review.
**Database:** DW2 MySQL (`callbox_dw2` + cross-DB join to `callbox_misc`)
**Parameters to change:**
- `a.date_inserted BETWEEN '2025-08-01 00:00:00' AND '2025-09-15 23:00:00'` — date range
- `clients.client_id = 22447` — target client ID
- Uncomment `ca.hierarchy_tree_id IN (11)` to filter by team instead

```sql
SELECT
    clients.client_id,
    ca.teamid AS team_id,
    com.company,
    com2.company AS contact_company,
    con.first_name,
    con.last_name,
    e.user_id,
    e.first_name AS a_first_name,
    e.last_name AS a_last_name,
    e2.user_id AS qa_user_id,
    e2.first_name AS qa_first_name,
    e2.last_name AS qa_last_name,
    qa.event_date,
    qa.event_time,
    a.event_tm_ob_txn_id,
    a.expiry_date,
    a.status,
    a.rating,
    a.interest_level,
    a.comments,
    ht.node AS team,
    af.appt_feedback_log_id
FROM clients
JOIN client_accounts AS ca        ON ca.client_id              = clients.client_id
JOIN client_job_orders AS cjo     ON cjo.client_account_id     = ca.client_account_id
JOIN client_lists AS cl           ON cl.client_job_order_id    = cjo.client_job_order_id
JOIN events_tm_ob_lkp AS lkp      ON lkp.client_list_id        = cl.client_list_id
JOIN events_tm_ob_txn AS txn      ON txn.event_tm_ob_lkp_id    = lkp.event_tm_ob_lkp_id
JOIN client_list_details AS cld   ON cld.client_list_detail_id = txn.client_list_detail_id
JOIN target_details AS td         ON td.target_detail_id       = cld.target_detail_id
JOIN contacts AS con              ON con.contact_id             = td.contact_id
JOIN callbox_misc.appt_feedback AS a ON a.event_tm_ob_txn_id   = txn.event_tm_ob_txn_id
JOIN target_details AS td2        ON td2.target_detail_id      = clients.target_detail_id
JOIN comp_details AS comp         ON comp.comp_detail_id       = td2.comp_detail_id
JOIN companies AS com             ON com.company_id             = comp.company_id
JOIN comp_details AS comp2        ON comp2.comp_detail_id      = td.comp_detail_id
JOIN companies AS com2            ON com2.company_id            = comp2.company_id
JOIN employees AS e               ON e.user_id                 = lkp.user_id
LEFT JOIN hierarchy_tree AS ht    ON ht.hierarchy_tree_id      = ca.teamid
JOIN qa_ob_events_txn AS qa       ON qa.event_tm_ob_txn_id     = txn.event_tm_ob_txn_id
JOIN qa_forms_txn AS qaf          ON qaf.qa_forms_txn_id       = qa.qa_forms_id
JOIN employees AS e2              ON e2.user_id                 = qaf.qa_id
LEFT JOIN callbox_misc.appt_feedback_logs AS af ON qa.event_tm_ob_txn_id = af.event_tm_ob_txn_id
JOIN events_client_lkp AS elkp    ON elkp.event_tm_ob_txn_id   = txn.event_tm_ob_txn_id
JOIN events_client_txn AS etxn    ON etxn.event_client_lkp_id  = elkp.event_client_lkp_id
                                  AND etxn.axn_required = 'yes'
WHERE
  -- ca.hierarchy_tree_id IN (11) AND   -- ← uncomment to filter by team
  a.date_inserted BETWEEN '2025-08-01 00:00:00' AND '2025-09-15 23:00:00'
  AND a.date_answered IS NOT NULL
  AND txn.event_state_lkp_id = 19       -- 19 = Appointment
  AND txn.x = 'active'
  AND clients.client_id = 22447         -- ← target client_id
GROUP BY qa.event_tm_ob_txn_id;
```

**Notes:**
- `callbox_misc.appt_feedback` — cross-DB join; ensure DB user has SELECT on `callbox_misc`
- `a.date_answered IS NOT NULL` — only include feedback that has been submitted/answered
- `etxn.axn_required = 'yes'` — filters to the primary client action on the transaction
- `com` = client's company name (via `clients.target_detail_id`); `com2` = contact's company
- `af.appt_feedback_log_id` — NULL if no follow-up log exists (LEFT JOIN)
- `ht.node` = team name; NULL if account has no team assigned
- To look up a specific contact: add `AND con.name_trim = 'First Last'` (name_trim is the normalized/trimmed version of the contact name — use this over first_name/last_name for exact lookups)
- `txn.event_state_lkp_id = 19` can be commented out to include all event states (not just appointments)

### Appointment Feedback — No Answer (Feedback Not Yet Submitted)
**Purpose:** Find appointments where feedback has NOT been submitted yet (`a.event_tm_ob_txn_id IS NULL`). Returns full contact and client details, agent, team, and event date/time. Used to follow up on unanswered appointment feedback.
**Database:** DW2 MySQL (`callbox_dw2` + `callbox_misc`)
**Parameters to change:**
- `q.event_date BETWEEN '2025-08-01 00:00:00' AND '2025-09-15 23:00:00'` — date range
- `c.client_id = 22447` — target client ID
- `c.client_id NOT IN (21227, 21612, 21257)` — exclusion list (adjust as needed)
- Uncomment `ca.hierarchy_tree_id IN (11)` to filter by team

```sql
SELECT
    con.*,
    com.*,
    com2.company AS contact_company,
    c.client_id,
    etxn.event_state_lkp_id,
    txn.event_tm_ob_txn_id,
    etxn.event_date,
    etxn.event_time,
    ca.teamid AS team_id,
    ht.node AS team,
    e.first_name AS a_first_name,
    e.last_name AS a_last_name,
    af.appt_feedback_log_id
FROM qa_ob_events_txn AS q
JOIN events_tm_ob_txn AS txn      ON txn.event_tm_ob_txn_id    = q.event_tm_ob_txn_id
JOIN events_tm_ob_lkp AS lkp      ON lkp.event_tm_ob_lkp_id    = txn.event_tm_ob_lkp_id
JOIN client_lists AS cl            ON cl.client_list_id          = lkp.client_list_id
JOIN client_job_orders AS cjo      ON cjo.client_job_order_id   = cl.client_job_order_id
JOIN client_accounts AS ca         ON ca.client_account_id      = cjo.client_account_id
JOIN events_client_lkp AS elkp     ON elkp.event_tm_ob_txn_id   = txn.event_tm_ob_txn_id
JOIN client_list_details AS cld    ON cld.client_list_detail_id = txn.client_list_detail_id
JOIN target_details AS td          ON td.target_detail_id       = cld.target_detail_id
JOIN contacts AS con               ON con.contact_id             = td.contact_id
JOIN clients AS c                  ON c.client_id               = ca.client_id
JOIN target_details AS td2         ON td2.target_detail_id      = c.target_detail_id
JOIN comp_details AS comp          ON comp.comp_detail_id       = td2.comp_detail_id
JOIN companies AS com              ON com.company_id             = comp.company_id
JOIN comp_details AS comp2         ON comp2.comp_detail_id      = td.comp_detail_id
JOIN companies AS com2             ON com2.company_id            = comp2.company_id
LEFT JOIN hierarchy_tree AS ht     ON ht.hierarchy_tree_id      = ca.teamid
JOIN employees AS e                ON e.user_id                 = lkp.user_id
JOIN events_client_txn AS etxn     ON etxn.event_client_lkp_id  = elkp.event_client_lkp_id
                                   AND etxn.axn_required = 'yes'
LEFT JOIN callbox_misc.appt_feedback AS a       ON a.event_tm_ob_txn_id  = txn.event_tm_ob_txn_id
LEFT JOIN callbox_misc.appt_feedback_logs AS af ON txn.event_tm_ob_txn_id = af.event_tm_ob_txn_id
WHERE txn.event_state_lkp_id = 19
  -- AND ca.hierarchy_tree_id IN (11)                           -- ← uncomment to filter by team
  AND q.event_date BETWEEN '2025-08-01 00:00:00' AND '2025-09-15 23:00:00'  -- ← date range
  AND a.event_tm_ob_txn_id IS NULL                             -- ← no feedback submitted
  AND c.client_id NOT IN (21227, 21612, 21257)                 -- ← exclusion list
  AND c.client_id = 22447                                      -- ← target client_id
GROUP BY txn.event_tm_ob_txn_id
ORDER BY CONCAT(etxn.event_date, ' ', etxn.event_time) DESC;
```

**Notes:**
- Key difference from the answered feedback query: `appt_feedback` is a **LEFT JOIN** here, and `AND a.event_tm_ob_txn_id IS NULL` filters to rows with no feedback record at all
- `af.appt_feedback_log_id` — feedback log status; NULL = no log entry yet
- Starts from `qa_ob_events_txn` (not `clients`) — gives QA-event-first perspective
- `con.*` and `com.*` — selects all columns from contacts and client companies; narrow down if needed
- `etxn.axn_required = 'yes'` — isolates the primary client-side action for the appointment

### Get Contact Name and Client ID
**Purpose:** Simple lookup — contact name mapped to their client account and client ID.
**Database:** DW2 MySQL (`callbox_dw2`)
**Parameters to change:**
- `clients.client_id = 22447` — replace with target client_id

```sql
SELECT
    clients.client_id,
    ca.client_account_id,
    ca.account_number,
    CONCAT(con.first_name, ' ', con.last_name) AS contact_name,
    con.contact_id
FROM clients
JOIN client_accounts AS ca        ON ca.client_id              = clients.client_id
JOIN client_job_orders AS cjo     ON cjo.client_account_id     = ca.client_account_id
JOIN client_lists AS cl           ON cl.client_job_order_id    = cjo.client_job_order_id
JOIN events_tm_ob_lkp AS lkp      ON lkp.client_list_id        = cl.client_list_id
JOIN events_tm_ob_txn AS txn      ON txn.event_tm_ob_lkp_id    = lkp.event_tm_ob_lkp_id
JOIN client_list_details AS cld   ON cld.client_list_detail_id = txn.client_list_detail_id
JOIN target_details AS td         ON td.target_detail_id       = cld.target_detail_id
JOIN contacts AS con              ON con.contact_id             = td.contact_id
WHERE clients.client_id = 22447   -- ← target client_id
  AND txn.x = 'active'
GROUP BY td.target_detail_id
ORDER BY con.last_name, con.first_name;
```

**Notes:**
- `GROUP BY td.target_detail_id` — deduplicates contacts that appear in multiple lists/events
- Add `AND ca.client_account_id = X` to narrow to a specific account
- Add `AND txn.event_state_lkp_id = 19` to limit to appointment contacts only

---

## HubSpot Queries / Operations

### Delete a HubSpot Target — Full Cascade Flow
**Purpose:** Safely remove a HubSpot target from all related tables before deleting it from HubSpot CRM. Must follow this order to avoid orphaned records.
**Databases involved:** `callbox_hubspot_reports`, `callbox_pipeline2`, HubSpot CRM (manual/API step)

#### Step-by-step order:

**1. Check `callbox_hubspot_reports` — find all related records**
```sql
-- Check records_map
SELECT * FROM callbox_hubspot_reports.records_map WHERE target_id = <target_id>;

-- Check hs_tm_ob_logs
SELECT * FROM callbox_hubspot_reports.hs_tm_ob_logs WHERE target_id = <target_id>;

-- Check hs_tm_ob_engagements
SELECT * FROM callbox_hubspot_reports.hs_tm_ob_engagements WHERE target_id = <target_id>;

-- Check funnel_progression_report_tmp
SELECT * FROM callbox_hubspot_reports.funnel_progression_report_tmp WHERE target_id = <target_id>;
```

**2. Delete from `callbox_hubspot_reports` tables**
```sql
DELETE FROM callbox_hubspot_reports.records_map WHERE target_id = <target_id>;
DELETE FROM callbox_hubspot_reports.hs_tm_ob_logs WHERE target_id = <target_id>;
DELETE FROM callbox_hubspot_reports.hs_tm_ob_engagements WHERE target_id = <target_id>;
DELETE FROM callbox_hubspot_reports.funnel_progression_report_tmp WHERE target_id = <target_id>;
```

**3. Soft-delete in `callbox_pipeline2` — set x = 'deleted'**
```sql
-- Soft-delete events_tm_ob_txn
UPDATE callbox_pipeline2.events_tm_ob_txn
SET x = 'deleted'
WHERE event_tm_ob_lkp_id IN (
    SELECT event_tm_ob_lkp_id FROM callbox_pipeline2.events_tm_ob_lkp
    WHERE target_id = <target_id>
);

-- Soft-delete events_tm_ob_lkp
UPDATE callbox_pipeline2.events_tm_ob_lkp
SET x = 'deleted'
WHERE target_id = <target_id>;

-- Soft-delete client_list_details
UPDATE callbox_pipeline2.client_list_details
SET x = 'deleted'
WHERE target_detail_id = <target_detail_id>;
```

**4. Delete from HubSpot CRM**
- Go to HubSpot CRM and delete the contact/target record manually, or via HubSpot API
- Only do this AFTER all DB steps above are complete

#### Notes:
- Always run SELECT checks (step 1) before any DELETE/UPDATE to confirm the target_id is correct
- `callbox_pipeline2` uses soft-delete (`x = 'deleted'`) — do NOT hard delete these rows
- `callbox_hubspot_reports` tables are hard-deleted
- `target_detail_id` may differ from `target_id` — confirm the correct ID from `records_map` first
- HubSpot CRM deletion is the LAST step — never delete from CRM before cleaning the DB
