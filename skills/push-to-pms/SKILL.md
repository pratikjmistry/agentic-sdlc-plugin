---
name: push-to-pms
description: "Use this skill when the user types /push-to-pms or wants to create issues, work items, or tasks in their project management platform after /feature-to-issues has run. Reads the issue manifest from /ai-context/issues.json and creates all Epics, child issues, parent-child relationships, and dependency links in the chosen platform. Supports GitHub Issues, GitLab Issues + Epics, Azure DevOps Work Items, Jira, and Linear. Asks the user which platform to use and collects the required credentials interactively — no pre-configured connectors or environment variables needed. Trigger on: /push-to-pms, create issues in GitHub, push issues to Jira, create work items in Azure DevOps, push to GitLab, create issues in Linear, create PMS items, publish issue manifest, push issues to project management, create tickets from issue plan."
---

# /push-to-pms — Platform Issue Creator

## Workflow Role

`/push-to-pms` is the **final delivery step** of the Greenfield and Brownfield workflows. It reads the platform-agnostic issue manifest produced by `/feature-to-issues` and creates all items in the chosen project management platform — handling data model mapping, hierarchy wiring, and dependency linking specific to each platform.

**Input:** `/ai-context/issues.json` (produced by `/feature-to-issues`)

**Output:** All Epics and child issues created in the target platform. A mapping file saved to `/ai-context/pms-map.json` recording internal IDs → platform IDs for future reference.

```
GREENFIELD:
  ... → /feature-to-issues → HITL Issue Review → [/push-to-pms] → Ready to Develop
```

**Prerequisite:** HITL Issue Review in `/feature-to-issues` must be confirmed (APPROVED) before running.

---

## Supported Platforms

| Platform | Item Types Created | Hierarchy Method |
|----------|--------------------|-----------------|
| **GitHub** | Issues + sub-issues | Native sub-issue API |
| **GitLab** | Epics + Issues | Epic → Issue link |
| **Azure DevOps** | Epic → User Story → Task | Work Item parent-child link |
| **Jira** | Epic → Story/Task → Sub-task | Epic link + parent link |
| **Linear** | Projects/Cycles → Issues | Parent issue link |

---

## Execution Instructions

### Step 1 — Load Issue Manifest

Read `/ai-context/issues.json`. If the file is missing, halt and instruct the user to run `/feature-to-issues` first.

Validate the manifest:
- At least one item with `"type": "epic"`
- At least one item with a valid `parent_epic_id`
- All `dependencies[].id` references resolve to items in the array
- `execution_order` values are present on all items
- **Title prefix convention** — every `title` starts with its required bracketed prefix: `[EPIC]` for
  `"type": "epic"` items, or `[<own id>]` (e.g. `[AUTH-DB-001]`) for child items. This is the same string
  `/feature-to-issues` is required to have already written — see its Title Convention section. If any
  item's `title` is missing or has the wrong prefix (e.g. hand-edited manifest, or an older manifest
  generated before this convention existed), **fix it in memory before creating anything** — prepend the
  correct prefix rather than halting, since this is mechanically derivable from `id`/`type` and shouldn't
  block delivery. Report which titles were auto-fixed in the Step 7 summary.

If any other validation fails, report the specific errors and do not proceed.

**Do not strip or reformat this prefix per platform**, even where the platform already shows the issue
type natively (Jira/ADO Epic icons, GitLab Epic objects) — the bracketed prefix is what keeps issues
searchable and traceable back to `issues.json`/`pms-map.json` from plain-text contexts (PR titles, commit
messages, cross-platform search) where the platform's UI chrome isn't available. Send `title` through to
each platform's title/name field exactly as validated above.

### Step 2 — Platform Selection

Present an elicitation form using `mcp__visualize__show_widget` (first call `mcp__visualize__read_me` with modules `["elicitation"]` if not already loaded). Show all five platforms as selectable cards, each briefly describing what gets created.

Card layout to render:

| Platform | Creates |
|----------|---------|
| GitHub | Issues + sub-issues |
| GitLab | Epics + Issues |
| Azure DevOps | Epic → User Story → Task |
| Jira | Epic → Story/Task |
| Linear | Projects/Issues |

After the user selects a platform and submits, proceed immediately to Step 3. This selection IS the platform confirmation — do not ask again. Keep this form to a single question — do not combine with credential collection.

### Step 3 — Credentials & Project Configuration

Present a second elicitation form tailored to the platform selected in Step 2. Collect both the API credentials AND project-specific config in one form.

**GitHub:**
- Personal Access Token — needs `repo` scope (github.com/settings/tokens)
- Repository in `owner/repo` format (e.g. `myorg/myrepo`)
- Milestone name (optional)

