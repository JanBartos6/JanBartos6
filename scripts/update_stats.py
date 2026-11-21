"""Fetch GitHub stats for the profile card and write stats.json.

Standard library only. Needs a classic personal access token with the `repo` and `read:user`
scopes in the ACCESS_TOKEN environment variable (repo is needed so private repos such as
JetGoal count towards commits and languages; their names and code are never shown).
"""
import datetime
import json
import os
import pathlib
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
API = "https://api.github.com/graphql"
TOKEN = os.environ.get("ACCESS_TOKEN", "")
LOGIN = os.environ.get("USER_NAME", "JanBartos6")
TOP_LANGUAGES = 3
CARD = json.loads((ROOT / "card.json").read_text(encoding="utf-8"))
# Repos that are mostly other people's code (downloaded copies, course material): they still
# count as repos and their commits by you still count, but their bytes don't skew "Top languages".
LANG_EXCLUDE = set(CARD.get("languages_exclude_repos", []))

if not TOKEN:
    print("ACCESS_TOKEN is not set: keeping the committed stats.json (see SETUP.md).")
    sys.exit(0)


def gql(query, **variables):
    req = urllib.request.Request(
        API,
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        out = json.load(r)
    if "errors" in out:
        raise RuntimeError(out["errors"])
    return out["data"]


USER_Q = """
query($login: String!, $cursor: String) {
  user(login: $login) {
    id
    contributionsCollection { contributionCalendar { totalContributions } }
    repositories(ownerAffiliations: OWNER, first: 100, after: $cursor) {
      pageInfo { hasNextPage endCursor }
      nodes {
        name
        isFork
        languages(first: 20, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } }
      }
    }
  }
}"""

COMMITS_Q = """
query($owner: String!, $name: String!, $id: ID!) {
  repository(owner: $owner, name: $name) {
    defaultBranchRef { target { ... on Commit { history(author: {id: $id}) { totalCount } } } }
  }
}"""


def main():
    repos, cursor = [], None
    while True:
        u = gql(USER_Q, login=LOGIN, cursor=cursor)["user"]
        repos += u["repositories"]["nodes"]
        page = u["repositories"]["pageInfo"]
        if not page["hasNextPage"]:
            break
        cursor = page["endCursor"]

    own = [r for r in repos if not r["isFork"]]
    forks = len(repos) - len(own)

    commits = 0
    langs = {}
    for r in own:
        ref = gql(COMMITS_Q, owner=LOGIN, name=r["name"], id=u["id"])["repository"]["defaultBranchRef"]
        if ref:
            commits += ref["target"]["history"]["totalCount"]
        if r["name"] in LANG_EXCLUDE:
            continue
        for e in r["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]

    total = sum(langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:TOP_LANGUAGES]
    languages = [[name, max(1, round(100 * size / total))] for name, size in top]

    stats = {
        "repos": len(own),
        "forks": forks,
        "commits": commits,
        "contributions": u["contributionsCollection"]["contributionCalendar"]["totalContributions"],
        "languages": languages,
        "updated": datetime.date.today().isoformat(),
    }
    (ROOT / "stats.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(stats))


if __name__ == "__main__":
    main()
