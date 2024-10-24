pipeline {
    agent { label 'podman' }

    parameters {
        choice(choices: ['Test'],
               description: 'Run Tests',
               name: 'buildChoice')

        booleanParam(name: 'PUBLISH_DOCUMENTATION', defaultValue: false, description: 'Publishes the generated documentation')
    }

    options {
        disableConcurrentBuilds()
        buildDiscarder(logRotator(artifactDaysToKeepStr: '7', artifactNumToKeepStr: '1', daysToKeepStr: '45', numToKeepStr: '10'))
        timeout(time: 1, unit: 'HOURS')
        gitLabConnection('CollabGitLab')
    }

    environment {
        PATH = "$workspace/.venv-mchbuild/bin:$HOME/tools/openshift-client-tools:$HOME/tools/trivy:$PATH"
        HTTP_PROXY = 'http://proxy.meteoswiss.ch:8080'
        HTTPS_PROXY = 'http://proxy.meteoswiss.ch:8080'
    }

    stages {
        stage('Preflight') {
            steps {
                updateGitlabCommitStatus name: 'Test', state: 'running'

                script {
                    sh '''
                    # Ensure pyenv is initialized
                    eval "$(pyenv init --path)"
                    eval "$(pyenv init -)"
                    eval "$(pyenv virtualenv-init -)"
                    '''

                    echo '---- INSTALL PYTHON 3.12 ----'
                    sh '''
                    # Install Python 3.12 using pyenv
                    pyenv install 3.12.0
                    '''

                    echo '---- SETUP PYTHON 3.12 LOCALLY ----'
                    sh '''
                    # Create a local Python version file to specify the version for this project
                    echo "3.12.0" > .python-version

                    # Create a virtual environment with Python 3.12
                    pyenv virtualenv 3.12.0 venv-3.12

                    # Activate the virtual environment
                    pyenv activate venv-3.12

                    '''
                    echo '---- INSTALL POETRY ----'
                    sh '''
                    # Install Poetry if not already installed
                    curl -sSL https://install.python-poetry.org | python3 - --yes
                    '''

                    echo '---- INSTALL DEPENDENCIES ----'
                    sh '''
                    # Install the project dependencies defined in pyproject.toml
                    poetry install
                    '''
                }
            }
        }

        stage('Test') {
            when { expression { Globals.runTests } }
            steps {
                echo '---- RUNNING PYTEST ----'
                sh '''
                # Run tests using Poetry
                poetry run pytest --junitxml=test_reports/junit.xml
                '''
            }
            post {
                always {
                    junit keepLongStdio: true, testResults: 'test_reports/junit.xml'
                }
            }
        }

        stage('Lint & Type Check') {
            when { expression { Globals.runTests } }
            steps {
                echo '---- LINT & TYPE CHECK ----'
                sh '''
                # Run linting and type checking using Poetry
                poetry run mchbuild test.lint
                '''
            }
            post {
                always {
                    script {
                        recordIssues(qualityGates: [[threshold: 10, type: 'TOTAL', unstable: false]], tools: [myPy(pattern: 'test_reports/mypy.log')])
                    }
                }
            }
        }

        stage('SonarQube Analysis') {
            when { expression { Globals.runTests } }
            steps {
                echo "---- SONARQUBE ANALYSIS ----"
                withSonarQubeEnv("Sonarqube-PROD") {
                    sh "sed -i 's/\\/src\\/app-root/.\\//g' test_reports/coverage.xml"
                    sh "poetry run ${SCANNER_HOME}/bin/sonar-scanner"
                }

                echo "---- SONARQUBE QUALITY GATE ----"
                timeout(time: 1, unit: 'HOURS') {
                    waitForQualityGate abortPipeline: false
                }
            }
        }
    }

    post {
        cleanup {
            sh '''
            # Clean up using mchbuild
            poetry run mchbuild clean
            '''
        }
        aborted {
            updateGitlabCommitStatus name: 'Test', state: 'canceled'
        }
        failure {
            updateGitlabCommitStatus name: 'Test', state: 'failed'
            emailext(subject: "${currentBuild.fullDisplayName}: ${currentBuild.currentResult}",
                     attachLog: true,
                     body: "Job '${env.JOB_NAME} #${env.BUILD_NUMBER}': ${env.BUILD_URL}",
                     recipientProviders: [requestor(), developers()])
        }
        success {
            echo 'Tests succeeded'
            updateGitlabCommitStatus name: 'Test', state: 'success'
        }
    }
}

