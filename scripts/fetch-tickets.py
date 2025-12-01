#!/usr/bin/env python3
"""
Fetch Jira tickets from configured cloud instances.

Usage:
    fetch-tickets <instance-name>              # Fetch all open tickets assigned to you
    fetch-tickets <instance-name> <ticket-key> # Fetch a specific ticket
"""

import sys
import os
import json
import yaml
import requests
import re
from pathlib import Path
from requests.auth import HTTPBasicAuth


CONFIG_PATH = Path.home() / ".jira-config.yaml"

DEFAULT_CONFIG = """instances:
  example-company:
    url: https://example.atlassian.net
    email: your.email@example.com
    api_token: your_api_token_here
    jql: "assignee = currentUser() AND statusCategory != Done"
"""


def ensure_config_exists():
    """Create a template config file if it doesn't exist."""
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(DEFAULT_CONFIG)
        print(f"Created template config at {CONFIG_PATH}", file=sys.stderr)
        print("Please edit it with your Jira instance details.", file=sys.stderr)
        sys.exit(1)


def load_config():
    """Load and parse the YAML config file."""
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def strip_html(html_text):
    """Remove HTML tags from text."""
    if not html_text:
        return None
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', html_text)
    # Decode HTML entities
    text = text.replace('&nbsp;', ' ').replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def fetch_all_tickets(instance_config):
    """Fetch all open tickets assigned to the current user."""
    url = f"{instance_config['url']}/rest/api/3/search/jql"
    auth = HTTPBasicAuth(instance_config['email'], instance_config['api_token'])

    # Use custom JQL if provided, otherwise use default
    jql = instance_config.get('jql', 'assignee = currentUser() AND statusCategory != Done')

    params = {
        'jql': jql,
        'fields': 'key,summary,description,status,assignee,comment',
        'expand': 'renderedFields',
        'maxResults': 100
    }

    response = requests.get(url, auth=auth, params=params)
    response.raise_for_status()

    data = response.json()

    # Format the response to include only relevant fields
    tickets = []
    for issue in data.get('issues', []):
        # Get rendered description (HTML) and convert to plain text
        rendered_desc = issue.get('renderedFields', {}).get('description')
        description = strip_html(rendered_desc) if rendered_desc else None

        ticket = {
            'key': issue['key'],
            'summary': issue['fields'].get('summary'),
            'description': description,
            'status': issue['fields'].get('status', {}).get('name'),
            'assignee': issue['fields'].get('assignee', {}).get('displayName') if issue['fields'].get('assignee') else None,
            'comments': []
        }

        # Extract comments with author and timestamp
        comments_data = issue['fields'].get('comment', {})
        for comment in comments_data.get('comments', []):
            # Get rendered comment body if available
            rendered_body = comment.get('renderedBody')
            body = strip_html(rendered_body) if rendered_body else comment.get('body')

            ticket['comments'].append({
                'author': comment['author'].get('displayName'),
                'created': comment['created'],
                'body': body
            })

        tickets.append(ticket)

    return tickets


def fetch_single_ticket(instance_config, ticket_key):
    """Fetch a specific ticket by key."""
    url = f"{instance_config['url']}/rest/api/3/issue/{ticket_key}"
    auth = HTTPBasicAuth(instance_config['email'], instance_config['api_token'])

    params = {
        'fields': 'key,summary,description,status,assignee,comment',
        'expand': 'renderedFields'
    }

    response = requests.get(url, auth=auth, params=params)
    response.raise_for_status()

    issue = response.json()

    # Get rendered description (HTML) and convert to plain text
    rendered_desc = issue.get('renderedFields', {}).get('description')
    description = strip_html(rendered_desc) if rendered_desc else None

    # Format the ticket
    ticket = {
        'key': issue['key'],
        'summary': issue['fields'].get('summary'),
        'description': description,
        'status': issue['fields'].get('status', {}).get('name'),
        'assignee': issue['fields'].get('assignee', {}).get('displayName') if issue['fields'].get('assignee') else None,
        'comments': []
    }

    # Extract comments with author and timestamp
    comments_data = issue['fields'].get('comment', {})
    for comment in comments_data.get('comments', []):
        # Get rendered comment body if available
        rendered_body = comment.get('renderedBody')
        body = strip_html(rendered_body) if rendered_body else comment.get('body')

        ticket['comments'].append({
            'author': comment['author'].get('displayName'),
            'created': comment['created'],
            'body': body
        })

    return ticket


def main():
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    ensure_config_exists()
    config = load_config()

    instance_name = sys.argv[1]
    ticket_key = sys.argv[2] if len(sys.argv) > 2 else None

    if instance_name not in config['instances']:
        raise KeyError(f"Instance '{instance_name}' not found in config")

    instance_config = config['instances'][instance_name]

    if ticket_key:
        result = fetch_single_ticket(instance_config, ticket_key)
    else:
        result = fetch_all_tickets(instance_config)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
