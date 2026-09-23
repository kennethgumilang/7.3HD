# SETUP_GUIDE — Task Manager API DevOps Pipeline (SIT223/SIT753 HD Task)

This gets you a working 7-stage Jenkins pipeline (Build, Test, Code Quality,
Security, Deploy, Release, Monitoring) for the Task Manager API, using only
free, locally-run tools — no cloud accounts required. Everything below runs
on your own machine.

Target band: this setup gets you all 7 stages **functioning correctly**
(Mid-High HD, 86–95%). The "optional enhancements" at the end push specific
criteria toward Top HD if you have time.

## 0. Prerequisites

Install if you don't already have them:
- **Docker Desktop** (includes Docker Compose) — docker.com
- **Git**
- A **GitHub** account

Verify:
```bash
docker --version
docker compose version
git --version
```

## 1. Push this project to GitHub

```bash
cd taskapi
git init
git add .
git commit -m "Initial commit: Task Manager API"
git branch -M main
git remote add origin https://github.com/<your-username>/taskapi.git
git push -u origin main
```

In GitHub → repo → **Settings → Collaborators**, add your marking tutor and
the unit chair with at least Read access (the task sheet is explicit that
both need access — don't lose marks over this).

## 2. Run Jenkins locally (in Docker, with Docker access)

Jenkins needs to be able to run `docker build` / `docker compose` itself, so
run it with the host's Docker socket mounted in:

```bash
docker volume create jenkins_home

docker run -d --name jenkins \
  -p 8080:8080 -p 50000:50000 \
  -v jenkins_home:/var/jenkins_home \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -u root \
  jenkins/jenkins:lts
```

Then give the Jenkins container the `docker` CLI itself (the image doesn't
ship it by default):

```bash
docker exec -u root jenkins bash -c "curl -fsSL https://get.docker.com | sh"
docker exec -u root jenkins bash -c "apt-get update && apt-get install -y python3 python3-venv python3-pip"
```

Get the initial admin password and open Jenkins:
```bash
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```
Go to **http://localhost:8080**, paste the password, choose **Install
suggested plugins**, then create your admin user.

## 3. Install extra Jenkins plugins

**Manage Jenkins → Plugins → Available plugins**, install:
- Docker Pipeline
- Git
- JUnit
- (optional, only if you set up SonarQube in step 6) SonarQube Scanner
- (optional) Email Extension or Slack Notification, for real alerting

Restart Jenkins after installing.

## 4. Create the pipeline job

1. **New Item → Pipeline**, name it `taskapi-pipeline`.
2. Under **Pipeline**, set **Definition** to `Pipeline script from SCM`.
3. **SCM**: Git → paste your GitHub repo URL.
4. **Branch**: `*/main`.
5. **Script Path**: `Jenkinsfile` (already correct by default).
6. Save.

## 5. Run it

Click **Build Now**. Watch the stage view — you should see Checkout, Build,
Test, Code Quality, Security, Deploy, Release, Monitoring go green in order.

If a stage fails, click into it and read the console log — the most common
first-run issues are:
- `docker: command not found` → re-run the `get.docker.com` install from
  step 2 inside the Jenkins container.
- `python3: command not found` → re-run the `apt-get install` line from
  step 2.
- Port `5000`/`5001` already in use → stop whatever's using it, or change
  the port mapping in `docker-compose.yml`.

Once green, check the running app:
```bash
curl http://localhost:5001/health   # staging
curl http://localhost:5000/health   # production, after Release stage
curl http://localhost:5000/metrics  # Prometheus-format metrics
```

Take your **Jenkins pipeline screenshot** here (Stage View, all 7 stages
green) — that's the screenshot the report template asks for.

## 6. Optional: SonarQube for the Code Quality stage

The task explicitly names SonarQube as a suggested tool. The Jenkinsfile
currently uses flake8 + pylint (which already satisfies the Code Quality
criterion). To upgrade to SonarQube:

```bash
docker run -d --name sonarqube -p 9000:9000 sonarqube:community
```
Open http://localhost:9000 (default login admin/admin, you'll be asked to
change it), create a project token, then in Jenkins:
**Manage Jenkins → System → SonarQube servers**, add a server named
`sonarqube` pointing at `http://host.docker.internal:9000` with the token.
Also install `sonar-scanner` on the Jenkins agent (or run it via the
`sonarsource/sonar-scanner-cli` Docker image). Then uncomment the
`withSonarQubeEnv` block in the `Code Quality` stage of the Jenkinsfile.

## 7. Optional: fuller monitoring (Prometheus + Grafana)

This pushes the Monitoring criterion from "alerts triggered and explained"
toward "fully integrated system with live metrics":

```bash
docker compose --profile monitoring up -d
```
Open Grafana at http://localhost:3000 (admin/admin), add Prometheus
(http://prometheus:9090) as a data source, and build a simple dashboard on
`taskapi_requests_total` and `taskapi_request_latency_seconds`. Screenshot
the dashboard for your report.

## 8. Record the demo video (≤10 min)

Cover, in order:
1. Clone the repo, open the Jenkinsfile briefly.
2. Show the Jenkins job configuration (SCM pointing at your repo).
3. Click Build Now, narrate each stage as it goes green, pause on Test
   (show JUnit results), Code Quality (show flake8/pylint or SonarQube
   output), and Security (show the bandit finding and explain it — see
   below).
4. Show `curl http://localhost:5000/health` and `/tasks` working against
   the released production container.
5. If you did the Prometheus/Grafana step, show the dashboard.

## 9. What to say about the Security stage finding

Bandit will flag one Medium-severity issue in `app/app.py`:

> **B104: hardcoded_bind_all_interfaces** — `app.run(host="0.0.0.0", ...)`

This is expected and justified, not a bug to "fix": binding to `0.0.0.0` is
required so the Flask dev server is reachable from outside the Docker
container. In production the app doesn't actually use this code path at all
— `gunicorn` (set in the Dockerfile's `CMD`) serves the app instead, and
external exposure is controlled entirely by the port mapping in
`docker-compose.yml`, not by the bind address. Use this exact reasoning in
your report's Security stage description — it's a good example of
"vulnerability categorised and addressed/justified" for the rubric.

## 10. Filling in the report

Use `taskapi-report.docx` (already drafted for you) — just:
- Paste your demo video link and GitHub repo link into the two link fields.
- Paste in the Jenkins Stage View screenshot from step 5.
- Double-check the stage count matches what actually went green for you.