**GitLab:**
- Personal Access Token — needs `api` scope
- GitLab instance URL (default: `https://gitlab.com`)
- Namespace + project path (e.g. `mygroup/myproject`)
- Milestone name (optional)

**Azure DevOps:**
- Personal Access Token — needs Work Items: Read, Write, Manage
- Organization URL (e.g. `https://dev.azure.com/myorg`)
- Project name
- Area Path (optional — blank = project root)
- Iteration Path / Sprint (optional — blank = backlog)

**Jira:**
- Site URL — subdomain only, e.g. `yourorg.atlassian.net`
- Email address (your Atlassian login)
- API Token (id.atlassian.com/manage-profile/security/api-tokens)
- Project key (e.g. `AUTH`)
- Sprint name (optional)

**Linear:**
- API Key (Linear Settings → API → Personal API keys)
- Team ID or key (visible in team settings URL)
- Should Epics map to **Projects** or **parent Issues**?
- Cycle name (optional)

After the user submits, store all values as named variables and proceed to Step 4.

### Step 4 — Map Data Model

Silently map each manifest field to the target platform's equivalent using the Platform Data Model Mappings section below. This determines the API call payloads used in Step 5.

### Step 5 — Create Items via Direct API Calls

Use `mcp__workspace__bash` to run Python scripts that call the platform API directly with the credentials from Step 3. The Platform API Call Patterns section below contains ready-to-use code for each platform. Before running any script, ensure `requests` is available:

```bash
pip install requests --quiet --break-system-packages
```

Create items in four phases, always in this order:

**Phase A — Create all Epics first**

Create every manifest item where `"type": "epic"` before any child items. Record the platform-assigned ID for each Epic immediately — needed for Phase C wiring. Do not proceed to Phase B until all Epics are confirmed created.

**Phase B — Create child issues in execution_order sequence**

Create child items (`"type": "task"`) in ascending `execution_order` order. Items sharing the same value can be created in sequence within that group. Record each platform ID immediately after creation.

**Phase C — Wire parent-child relationships**

After all child items exist, link each child to its Epic using the platform's native parent mechanism. Use Epic IDs from Phase A and child IDs from Phase B. For ADO, this can be done at creation time by passing the parent URL in the work item payload.

**Phase D — Set dependency links**

For each item with `dependencies[].type = "blocking"`, create a blocking/predecessor link. Items with `"parallel"` need no link. Items with `"integration"` get a note added to the issue body.

**Failure handling:** Log each failure and continue. After all phases, report any failures with manual steps to resolve.

---

## Platform API Call Patterns

Use these Python patterns in your bash scripts. Substitute variables collected in Step 3.

### GitHub

```python
import requests

TOKEN = "{github_pat}"
OWNER, REPO = "{owner_repo}".split("/", 1)
BASE = "https://api.github.com"
H = {"Authorization": f"Bearer {TOKEN}",
     "Accept": "application/vnd.github+json",
     "X-GitHub-Api-Version": "2022-11-28"}

def create_issue(title, body, labels):
    r = requests.post(f"{BASE}/repos/{OWNER}/{REPO}/issues",
        headers=H, json={"title": title, "body": body, "labels": labels})
    r.raise_for_status()
    d = r.json()
    return d["number"], d["html_url"]

def add_sub_issue(epic_num, child_num, child_body=""):
    r = requests.post(f"{BASE}/repos/{OWNER}/{REPO}/issues/{epic_num}/sub_issues",
        headers=H, json={"sub_issue_number": child_num})
    if r.status_code == 404:
        # Sub-issue API not enabled — fall back to body reference
        requests.patch(f"{BASE}/repos/{OWNER}/{REPO}/issues/{child_num}",
            headers=H, json={"body": f"Parent Epic: #{epic_num}\n\n{child_body}"})
    else:
        r.raise_for_status()
```

Labels: add `"epic"` label to epics. Map `category[]` values directly as additional labels.

---

### GitLab

```python
import requests

TOKEN = "{gitlab_pat}"
BASE = "{gitlab_url}/api/v4"
GROUP = "{group_path}"
PROJECT = "{group_path}%2F{project}"  # URL-encoded
H = {"PRIVATE-TOKEN": TOKEN, "Content-Type": "application/json"}

def create_epic(title, description):
    r = requests.post(f"{BASE}/groups/{GROUP}/epics",
        headers=H, json={"title": title, "description": description})
    r.raise_for_status()
    return r.json()["iid"]

def create_issue(title, body, epic_iid, labels):
    r = requests.post(f"{BASE}/projects/{PROJECT}/issues",
        headers=H, json={"title": title, "description": body,
                         "epic_iid": epic_iid, "labels": ",".join(labels)})
    r.raise_for_status()
    return r.json()["iid"], r.json()["web_url"]

def add_block(blocker_iid, blocked_iid):
    requests.post(f"{BASE}/projects/{PROJECT}/issues/{blocker_iid}/links",
        headers=H, json={"target_project_id": PROJECT.replace("%2F", "/"),
                         "target_issue_iid": blocked_iid, "link_type": "blocks"})
```

