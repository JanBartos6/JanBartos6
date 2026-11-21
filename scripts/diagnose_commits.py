"""One-off: explain why the card's commit count differs from what you expect.

Prints totals only (no repo names, no full email addresses), because Actions logs on a public
repo are public.
"""
import collections
import datetime
import json
import os
import re
import urllib.request

API = "https://api.github.com/graphql"
TOKEN = os.environ["ACCESS_TOKEN"]
LOGIN = os.environ.get("USER_NAME", "JanBartos6")
NAME_RE = re.compile(r"jan|bart|honz", re.I)


def gql(query, **variables):
    req = urllib.request.Request(
        API,
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        out = json.load(r)
    if "errors" in out:
        raise RuntimeError(out["errors"])
    return out["data"]


def owned_repos():
    q = """query($login:String!,$cursor:String){user(login:$login){id createdAt
      repositories(ownerAffiliations:OWNER,first:100,after:$cursor){pageInfo{hasNextPage endCursor}
      nodes{name isFork defaultBranchRef{name}}}}}"""
    repos, cursor = [], None
    while True:
        u = gql(q, login=LOGIN, cursor=cursor)["user"]
        repos += u["repositories"]["nodes"]
        p = u["repositories"]["pageInfo"]
        if not p["hasNextPage"]:
            return u["id"], u["createdAt"], repos
        cursor = p["endCursor"]


def yearly(created):
    first = int(created[:4])
    now = datetime.datetime.now(datetime.timezone.utc)
    parts = []
    for y in range(first, now.year + 1):
        end = now.isoformat() if y == now.year else f"{y}-12-31T23:59:59Z"
        parts.append(
            f'y{y}: contributionsCollection(from:"{y}-01-01T00:00:00Z", to:"{end}") {{'
            " totalCommitContributions restrictedContributionsCount"
            " contributionCalendar { totalContributions }"
            " commitContributionsByRepository(maxRepositories: 100) { repository { owner { login } } contributions { totalCount } } }"
        )
    data = gql("query($login:String!){user(login:$login){" + " ".join(parts) + "}}", login=LOGIN)["user"]
    return data


def scan(repo, uid):
    q = """query($owner:String!,$name:String!,$cursor:String){repository(owner:$owner,name:$name){
      defaultBranchRef{target{... on Commit{history(first:100,after:$cursor){pageInfo{hasNextPage endCursor}
      nodes{author{name email user{login}}}}}}}}}"""
    counts = collections.Counter()
    domains = collections.Counter()
    cursor = None
    while True:
        ref = gql(q, owner=LOGIN, name=repo, cursor=cursor)["repository"]["defaultBranchRef"]
        if not ref:
            return counts, domains
        h = ref["target"]["history"]
        for n in h["nodes"]:
            a = n["author"] or {}
            user = (a.get("user") or {}).get("login")
            if user == LOGIN:
                counts["linked_to_you"] += 1
            elif user is None and NAME_RE.search(a.get("name") or ""):
                counts["your_name_unlinked_email"] += 1
                domains[(a.get("email") or "@?").split("@")[-1].lower()] += 1
            elif user is None:
                counts["other_unlinked"] += 1
            else:
                counts["other_people"] += 1
        if not h["pageInfo"]["hasNextPage"]:
            return counts, domains
        cursor = h["pageInfo"]["endCursor"]


def branch_extra(repo, uid, default):
    q = """query($owner:String!,$name:String!,$id:ID!){repository(owner:$owner,name:$name){
      refs(refPrefix:"refs/heads/",first:100){totalCount nodes{name target{... on Commit{history(author:{id:$id}){totalCount}}}}}}}"""
    refs = gql(q, owner=LOGIN, name=repo, id=uid)["repository"]["refs"]
    best = {n["name"]: n["target"]["history"]["totalCount"] for n in refs["nodes"]}
    d = best.get(default, 0)
    return max(best.values() or [0]) - d, refs["totalCount"]


def main():
    uid, created, repos = owned_repos()
    print(f"account created: {created[:10]}; owned repos: {len(repos)} ({sum(r['isFork'] for r in repos)} forks)")

    print("\n== GitHub's own yearly numbers (what the contribution graph shows) ==")
    data = yearly(created)
    tot_commit = tot_restricted = tot_contrib = tot_other_owner = 0
    for key in sorted(data):
        c = data[key]
        other = sum(r["contributions"]["totalCount"] for r in c["commitContributionsByRepository"]
                    if r["repository"]["owner"]["login"] != LOGIN)
        print(f"{key[1:]}: commits {c['totalCommitContributions']:>5}  private-restricted {c['restrictedContributionsCount']:>5}"
              f"  all contributions {c['contributionCalendar']['totalContributions']:>5}  commits in repos you don't own {other:>4}")
        tot_commit += c["totalCommitContributions"]
        tot_restricted += c["restrictedContributionsCount"]
        tot_contrib += c["contributionCalendar"]["totalContributions"]
        tot_other_owner += other
    print(f"ALL YEARS: commits {tot_commit}, restricted {tot_restricted}, all contributions {tot_contrib}, "
          f"commits in repos you don't own {tot_other_owner}")

    print("\n== Default branches of repos you own ==")
    total = collections.Counter()
    domains = collections.Counter()
    extra_branch = 0
    multi_branch_repos = 0
    for r in repos:
        if r["isFork"] or not r["defaultBranchRef"]:
            continue
        c, d = scan(r["name"], uid)
        total.update(c)
        domains.update(d)
        extra, nrefs = branch_extra(r["name"], uid, r["defaultBranchRef"]["name"])
        extra_branch += max(0, extra)
        multi_branch_repos += nrefs > 1
    for k, v in total.most_common():
        print(f"{k}: {v}")
    print("your-name commits under emails NOT linked to your account, by email domain:")
    for dom, v in domains.most_common():
        print(f"  {dom}: {v}")
    print(f"extra commits by you on non-default branches (lower bound): {extra_branch} "
          f"across {multi_branch_repos} repos with more than one branch")


if __name__ == "__main__":
    main()
