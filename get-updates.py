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


def get_PR(session, number):

    url = "{}/repos/elastic/beats/pulls/{}".format(base, number)

    result = session.get(url).json()

    return result


def get_labels(pr):

    labels = []

    if "labels" in pr:
        for label in pr["labels"]:
            labels.append(label["name"])

    return labels


def get_poi(pr):

    labels = get_labels(pr)

    for poi in major_poi:
        if poi in labels:
            return major_poi[poi]
        return "Other"


def get_branch(pr):
    if "base" in pr:
        return pr["base"]["label"]


def dump_html(summary):

    for branch, changes in summary.iteritems():
        print "<p><strong>Changes in {}</strong></p>".format(branch)

        print "<p>"
        for poi, list in changes.iteritems():
            print "<p>{}:</p>".format(poi)

            print "<ul>"
            for pr in list:
                print "<li>{} <a href=\"{}\">#{}</a> </li>".format(pr["title"], pr["link"], pr["number"])
            print "</ul>"
        print "</p>"


def main():

    token = open(expanduser("~/.github_token"), "r").read().strip()
    session = requests.Session()
    session.headers.update({"Authorization": "token " + token})
    session.headers.update({"Accept": "application/vnd.github.v3+json"})

    week_ago = datetime.date.today()-datetime.timedelta(days=7)

    print "Merged pull requests since {}:".format(week_ago)

    summary = {}

    prs = get_PRs(session, {"repo": "elastic%2Fbeats", "is": "pr", "state": "closed", "merged":">"+week_ago.strftime("%Y-%m-%d")})
    for pr in prs:
        pr_details = get_PR(session, pr["number"])

        poi = get_poi(pr)
        branch = get_branch(pr_details)

        if branch not in summary:
            summary[branch] = {}

        if poi not in summary[branch]:
            summary[branch][poi] = []

        summary[branch][poi].append({
            "number": pr["number"],
            "title": pr["title"],
            "merged_at": pr_details["merged_at"],
            "link": "https://github.com/elastic/beats/pull/{}".format(pr["number"])
            })

    dump_html(summary)

if __name__ == "__main__":
    sys.exit(main())
