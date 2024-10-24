class Globals {
    static boolean runTests = true  // new variable to run tests

    // remove unused variables related to build, deploy, etc.
}

pipeline {
    agent { label 'podman' }

    parameters {
        choice(
            choices: ['Test'],  // Only keep Test option
            description: 'Run Tests',
            name: 'buildChoice'  // Name for the choice parameter
        )
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
        SCANNER_HOME = tool name: 'Sonarqube-certs-PROD', type: 'hudson.plugins.sonar.SonarRunnerInstallation'
    }

    stages {
        stage('Preflight') {
            steps {
                updateGitlabCommitStatus name: 'Test', state: 'running'

                script {
                    echo '---- INSTALL MCHBUILD ----'
                    sh '''
                    python -m venv .venv-mchbuild
                    PIP_INDEX_URL=https://hub.meteoswiss.ch/nexus/repository/python-all/simple \
                      .venv-mchbuild/bin/pip install --upgrade mchbuild pytest
                    '''

                    echo '---- INITIALIZE PARAMETERS ----'
                    Globals.runTests = params.buildChoice == 'Test'
                }
            }
        }

        stage('Test') {
            when { expression { Globals.runTests } }
            steps {
                echo '---- RUNNING PYTEST ----'
                sh '''
                .venv-mchbuild/bin/pytest --junitxml=test_reports/junit.xml
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
                .venv-mchbuild/bin/mchbuild test.lint
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
                    sh "${SCANNER_HOME}/bin/sonar-scanner"
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
            mchbuild clean
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