---

### Azure DevOps

```python
import requests, base64

PAT = "{ado_pat}"
ORG_URL = "{ado_org_url}".rstrip("/")
PROJECT = "{ado_project}"
AREA = "{area_path}" or PROJECT
ITER = "{iteration_path}" or None

auth = base64.b64encode(f":{PAT}".encode()).decode()
H = {"Authorization": f"Basic {auth}", "Content-Type": "application/json-patch+json"}
API = f"{ORG_URL}/{PROJECT}/_apis/wit"

def create_work_item(item_type, title, desc, tags="", parent_url=None):
    payload = [
        {"op": "add", "path": "/fields/System.Title",       "value": title},
        {"op": "add", "path": "/fields/System.Description", "value": desc},
        {"op": "add", "path": "/fields/System.AreaPath",    "value": AREA},
        {"op": "add", "path": "/fields/System.Tags",        "value": tags},
    ]
    if ITER:
        payload.append({"op": "add", "path": "/fields/System.IterationPath", "value": ITER})
    if parent_url:
        payload.append({"op": "add", "path": "/relations/-",
                        "value": {"rel": "System.LinkTypes.Hierarchy-Reverse",
                                  "url": parent_url}})
    r = requests.post(f"{API}/workitems/${item_type}?api-version=7.1",
        headers=H, json=payload)
    r.raise_for_status()
    d = r.json()
    return d["id"], d["url"]

def add_predecessor(blocker_url, blocked_id):
    payload = [{"op": "add", "path": "/relations/-",
                "value": {"rel": "System.LinkTypes.Dependency-Forward", "url": blocker_url}}]
    requests.patch(f"{API}/workitems/{blocked_id}?api-version=7.1", headers=H, json=payload)
```

