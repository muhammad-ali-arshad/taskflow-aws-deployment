pipeline {
    // Run on the online controller node; Docker Pipeline uses its configured daemon.
    agent any

    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
        timeout(time: 20, unit: 'MINUTES')
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    triggers { githubPush() }

    parameters {
        string(name: 'NOTIFY_EMAIL', defaultValue: '',
               description: 'Optional: your email address. Configure SMTP before enabling.')
    }

    environment {
        PYTHONDONTWRITEBYTECODE = '1'
        PART2_CODE_DIR = '/var/lib/jenkins/taskflow-part2-code'
        PART2_ENV_FILE = '/etc/taskflow-part2.env'
        PART2_COMPOSE_FILE = 'docker-compose.part2.yml'
    }

    stages {
        stage('Checkout from GitHub') {
            steps {
                deleteDir()
                checkout scm
                script {
                    def commitId = sh(script: 'git rev-parse --short=12 HEAD', returnStdout: true).trim()
                    env.IMAGE_TAG = "taskflow-ci:${env.BUILD_NUMBER}-${commitId}"
                }
            }
        }

        stage('Test inside Docker') {
            steps {
                script {
                    def uid = sh(script: 'id -u', returnStdout: true).trim()
                    def gid = sh(script: 'id -g', returnStdout: true).trim()
                    sh 'mkdir -p reports'
                    docker.image('python:3.12-slim').withRun(
                        "-t --user ${uid}:${gid} --env PYTHONDONTWRITEBYTECODE=1 -v ${env.WORKSPACE}:/workspace:rw,z -w /workspace",
                        'cat'
                    ) { testContainer ->
                        def testStatus = sh(
                            script: "docker exec ${testContainer.id} sh -lc 'set -eu; python -m venv /tmp/taskflow-ci-venv; /tmp/taskflow-ci-venv/bin/python -m pip install --no-cache-dir -r requirements-dev.txt; /tmp/taskflow-ci-venv/bin/python -m pytest -q -p no:cacheprovider --junitxml=/tmp/pytest.xml'",
                            returnStatus: true
                        )
                        def reportStatus = sh(
                            script: "docker cp ${testContainer.id}:/tmp/pytest.xml reports/pytest.xml",
                            returnStatus: true
                        )
                        if (testStatus != 0) {
                            error("Containerized tests failed with exit code ${testStatus}.")
                        }
                        if (reportStatus != 0) {
                            error('Could not copy the JUnit report out of the test container.')
                        }
                    }
                }
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

        stage('Verify image health') {
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
                            echo 'Application health check passed.'
                            exit 0
                        fi
                        sleep 2
                    done
                    docker logs "$name"
                    exit 1
                '''
            }
        }

        stage('Deploy Part II with Compose') {
            when {
                expression {
                    currentBuild.getBuildCauses('com.cloudbees.jenkins.GitHubPushCause').size() > 0
                }
            }
            steps {
                sh '''
                    set -eu
                    mkdir -p "$PART2_CODE_DIR"
                    find "$PART2_CODE_DIR" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
                    cp "$WORKSPACE/application.py" "$WORKSPACE/config.py" "$WORKSPACE/requirements.txt" "$PART2_CODE_DIR/"
                    cp -a "$WORKSPACE/taskflow" "$PART2_CODE_DIR/taskflow"
                    TASKFLOW_CODE_DIR="$PART2_CODE_DIR" docker compose \
                        --env-file "$PART2_ENV_FILE" \
                        --project-name taskflow-part2 \
                        --file "$WORKSPACE/$PART2_COMPOSE_FILE" \
                        up -d --force-recreate

                    for attempt in $(seq 1 40); do
                        if curl --fail --silent --show-error http://127.0.0.1:8082/health; then
                            echo
                            echo 'Part II application and database are healthy.'
                            exit 0
                        fi
                        sleep 3
                    done

                    docker compose --env-file "$PART2_ENV_FILE" \
                        --project-name taskflow-part2 \
                        --file "$WORKSPACE/$PART2_COMPOSE_FILE" logs --tail=100
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
            sh 'if [ -n "${IMAGE_TAG:-}" ]; then docker image rm "$IMAGE_TAG" || true; fi'
        }
    }
}
