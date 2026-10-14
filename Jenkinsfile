pipeline {
    // Add the label "docker" to your Linux Jenkins execution node.
    agent { label 'docker' }

    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
        timeout(time: 20, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    triggers { githubPush() }

    parameters {
        string(name: 'NOTIFY_EMAIL', defaultValue: '',
               description: 'Optional: your email address. Configure SMTP before enabling.')
    }

    environment {
        PYTHONDONTWRITEBYTECODE = '1'
    }

    stages {
        stage('Checkout') {
            steps {
                deleteDir()
                checkout scm
                script {
                    def commitId = sh(
                        script: 'git rev-parse --short=12 HEAD',
                        returnStdout: true
                    ).trim()
                    env.IMAGE_TAG = "taskflow-ci:${env.BUILD_NUMBER}-${commitId}"
                }
            }
        }

        stage('Test inside Docker agent') {
            agent {
                docker {
                    image 'python:3.12-slim'
                    reuseNode true
                }
            }
            steps {
                sh '''
                    set -eu
                    python -m venv /tmp/taskflow-ci-venv
                    /tmp/taskflow-ci-venv/bin/python -m pip install --no-cache-dir -r requirements-dev.txt
                    mkdir -p reports
                    /tmp/taskflow-ci-venv/bin/python -m pytest -q -p no:cacheprovider --junitxml=reports/pytest.xml
                '''
            }
            post {
                always {
                    junit testResults: 'reports/pytest.xml', allowEmptyResults: true
                }
            }
        }

        stage('Build application image') {
            steps {
                sh 'docker build --pull --tag "$IMAGE_TAG" .'
            }
        }

        stage('Verify running container') {
            steps {
                sh '''
                    set -eu
                    name="taskflow-ci-check-${BUILD_NUMBER}-$(date +%s)-$$"
                    trap 'docker rm -f "$name" >/dev/null 2>&1 || true' EXIT
                    docker run --detach --name "$name" \
                        --env DATABASE_URL=sqlite:////tmp/taskflow-smoke.db \
                        --env SECRET_KEY=temporary-ci-only-secret-not-for-deployment \
                        "$IMAGE_TAG"
                    for attempt in $(seq 1 30); do
                        if docker exec "$name" python -c "import json,urllib.request; r=json.load(urllib.request.urlopen('http://127.0.0.1:8000/health',timeout=2)); assert r['database']=='connected'; print(r)"; then
                            echo 'Application and database health check passed.'
                            exit 0
                        fi
                        sleep 2
                    done
                    docker logs "$name"
                    exit 1
                '''
            }
        }
    }

    post {
        always {
            script {
                if (params.NOTIFY_EMAIL?.trim()) {
                    emailext(
                        to: params.NOTIFY_EMAIL.trim(),
                        subject: "TaskFlow ${currentBuild.currentResult}: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                        body: "Result: ${currentBuild.currentResult}\nBuild: ${env.BUILD_URL}\nImage: ${env.IMAGE_TAG ?: 'not built'}"
                    )
                }
            }
        }
        cleanup {
            // Remove only this build's local image; never prune unrelated images.
            sh 'if [ -n "${IMAGE_TAG:-}" ]; then docker image rm "$IMAGE_TAG" || true; fi'
        }
    }
}
