-- roles/fluentbit/files/enrich.lua
-- Plan 03-05 -- INGEST-07 gap closure (iteration 1).
--
-- Fluent Bit [FILTER] lua callback that enriches every record with
-- `service` and `job` Loki labels derived from the source container's
-- Docker labels `org.telemetron.service` and `org.telemetron.job`.
--
-- Source of truth: /var/lib/docker/containers/<container_id>/config.v2.json
-- (RO bind-mount; already in place from Plan 03-04). NO Docker socket.
--
-- Dependency posture: NO cjson / NO cjson.safe. The fluent/fluent-bit:4.2.3
-- image bundles LuaJIT but not the lua-cjson Alpine package. We use
-- Lua string.match patterns on the raw JSON content to extract three
-- fields (service label, job label, top-level Name). The Docker
-- config.v2.json serialization is stable enough for pattern extraction:
-- the label keys are globally unique within the file and the top-level
-- "Name" appears with an optional leading "/".
--
-- Tag -> container_id derivation: Plan 03-04's [INPUT] tail uses the
-- Tag_Regex `(?<container_id>[^/]+)\.log$` against the path
-- `*/*-json.log`. The greedy `[^/]+` captures `<hex>-json` (NOT the bare
-- <hex> directory id) because the basename is `<hex>-json.log`. We strip
-- a trailing `-json` suffix on the captured id BEFORE using it as the
-- path segment for `/var/lib/docker/containers/<id>/config.v2.json`.
-- The strip lives in this Lua file only -- we deliberately do NOT touch
-- the shipped Plan 03-04 Tag_Regex (changing a role template to fix a
-- Lua-side bug would re-trigger a handler restart for the wrong reason).
-- DO NOT remove the suffix-strip without first reverting the Tag_Regex.
--
-- Fallbacks:
--   service: unset -> "unlabeled"
--   job:     unset -> container_name (Name field, leading "/" stripped)
--
-- In-memory cache keyed by container_id with 300s TTL avoids per-log-line
-- disk reads. Cache miss -> read JSON as raw string, pattern-match, populate.
-- JSON read failure (container died) -> emit service="unlabeled" + job="unknown"
-- and log a single stderr warning per container_id.

-- Tunables -- mirror roles/fluentbit/defaults/main.yml.
local DOCKER_ROOT = "/var/lib/docker/containers"
local CACHE_TTL_SECONDS = 300
local UNLABELED_SERVICE = "unlabeled"
local UNLABELED_JOB = "unknown"

-- Per-process in-memory cache.
-- key = container_id (string, post-suffix-strip)
-- value = { service=string, job=string, container_name=string, expires_at=number }
local cache = {}

-- Per-process set tracking which container_ids have already emitted a
-- "JSON read failed" stderr warning (so we warn once, not per log line).
local warned = {}

-- Extract container_id from the FB tag set by tasks/main.yml's
-- Tag_Regex. Greedy capture against `<hex>-json.log` yields `<hex>-json`,
-- so we strip the trailing `-json` (6 chars: `-json`) to recover the bare
-- container directory id used as the path segment.
local function container_id_from_tag(tag)
    -- FB tag shape from Plan 03-04 [INPUT] tail: "docker.<container_id>"
    -- where <container_id> includes the trailing "-json" per the greedy regex.
    local id = string.match(tag or "", "^docker%.(.+)$")
    if id and id:sub(-5) == "-json" then
        id = id:sub(1, -6)
    end
    return id
end

-- Read and pattern-match /var/lib/docker/containers/<id>/config.v2.json.
-- Returns service, job, container_name, ok. NO cjson dependency.
local function read_container_config(container_id)
    local path = DOCKER_ROOT .. "/" .. container_id .. "/config.v2.json"
    local f, err = io.open(path, "r")
    if not f then
        if not warned[container_id] then
            io.stderr:write(string.format(
                "[enrich.lua] WARN: cannot open %s: %s -- using fallbacks\n",
                path, tostring(err)))
            warned[container_id] = true
        end
        return nil, nil, nil, false
    end
    local raw = f:read("*all")
    f:close()
    if not raw or raw == "" then
        if not warned[container_id] then
            io.stderr:write(string.format(
                "[enrich.lua] WARN: empty config.v2.json at %s -- using fallbacks\n",
                path))
            warned[container_id] = true
        end
        return nil, nil, nil, false
    end
    -- Pattern-match the three fields. Patterns are robust because:
    --   - "org.telemetron.service" and "org.telemetron.job" are unique
    --     label keys that do not appear elsewhere in config.v2.json.
    --   - The top-level "Name" appears as a JSON key starting with /.
    -- NO cjson dependency -- the FB 4.2.3 image does not ship lua-cjson.
    local svc  = raw:match('"org%.telemetron%.service"%s*:%s*"([^"]*)"')
    local job  = raw:match('"org%.telemetron%.job"%s*:%s*"([^"]*)"')
    local name = raw:match('"Name"%s*:%s*"/?([^"]*)"') or ""
    if not svc or svc == "" then
        svc = UNLABELED_SERVICE
    end
    if not job or job == "" then
        if name ~= "" then
            job = name
        else
            job = UNLABELED_JOB
        end
    end
    return svc, job, name, true
end

-- Public callback. Signature per Fluent Bit Lua filter docs:
--   function name(tag, timestamp, record)
--   returns code, timestamp, record  -- code 2 = record modified
function enrich(tag, timestamp, record)
    local container_id = container_id_from_tag(tag)
    if not container_id then
        record["service"] = UNLABELED_SERVICE
        record["job"] = UNLABELED_JOB
        return 2, timestamp, record
    end

    local now = os.time()
    local entry = cache[container_id]
    if entry and entry.expires_at > now then
        record["service"] = entry.service
        record["job"] = entry.job
        return 2, timestamp, record
    end

    local svc, job, name, ok = read_container_config(container_id)
    if not ok then
        -- Read failed -- still emit the record with fallback labels.
        record["service"] = UNLABELED_SERVICE
        record["job"] = UNLABELED_JOB
        return 2, timestamp, record
    end

    cache[container_id] = {
        service = svc,
        job = job,
        container_name = name,
        expires_at = now + CACHE_TTL_SECONDS,
    }
    record["service"] = svc
    record["job"] = job
    return 2, timestamp, record
end
