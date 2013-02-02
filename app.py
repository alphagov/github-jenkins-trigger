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


@app.route('/build', methods=('POST',))
def build():
    branch = _get_pushed_branch()

    if branch in IGNORE_BRANCHES:
        log.debug('Ignoring push on %s', branch)
        return jsonify(status=200, message='Ignoring push on {0}'.format(branch))

    jenkins_job       = require_arg('jenkins_job')
    jenkins_token     = require_arg('jenkins_token')
    jenkins_url       = require_arg('jenkins_url')
    jenkins_param_key = require_arg('jenkins_param_key', 'BRANCH')

    url = '{jenkins_url}/{jenkins_job}/buildWithParameters'.format(**vars())
    params = {'token': jenkins_token,
              jenkins_param_key: branch}

    log.debug('Submitting build request to %s with params %s', url, params)
    res = requests.get(url, data=params)

    if res.ok:
        log.debug('Request submitted successfully to %s with params %s', url, params)
        return jsonify(status=200, message='Submitted request for build')
    else:
        log.warn('Failed to submit request to %s with params %s. Upstream status %s, body follows:', url, params, res.status)
        log.warn('%s', res.body)

        abort('Error communicating with Jenkins',
              status=500,
              upstream_status=res.status,
              upstream_response_body=res.body)


def _get_pushed_branch():
    """Parse the POST payload and return the name of the pushed branch"""
    payload_json = request.form.get('payload')
    if payload_json is None:
        abort('No "payload" POST parameter supplied')

    try:
        payload = json.loads(payload_json)
    except ValueError:
        abort('Error encountered when parsing payload JSON')

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
