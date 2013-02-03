# github-jenkins-trigger

This is a tiny Heroku-compatible application which helps trigger builds in
Jenkins from a GitHub post-receive hook.

## The problem

The [Jenkins GitHub plugin][1] simplifies the process of triggering builds
when you push to GitHub. Unfortunately, it doesn't offer any way of making
sure that you only build the branch that was pushed (which you might want if
you wish to build every pushed branch and submit the results to the [GitHub
commit status API][2]).

[1]: https://wiki.jenkins-ci.org/display/JENKINS/GitHub+Plugin
[2]: http://developer.github.com/v3/repos/statuses/

## The solution

This application sits between GitHub and Jenkins, receives the GitHub
post-receive hook, and then submits a request to Jenkins that triggers a
parameterised build. By default, it will set a parameter of `BRANCH` to the
name of the pushed branch (e.g. `master`, `feature/foo`).

## Deployment and configuration

First, allow remote triggering of your Jenkins job by enabling the "Trigger
builds remotely (e.g., from scripts)" option in the job configuration page.
Create a unique authentication token (using `uuidgen(1)`, for example) and
make a note of it.

Next, spin up an instance of this application on Heroku:

    git clone https://github.com/alphagov/jenkins-trigger-build
    heroku create
    git push heroku master

If your Heroku application is running at http://myapp-123.herokuapp.com, you
should now add a WebHook to your GitHub project. Use the following URL as a
template, removing newlines which have been added here for clarity:

    http://myapp-123.herokuapp.com/build?jenkins_url=<root_url>
                                        &jenkins_job=<job_name>
                                        &jenkins_token=<token>

For example:

    http://myapp-123.herokuapp.com/build?jenkins_url=http://jenkins.acmecorp.com
                                        &jenkins_job=acme-product
                                        &jenkins_token=4e7ea85b-8ed0-458f-a055-e18519cde94b

Other optional parameters include:

- `jenkins_user`: HTTP basic auth username for Jenkins authentication
- `jenkins_password`: HTTP basic auth password for Jenkins authentication
- `jenkins_param_key`: override build parameter name (default: `BRANCH`)

You can also set a Heroku config option telling the service to ignore pushes
to specified branches:

    heroku config set IGNORE_BRANCHES=master,release

## License

`github-jenkins-trigger` is released under the MIT license, a copy of which
can be found in `LICENSE`.
