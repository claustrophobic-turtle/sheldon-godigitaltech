pipeline {
    agent any

    environment {
        AWS_REGION = 'us-east-1'
        ECR_REPO = '${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${PROJECT_NAME}'
        PROJECT_NAME = 'etl-project'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    docker.build("${ECR_REPO}:${BUILD_NUMBER}")
                }
            }
        }

        stage('Push to ECR') {
            steps {
                script {
                    sh """
                        aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com
                        docker push ${ECR_REPO}:${BUILD_NUMBER}
                    """
                }
            }
        }

        stage('Deploy Infrastructure') {
            steps {
                dir('terraform') {
                    sh """
                        terraform init
                        terraform plan
                        terraform apply -auto-approve
                    """
                }
            }
        }

        stage('Update Lambda') {
            steps {
                script {
                    sh """
                        aws lambda update-function-code \
                            --function-name ${PROJECT_NAME}-dev-etl \
                            --image-uri ${ECR_REPO}:${BUILD_NUMBER}
                    """
                }
            }
        }
    }
}