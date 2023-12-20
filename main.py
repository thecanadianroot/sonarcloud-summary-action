import re
import sys

import github as _github
import argparse


def parse_args(args):
    parser = argparse.ArgumentParser(description='Creates a summary of all the SonarCloud comments')
    parser.add_argument('-gr', '--github-repository', type=str, required=True)
    parser.add_argument('-gt', '--github-token', type=str, required=True)
    parser.add_argument('-pr', '--pull-request', type=int, required=True)
    parser.add_argument('-c', '--commit', type=str, required=False)

    parser.add_argument('-ch', '--comment-header', type=str, required=False, default="SonarCloud Summary:")

    parser.add_argument('-pnp', '--project-name-pattern', type=pattern, required=False)

    parser.add_argument('-qgp', '--quality-gate-pattern', type=pattern, required=False)
    parser.add_argument('-qgsp', '--quality-gate-sub-pattern', type=pattern, required=False)
    parser.add_argument('-qgsr', '--quality-gate-sub-repl', type=pattern, required=False)

    parser.add_argument('-ip', '--issues-pattern', type=pattern, required=False)
    parser.add_argument('-isp', '--issues-sub-pattern', type=pattern, required=False)
    parser.add_argument('-isr', '--issues-sub-repl', type=pattern, required=False)

    parser.add_argument('-shp', '--security-hotspots-pattern', type=pattern, required=False)
    parser.add_argument('-shsp', '--security-hotspots-sub-pattern', type=pattern, required=False)
    parser.add_argument('-shsr', '--security-hotspots-sub-repl', type=pattern, required=False)

    parser.add_argument('-csp', '--code-smells-pattern', type=pattern, required=False)
    parser.add_argument('-cssp', '--code-smells-sub-pattern', type=pattern, required=False)
    parser.add_argument('-cssr', '--code-smells-sub-repl', type=pattern, required=False)

    parser.add_argument('-ccp', '--code-coverage-pattern', type=pattern, required=False)
    parser.add_argument('-ccsp', '--code-coverage-sub-pattern', type=pattern, required=False)
    parser.add_argument('-ccsr', '--code-coverage-sub-repl', type=pattern, required=False)

    parser.add_argument('-cdp', '--code-duplication-pattern', type=pattern, required=False)
    parser.add_argument('-cdsp', '--code-duplication-sub-pattern', type=pattern, required=False)
    parser.add_argument('-cdsr', '--code-duplication-sub-repl', type=pattern, required=False)

    return parser.parse_args(args)


def pattern(x: str):
    """
    Transforms a simple string into a raw string
    :param x: a string
    :return: a raw string
    """
    return repr(x)[1:-1]


def this_or_that(this, that):
    """
    Returns this or that using a ternary operation
    :param this: a value
    :param that: a value
    :return: this or that
    """
    return this if this else that


def substitute(sub, sub_alt, repl, repl_alt, string):
    """
    Substitutes unwanted stuff from a string
    :param sub: a substitution pattern
    :param sub_alt: an alternate substitution pattern (a default value)
    :param repl: a replacement pattern
    :param repl_alt: an alternate replacement pattern (a default value)
    :param string: a string
    :return: a string
    """
    return re.sub(this_or_that(sub, sub_alt), this_or_that(repl, repl_alt), string).rstrip()


if __name__ == '__main__':
    args = parse_args(sys.argv[1:])
    github = _github.Github(args.github_token)
    repo = github.get_repo(args.github_repository)
    issue = repo.get_issue(args.pull_request)

    commit = None
    if args.commit:
        commit = repo.get_commit(args.commit)

    comments = list(issue.get_comments())
    table = {}
    for comment in comments:
        if commit and commit.commit.committer.date > comment.created_at:  # skip comments related to older commits
            continue
        if comment.user.login == 'sonarcloud[bot]':
            m = re.search(
                this_or_that(args.project_name_pattern, r'id=(?P<project_name>[a-zA-Z0-9-_\.\:]+)&'),
                comment.body
            )
            if m:
                project_name = m.group("project_name")
                if project_name:
                    project = {
                        "quality-gate": "N/A",
                        "issues": "N/A",
                        "security-hotspots": "N/A",
                        "code-coverage": "N/A",
                        "code-duplication": "N/A",
                    }
                    for line in comment.body.splitlines(keepends=False):
                        if re.search(
                                this_or_that(args.quality_gate_pattern, r'\[!\[Quality Gate (Passed|Failed)\]'), line
                        ):
                            project["quality-gate"] = substitute(
                                args.quality_gate_sub_pattern, r'(.*)(\[!\[)(.*)(\]\(.*\)\])(\(.*\))(.*)',
                                args.quality_gate_sub_repl, r'\2\4\5',
                                line
                            )
                        elif re.search(
                                this_or_that(args.issues_pattern, r'\[\d+.*(issue|issues).*]'), line
                        ):
                            project["issues"] = substitute(
                                args.issues_sub_pattern, r'(.*)(\[\d+)(.*)(issue|issues)(.*)(\])',
                                args.issues_sub_repl, r'\2\6',
                                line
                            )
                        elif re.search(
                                this_or_that(args.security_hotspots_pattern,
                                             r'\[\d+.*(Security|security|Hotspot|hotspot|Hotspots|hotspots).*]'), line
                        ):
                            project["security-hotspots"] = substitute(
                                args.security_hotspots_sub_pattern,
                                r'(.*)(\[\d+)(.*)(Security|security|Hotspot|hotspot|Hotspots|hotspots)(.*)(\])',
                                args.security_hotspots_sub_repl, r'\2\6',
                                line
                            )
                        elif re.search(
                                this_or_that(args.code_coverage_pattern, r'\[\d+\.\d+%.*(Coverage|coverage).*\]'), line
                        ):
                            project["code-coverage"] = substitute(
                                args.code_coverage_sub_pattern, r'(.*)(\[\d+\.\d+%)(.*)(Coverage|coverage)(.*)(\])',
                                args.code_coverage_sub_repl, r'\2\6',
                                line
                            )
                        elif re.search(
                                this_or_that(args.code_duplication_pattern,
                                             r'\[\d+\.\d+%.*(Duplication|duplication).*\]'),
                                line
                        ):
                            project["code-duplication"] = substitute(
                                args.code_duplication_sub_pattern,
                                r'(.*)(\[\d+\.\d+%)(.*)(Duplication|duplication)(.*)(\])',
                                args.code_duplication_sub_repl, r'\2\6',
                                line
                            )
                    table[project_name] = project
    if table.keys():
        body = f'### {args.comment_header}\r\n| Project | Quality Gate | Issues | Security Hotspots | Coverage | Duplication |\r\n|---|:---:|:---:|:---:|:---:|:---:|'

        for key, value in sorted(table.items()):
            qg = value["quality-gate"]
            i = value["issues"]
            sh = value["security-hotspots"]
            cc = value["code-coverage"]
            cd = value["code-duplication"]
            body += f'\r\n| {key} | {qg} | {i} | {sh} | {cc} | {cd} |'

        print()
        # issue.create_comment(body)