Type mapping: `epic` → `"Epic"`, database/backend/frontend tasks → `"User Story"`, integration tasks → `"Task"`.
Pass `parent_url` (Epic's `url` field) when creating child items to wire hierarchy at creation time.

---

### Jira

```python
import requests, base64

SITE = "{jira_site}"
EMAIL = "{jira_email}"
TOKEN = "{jira_api_token}"
PROJECT_KEY = "{jira_project_key}"
BASE = f"https://{SITE}/rest/api/3"

auth = base64.b64encode(f"{EMAIL}:{TOKEN}".encode()).decode()
H = {"Authorization": f"Basic {auth}", "Content-Type": "application/json",
     "Accept": "application/json"}

def create_issue(summary, desc_text, issue_type, parent_key=None, labels=None):
    fields = {
        "project": {"key": PROJECT_KEY},
        "issuetype": {"name": issue_type},
        "summary": summary,
        "description": {"type": "doc", "version": 1,
                        "content": [{"type": "paragraph",
                                     "content": [{"type": "text", "text": desc_text}]}]},
        "labels": labels or []
    }
    if parent_key:
        fields["parent"] = {"key": parent_key}
    r = requests.post(f"{BASE}/issue", headers=H, json={"fields": fields})
    if r.status_code == 400 and parent_key:
        # Classic project — try Epic Link custom field
        fields.pop("parent", None)
        fields["customfield_10014"] = parent_key
        r = requests.post(f"{BASE}/issue", headers=H, json={"fields": fields})
    r.raise_for_status()
    key = r.json()["key"]
    return key, f"https://{SITE}/browse/{key}"

def add_block(blocker_key, blocked_key):
    requests.post(f"{BASE}/issueLink", headers=H,
        json={"type": {"name": "Blocks"},
              "inwardIssue": {"key": blocker_key},
              "outwardIssue": {"key": blocked_key}})
```

Issue type: epic → `"Epic"`, tasks → `"Story"` (fall back to `"Task"` on 400).

---

### Linear

```python
import requests

API_KEY = "{linear_api_key}"
TEAM_ID = "{linear_team_id}"
BASE = "https://api.linear.app/graphql"
H = {"Authorization": API_KEY, "Content-Type": "application/json"}

def gql(query, variables):
    r = requests.post(BASE, headers=H, json={"query": query, "variables": variables})
    r.raise_for_status()
    d = r.json()
    if "errors" in d:
        raise Exception(d["errors"])
    return d["data"]

CREATE_ISSUE = """mutation($teamId:String!,$title:String!,$description:String,
  $parentId:String,$labelIds:[String!]){
  issueCreate(input:{teamId:$teamId,title:$title,description:$description,
    parentId:$parentId,labelIds:$labelIds}){issue{id identifier url}}
}"""

def create_issue(title, description, parent_id=None, label_ids=None):
    d = gql(CREATE_ISSUE, {"teamId": TEAM_ID, "title": title,
                            "description": description, "parentId": parent_id,
                            "labelIds": label_ids or []})
    i = d["issueCreate"]["issue"]
    return i["id"], i["identifier"], i["url"]

def add_blocks(blocker_id, blocked_id):
    gql("""mutation($a:String!,$b:String!,$t:IssueRelationType!){
      issueRelationCreate(input:{issueId:$a,relatedIssueId:$b,type:$t}){issueRelation{id}}
    }""", {"a": blocker_id, "b": blocked_id, "t": "blocks"})
```

If the user chose Epics → Projects: use `projectCreate` mutation first, then set `projectId` on child issues instead of `parentId`.

---

## Platform Data Model Mappings

### GitHub
| Manifest Field | GitHub |
|---|---|
| `type: "epic"` | Issue + `epic` label |
| `type: "task"` | Issue |
| `parent_epic_id` | Sub-issue link (body ref fallback) |
| `category[]` | Labels |
| `dependencies[].type = "blocking"` | Body: "Blocked by #N" |

### GitLab
| Manifest Field | GitLab |
|---|---|
| `type: "epic"` | Group Epic |
| `type: "task"` | Project Issue with `epic_iid` |
| `category[]` | Labels |
| `dependencies[].type = "blocking"` | Issue link `blocks` |

### Azure DevOps
| Manifest Field | ADO |
|---|---|
| `type: "epic"` | Epic |
| `type: "task"` (db/backend/frontend) | User Story |
| `type: "task"` (integration) | Task |
| `parent_epic_id` | `Hierarchy-Reverse` relation |
| `dependencies[].type = "blocking"` | `Dependency-Forward` relation |
| `category[]` | Tags |

### Jira
| Manifest Field | Jira |
|---|---|
| `type: "epic"` | Epic |
| `type: "task"` | Story (or Task) |
| `parent_epic_id` | `parent` field / `customfield_10014` |
| `dependencies[].type = "blocking"` | Issue link "Blocks" |
| `category[]` | Labels |

### Linear
| Manifest Field | Linear |
|---|---|
| `type: "epic"` | Parent Issue or Project |
| `type: "task"` | Issue with `parentId` |
| `dependencies[].type = "blocking"` | Relation `blocks` |
| `execution_order` | Priority (1=Urgent→4=Low) |

---

## Step 6 — Write Platform Mapping File

After all items are created, save `/ai-context/pms-map.json`:

```json
{
  "platform": "github",
  "project": "myorg/myrepo",
  "created_at": "ISO-8601-timestamp",
  "items": [
    {
      "internal_id": "AUTH-EPIC",
      "platform_id": "42",
      "platform_url": "https://github.com/myorg/myrepo/issues/42",
      "title": "[EPIC] Authentication (F-01)",
      "type": "epic"
    }
  ],
  "failures": []
}
```

## Step 7 — Present Creation Summary

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PUSH TO PMS — COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Platform : [Platform Name]
Project  : [project path or key]

| Internal ID  | Title                                       | Type  | Platform ID | URL   | Status  |
|-------------|---------------------------------------------|-------|-------------|-------|---------|
| AUTH-EPIC   | [EPIC] Authentication                        | Epic  | #42         | [url] | Created |
| AUTH-DB-001 | [AUTH-DB-001] Create users table migration   | Task  | #43         | [url] | Created |

Epics created   : N
Tasks created   : N
Links wired     : N
Titles auto-fixed : N (missing/wrong prefix — corrected before creation; 0 if manifest was already compliant)
Failures        : N (see below if any)

Mapping saved to: /ai-context/pms-map.json

Ready to Develop. ✅
```

---

## Rules / Guardrails

### NEVER
- Create child items before all Epics are created (Phase A must complete before Phase B)
- Wire parent-child relationships before all child items in a group exist
- Silently skip failed items — always report failures with manual resolution steps
- Modify `/ai-context/issues.json` — read-only input; only `/ai-context/pms-map.json` is written
- Log or display credentials (PAT, API token) in the summary or mapping file
- Re-ask for credentials after a failure — report the raw API error so the user can diagnose scope/permission issues themselves

### ALWAYS
- Validate the manifest before asking any questions
- Present platform selection FIRST (Step 2), credentials SECOND (Step 3) — two separate elicitation forms
- Run `pip install requests --quiet --break-system-packages` before executing API scripts
- Record platform IDs immediately after each creation call
- Create Epics before child issues, regardless of platform
- Save `/ai-context/pms-map.json` even if some items failed
