import logging
import json
from os import environ

from flask import Flask, Response
from flask import abort as _abort, jsonify, request
import requests

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
log = logging.getLogger(__name__)

DEBUG           = environ.get('DEBUG', 'false') == 'true'
IGNORE_BRANCHES = [b for b in environ.get('IGNORE_BRANCHES', '').split(',') if b != '']
REF_PREFIX      = 'refs/heads/'
JENKINS_URL     = environ.get('JENKINS_URL', '')

app.config.from_object(__name__)


def abort(message='An error occurred while processing your request', status=400, **data):
    data.update(status=status, message=message)
    resp = Response(json.dumps(data), content_type='application/json', status=status)
    _abort(resp)


def require_arg(name, default=None):
    val = request.args.get(name, default)
    if val is None:
        abort('No "{0}" query parameter supplied'.format(name))
    return val


@app.route('/', methods=('GET',))
def root():
    return jsonify(status=200, message='This is a GitHub webhook that triggers builds on Jenkins: https://github.com/alphagov/github-jenkins-trigger')


@app.route('/build', methods=('POST',))
def build():
    if JENKINS_URL == '':
        abort('Environment variable JENKINS_URL was not set')

    payload = _get_payload()
    branch = _get_branch(payload)

    jenkins_job       = require_arg('jenkins_job')
    jenkins_token     = require_arg('jenkins_token')
    jenkins_url       = JENKINS_URL
    jenkins_user      = request.args.get('jenkins_user')
    jenkins_password  = request.args.get('jenkins_password', '')
    jenkins_param_key = require_arg('jenkins_param_key', 'BRANCH')

    url = '{jenkins_url}/job/{jenkins_job}/buildWithParameters'.format(**vars())
    params = {'token': jenkins_token,
              jenkins_param_key: branch}

    if branch in IGNORE_BRANCHES:
        msg = 'Ignoring push ("{0}" in IGNORE_BRANCHES)'.format(branch)
        log.debug(msg)
        return jsonify(status=200, message=msg)

    if payload.get('deleted'):
        msg = 'Ignoring branch deletion ("{0}")'.format(branch)
        log.debug(msg)
        return jsonify(status=200, message=msg)

    ip = requests.get('http://canhazip.com/').text.strip()

    log.debug('Submitting build request to %s with params %s from IP %s', url, params, ip)

    auth = None
    if jenkins_user is not None:
        auth = (jenkins_user, jenkins_password)
    res = requests.get(url, params=params, auth=auth, timeout=10)

    if res.ok:
        log.debug('Request submitted successfully to %s with params %s', url, params)
        return jsonify(status=200, message='Submitted request for build')
    else:
        log.warn('Failed to submit request to %s with params %s. Upstream status %s, body follows:', url, params, res.status_code)
        log.warn('%s', res.content)

        abort('Error communicating with Jenkins',
              status=500,
              upstream_status=res.status_code,
              upstream_response_body=res.content)


def _get_payload():
    """Parse and return the POST payload"""
    payload_json = request.form.get('payload')
    if payload_json is None:
        abort('No "payload" POST parameter supplied')

    try:
        payload = json.loads(payload_json)
    except ValueError:
        abort('Error encountered when parsing payload JSON')

    return payload


def _get_branch(payload):
    """Extract the branch name from the payload data"""
    ref = payload.get('ref')

    if ref is None:
        abort('No "ref" supplied in payload')

    if not ref.startswith(REF_PREFIX):
        abort('Invalid format for "ref" in payload: should be "{0}/BRANCHNAME"'.format(REF_PREFIX))

    branch = ref[len(REF_PREFIX):]
    return branch


if __name__ == '__main__':
    port = int(environ.get('PORT', 5000))
    host = '0.0.0.0'
    app.run(host=host, port=port)
