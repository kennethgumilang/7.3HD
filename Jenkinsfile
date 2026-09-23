pipeline {
    agent any

    environment {
        IMAGE_NAME = "taskapi"
        IMAGE_TAG  = "${env.BUILD_NUMBER}"
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build') {
            steps {
                sh """
                    docker build -t ${IMAGE_NAME}:${IMAGE_TAG} -t ${IMAGE_NAME}:latest .
                """
            }
        }

        stage('Test') {
            steps {
                sh """
                    mkdir -p reports
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install --quiet -r requirements-dev.txt
                    python3 -m pytest tests/ --junitxml=reports/junit.xml --cov=app --cov-report=xml:reports/coverage.xml
                """
            }
            post {
                always {
                    junit 'reports/junit.xml'
                }
            }
        }

        stage('Code Quality') {
            steps {
                sh """
                    . .venv/bin/activate
                    flake8 app/ --max-line-length=100 --format=default > reports/flake8.txt || true
                    pylint app/ --exit-zero > reports/pylint.txt
                """
                archiveArtifacts artifacts: 'reports/flake8.txt, reports/pylint.txt', allowEmptyArchive: true
            }
        }

        stage('Security') {
            steps {
                sh """
                    . .venv/bin/activate
                    bandit -r app/ -f txt -o reports/bandit.txt || true
                    pip-audit -r app/requirements.txt -f json -o reports/pip-audit.json || true
                """
                archiveArtifacts artifacts: 'reports/bandit.txt, reports/pip-audit.json', allowEmptyArchive: true
            }
        }

        stage('Deploy') {
            steps {
                sh """
                    IMAGE_TAG=${IMAGE_TAG} docker compose --profile staging up -d --force-recreate staging
                    sleep 5
                    docker exec taskapi-staging python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"
                """
            }
        }

        stage('Release') {
            steps {
                sh """
                    docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${IMAGE_NAME}:release
                    git tag -f release-${IMAGE_TAG} || true
                    IMAGE_TAG=release docker compose --profile production up -d --force-recreate production
                    sleep 5
                    docker exec taskapi-production python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"
                """
            }
        }

        stage('Monitoring') {
            steps {
                script {
                    def health = sh(
                        script: "docker exec taskapi-production python3 -c \"import urllib.request; print(urllib.request.urlopen('http://localhost:5000/health').status)\"",
                        returnStdout: true
                    ).trim()
                    if (health != '200') {
                        error "Production health check failed with status ${health} — alerting team."
                    } else {
                        echo "Production is healthy (HTTP ${health})."
                    }
                }
                sh "docker exec taskapi-production python3 -c \"import urllib.request; print(urllib.request.urlopen('http://localhost:5000/metrics').read().decode()[:500])\""
            }
        }
    }

    post {
        failure {
            echo "Pipeline FAILED at stage: ${env.STAGE_NAME}. An alert would be sent here."
        }
        always {
            sh "docker image prune -f || true"
        }
    }
}