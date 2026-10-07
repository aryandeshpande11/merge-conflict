pipeline {
    agent any

    environment {
        DOCKER_IMAGE = "merge-predictor:1.0"
    }

    stages {
        stage('Checkout') {
            steps {
                echo 'Checking out code from Git repository...'
                checkout scm
            }
        }

        stage('Test API') {
            steps {
                echo 'Running tests on API and model dependencies...'
                sh '''
                    python3 -m py_compile api/app.py
                    echo "API syntax validation successful!"
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                echo 'Building Docker container image...'
                sh "docker build -t ${DOCKER_IMAGE} ."
            }
        }

        stage('Push Docker Image') {
            steps {
                echo 'Pushing Docker image to registry (demonstration)...'
                // In production: docker push yourusername/merge-predictor:1.0
                sh "echo Image ${DOCKER_IMAGE} tagged and ready for deployment"
            }
        }

        stage('Deploy to Kubernetes') {
            steps {
                echo 'Deploying to Kubernetes cluster...'
                sh '''
                    kubectl apply -f k8s/deployment.yaml
                    kubectl apply -f k8s/service.yaml
                    kubectl rollout status deployment/merge-predictor
                '''
            }
        }
    }

    post {
        success {
            echo 'ML Prediction Service pipeline deployed successfully!'
        }
        failure {
            echo 'Pipeline failed. Check stage logs for troubleshooting.'
        }
    }
}
