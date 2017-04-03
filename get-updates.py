#!/usr/bin/env python
""" Generate updates with the pull requests that were merged in the last week in the Beats related repositories """

import sys
from os.path import expanduser
import requests
import datetime
from pprint import pprint

base = "https://api.github.com"

beats_poi = {

    "docs": "Documentation",
    "libbeat": "All Beats",
    "Metricbeat": "Metricbeat",
    "Packetbeat": "Packetbeat",
    "Filebeat": "Filebeat",
    "Heartbeat": "Heartbeat",
    "Winlogbeat": "Winlogbeat",
    ":Packaging": "Packaging",
    ":Infra": "Infrastructure",
    "new beat": "New community Beats",
}


def get_pages(session, search):

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


def get_PRs(session, repo, search):

    prs = []
    found_prs = get_pages(session, search)

    for pr in found_prs:
        pr_details = get_PR(session, repo, pr["number"])

        labels = get_labels(session, repo, pr["number"])
        branch = get_branch(pr_details).split(":")[1]

        if "backport" in labels:
            for backported_pr_number in get_backported_prs(pr):
                pr_details = get_PR(session, repo, backported_pr_number)
                labels = get_labels(session, repo, backported_pr_number)

                prs.append({
                    "number": backported_pr_number,
                    "title": pr_details["title"],
                    "merged_at": pr_details["merged_at"],
                    "link": "https://github.com/{}/pull/{}".format(repo, pr_details["number"]),
                    "branch": branch,
                    "poi": get_poi(repo, labels),
                    })
        else:

            prs.append({
                "number": pr_details["number"],
                "title": pr_details["title"],
                "merged_at": pr_details["merged_at"],
                "link": "https://github.com/{}/pull/{}".format(repo, pr_details["number"]),
                "branch": branch,
                "poi": get_poi(repo, labels),
            })

    pprint(prs)
    return prs


def get_PR(session, path, number):

    url = "{}/repos/{}/pulls/{}".format(base, path, number)

    result = session.get(url).json()

    return result


def get_labels(session, path, number):

    url = "{}/repos/{}/issues/{}/labels".format(base, path, number)

    result = session.get(url).json()

    labels = []
    for label in result:
        labels.append(label["name"])

    return labels


def get_poi(repo, labels):

    if repo == "elastic/beats":
        for poi in beats_poi:
            if poi in labels:
                return beats_poi[poi]
    elif repo == "elastic/kibana":
        return "Kibana"
    return "Other"


def get_branch(pr):
    if "base" in pr:
        return pr["base"]["label"]


def get_backported_prs(pr):

    backported_prs = []
    title_by_words = pr["title"].split()
    for word in title_by_words:
        if word.startswith("#"):
            backported_prs.append(word[1:])

    return backported_prs


def dump_poi_to_html(html, poi, details):

    html.write("<p><strong>{}</strong></p>".format(poi))

    for branch, prs in details.iteritems():

        html.write("<p>Changes in {}:</p>".format(branch))

        html.write("<p><ul>")
        for pr in prs:
            html.write("<li>{} <a href=\"{}\">#{}</a></li>".format(pr["title"], pr["link"], pr["number"]))
        html.write("</ul></p>")


def dump_changes(prs, html):

    summary = {}
    for pr in prs:
        poi = pr["poi"]
        branch = pr["branch"]

        if poi not in summary:
            summary[poi] = {}
        if branch not in summary[poi]:
            summary[poi][branch] = []

        summary[poi][branch].append(pr)

    for poi, changes in summary.iteritems():
        dump_poi_to_html(html, poi, changes)


def main():

    token = open(expanduser("~/.github_token"), "r").read().strip()
    session = requests.Session()
    session.headers.update({"Authorization": "token " + token})
    session.headers.update({"Accept": "application/vnd.github.v3+json"})

    week_ago = datetime.date.today()-datetime.timedelta(days=7)

    print "Collect all pull requests merged since {}".format(week_ago)

    out_file = "/tmp/updates.html"

    with open(out_file, 'w') as out:

        # get all closed PRs from the beats repo
        prs = get_PRs(session, "elastic/beats", {"repo": "elastic%2Fbeats", "is": "pr", "state": "closed", "merged":">"+week_ago.strftime("%Y-%m-%d")})
        dump_changes(prs, out)


        prs = get_PRs(session, "elastic/kibana", {"repo": "elastic%2Fkibana", "is": "pr", "state": "closed", "merged":
        ">"+week_ago.strftime("%Y-%m-%d"), "author": "simianhacker" })
        dump_changes(prs, out)

    print "{} was generated".format(out_file)

if __name__ == "__main__":
    sys.exit(main())
