pipeline {
    agent any

    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
        timeout(time: 10, unit: 'MINUTES')
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    triggers { githubPush() }

    environment {
        PART2_CODE_DIR = '/var/lib/jenkins/taskflow-part2-code'
        PART2_ENV_FILE = '/etc/taskflow-part2.env'
        PART2_COMPOSE_FILE = 'docker-compose.part2.yml'
    }

    stages {
        stage('Checkout from GitHub') {
            steps {
                checkout scm
                sh 'git log -1 --format="Commit: %h | Author: %an <%ae>"'
            }
        }

        stage('Validate in Docker') {
            steps {
                script {
                    docker.image('python:3.12-slim').inside {
                        sh 'python -m pip install --no-cache-dir -r requirements.txt'
                        sh 'python -m compileall -q application.py config.py taskflow'
                    }
                }
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
                    TASKFLOW_CODE_DIR="$PART2_CODE_DIR" docker compose \\
                        --env-file "$PART2_ENV_FILE" \\
                        --project-name taskflow-part2 \\
                        --file "$WORKSPACE/$PART2_COMPOSE_FILE" \\
                        up -d --force-recreate

                    for attempt in $(seq 1 40); do
                        if curl --fail --silent --show-error http://127.0.0.1:8082/health; then
                            echo
                            echo 'Part II application and database are healthy.'
                            exit 0
                        fi
                        sleep 3
                    done

                    docker compose --env-file "$PART2_ENV_FILE" \\
                        --project-name taskflow-part2 \\
                        --file "$WORKSPACE/$PART2_COMPOSE_FILE" logs --tail=100
                    exit 1
                '''
            }
        }
    }

    post {
        always {
            emailext(
                recipientProviders: [[$class: 'DevelopersRecipientProvider']],
                subject: "TaskFlow ${currentBuild.currentResult}: ${env.JOB_NAME} #${env.BUILD_NUMBER}",
                body: "Result: ${currentBuild.currentResult}\nBuild: ${env.BUILD_URL}\nCommit: ${env.GIT_COMMIT ?: 'unknown'}"
            )
        }
    }
}
