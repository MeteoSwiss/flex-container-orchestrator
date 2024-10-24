class Globals {
    // the library version
    static String version = 'latest'

    // the tag used when publishing documentation
    static String documentationTag = 'latest'
}

String rebuild_cron = env.BRANCH_NAME == "main" ? "@midnight" : ""

pipeline {
    agent {label 'podman'}

    triggers { cron(rebuild_cron) }

    parameters {
        booleanParam(name: 'RELEASE_BUILD', defaultValue: false, description: 'Creates and publishes a new release')
        string(name: 'version', description: '(Optional) The release version, must follow semantic versioning (e.g. v1.0.0). If not given, then the version will be the next one base on the latest TAG.')
        booleanParam(name: 'PUBLISH_DOCUMENTATION', defaultValue: false, description: 'Publishes the generated documentation')
    }

    environment {
        PATH = "$workspace/.venv-mchbuild/bin:$HOME/tools/openshift-client-tools:$PATH"
        HTTP_PROXY = 'http://proxy.meteoswiss.ch:8080'
        HTTPS_PROXY = 'http://proxy.meteoswiss.ch:8080'
        NO_PROXY = '.meteoswiss.ch,localhost'
    }

    options {
        gitLabConnection('CollabGitLab')

        // New jobs should wait until older jobs are finished
        disableConcurrentBuilds()
        // Discard old builds
        buildDiscarder(logRotator(artifactDaysToKeepStr: '7', artifactNumToKeepStr: '1', daysToKeepStr: '45', numToKeepStr: '10'))
        // Timeout the pipeline build after 1 hour
        timeout(time: 1, unit: 'HOURS')
    }

    stages {
        stage('Init') {
            steps {
                updateGitlabCommitStatus name: 'Build', state: 'running'
                script {
                    echo '---- INSTALL MCHBUILD ----'
                    sh '''
                    python -m venv .venv-mchbuild
                    PIP_INDEX_URL=https://hub.meteoswiss.ch/nexus/repository/python-all/simple \
                      .venv-mchbuild/bin/pip install --upgrade mchbuild
                    '''
                    if (params.RELEASE_BUILD) {
                        echo '---- TAGGING RELEASE ----'
                        sh 'mchbuild deploy.addNextTag'
                    }
                    Globals.documentationTag = env.BRANCH_NAME
                }
            }
        }

        stage('Test') {
            steps {
                sh 'mchbuild -s pythonImageName=3.12  build test.unit'
            }
            post {
                always {
                    junit keepLongStdio: true, testResults: 'test_reports/junit*.xml'
                }
            }
        }

        stage('Integration test') {
            steps {
                sh 'mchbuild test.integration'
            }
        }

        stage('Publish Documentation') {
            steps {
                withCredentials([string(credentialsId: 'documentation-main-prod-token',
                                        variable: 'DOC_TOKEN')]) {
                    sh """
                    mchbuild -s pythonImageName=3.12 -s deploymentEnvironment=prod \
                      -s docVersion=${Globals.documentationTag} deploy.docs
                    """
                }
            }
        }
    }

    post {
        aborted {
            updateGitlabCommitStatus name: 'Build', state: 'canceled'
        }
        failure {
            updateGitlabCommitStatus name: 'Build', state: 'failed'
            echo 'Sending email'
            script {
                emailext(subject: "${currentBuild.fullDisplayName}: ${currentBuild.currentResult}",
                    attachLog: true,
                    attachmentsPattern: 'generatedFile.txt',
                    // TODO replace direct e-mails once a python e-mail list is available
                    to: env.BRANCH_NAME == 'main' ? 'nestor.tarinburriel@meteoswiss.ch,peter.kroiss@meteoswiss.ch' : '',
                    body: "Job '${env.JOB_NAME} #${env.BUILD_NUMBER}': ${env.BUILD_URL}",
                    recipientProviders: [requestor(), developers()])
            }
        }
        success {
            echo 'Build succeeded'
            updateGitlabCommitStatus name: 'Build', state: 'success'
        }
    }
}

