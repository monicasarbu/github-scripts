#!/usr/bin/env python
""" Generate updates with the pull requests that were merged in the last week in the Beats related repositories """

import sys
from os.path import expanduser
import requests
import datetime


base = "https://api.github.com"

major_poi = {

    "docs": "Documentation",
    "libbeat": "All Beats",
    "Metricbeat": "Metricbeat",
    "Packetbeat": "Packetbeat",
    "Filebeat": "Filebeat",
    "Heartbeat": "Heartbeat",
    "Winlogbeat": "Winlogbeat",
    ":Packaging": "Packaging",
    ":Infra": "Infrastructure",
    "new Beat": "New community Beats",
}


def get_PRs(session, search):

    prs = []

    q = ""
    params = []

    for key, value in search.iteritems():
        params.append(key + ":" + value)
    q = '+'.join(params)

    page = 1
    while True:
        url = "{}/search/issues?q={}&page={}".format(base, q, page)
        result = session.get(url).json()
        if len(result["items"]) == 0:
            break

        prs.extend(result["items"])
        page += 1

    return prs


def get_PR(session, path, number):

    url = "{}/repos/{}/pulls/{}".format(base, path, number)

    result = session.get(url).json()

    return result


def get_labels(pr):

    labels = []

    if "labels" in pr:
        for label in pr["labels"]:
            labels.append(label["name"])

    return labels


def get_poi(labels):

    for poi in major_poi:
        if poi in labels:
            return major_poi[poi]
    return "Other"


def get_branch(pr):
    if "base" in pr:
        return pr["base"]["label"]


def get_backported_pr(pr):

    v = pr["title"].split()
    return (v[1][1:])


def dump_poi_to_html(poi, details):

    print "<p><strong>{}</strong></p>".format(poi)

    for branch, prs in details.iteritems():

        print "<p>Changes in {}:</p>".format(branch)

        print "<p><ul>"
        for pr in prs:
            print "<li>{} <a href=\"{}\">#{}</a> {}</li>".format(pr["title"], pr["link"], pr["number"], pr["labels"])
        print "</ul></p>"


def main():

    token = open(expanduser("~/.github_token"), "r").read().strip()
    session = requests.Session()
    session.headers.update({"Authorization": "token " + token})
    session.headers.update({"Accept": "application/vnd.github.v3+json"})

    week_ago = datetime.date.today()-datetime.timedelta(days=14)

    print "Merged pull requests since {}:".format(week_ago)

    summary = {}
    ignore_prs = []

    # get all closed PRs from the beats repo
    prs = get_PRs(session, {"repo": "elastic%2Fbeats", "is": "pr", "state": "closed", "merged":">"+week_ago.strftime("%Y-%m-%d")})
    for pr in prs:
        pr_details = get_PR(session, "elastic/beats", pr["number"])

        labels = get_labels(pr)

        if "backport" in labels:
            backported_pr_number = get_backported_pr(pr)
            ignore_prs.append(backported_pr_number)
        elif pr["number"] in ignore_prs:
            print "Ignore PR #{}".format(pr["number"])
            continue

        poi = get_poi(labels)
        branch = get_branch(pr_details).split(":")[1]

        if poi not in summary:
            summary[poi] = {}

        if branch not in summary[poi]:
            summary[poi][branch] = []

        summary[poi][branch].append({
            "number": pr["number"],
            "title": pr["title"],
            "merged_at": pr_details["merged_at"],
            "link": "https://github.com/elastic/beats/pull/{}".format(pr["number"]),
            "labels": labels
            })

    for poi, changes in summary.iteritems():
        dump_poi_to_html(poi, changes)

    # get all closed PRs from the kibana repo, done by Chris
    prs = get_PRs(session, {"repo": "elastic%2Fkibana", "is": "pr", "state": "closed", "merged":
    ">"+week_ago.strftime("%Y-%m-%d"), "author": "simianhacker" })

    kibana_prs = {}
    for pr in prs:
        pr_details = get_PR(session, "elastic/kibana", pr["number"])

        labels = get_labels(pr)
        branch = get_branch(pr_details).split(":")[1]

        if branch not in kibana_prs:
            kibana_prs[branch] = []

        kibana_prs[branch].append({
            "number": pr["number"],
            "title": pr["title"],
            "merged_at": pr_details["merged_at"],
            "link": "https://github.com/elastic/kibana/pull/{}".format(pr["number"]),
            "labels": labels
            })

    dump_poi_to_html("Changes in Kibana", kibana_prs)


if __name__ == "__main__":
    sys.exit(main())
