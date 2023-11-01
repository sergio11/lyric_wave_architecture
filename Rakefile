# Rakefile for deploying and managing your environment

# Define the default task when running "rake" without arguments
task default: %w[deploy]

# Deploy task: Deploys Architecture and launches services and daemons.
desc "Deploys Architecture and launches all services and daemons needed to work properly."
task :deploy => [
    :clean_environment,
    :start,
    :status
] do
    puts "Deploying services..."
end

# Undeploy task: Undeploys Architecture
desc "Undeploys Architecture"
task :undeploy => [:status] do 
    puts "Undeploy Services"
    puts `docker-compose down -v 2>&1`
end

# Start task: Start Containers
desc "Start Containers"
task :start => [ :check_docker, :login, :check_deployment_file ] do 
    puts "Start Containers"
    puts `docker-compose up -d --remove-orphans`
end 

# Stop task: Stop Containers
desc "Stop Containers"
task :stop => [ :check_docker ] do
    puts "Stop Containers"
    puts `docker-compose stop 2>&1`
    puts `docker-compose rm -f 2>&1`
end

# Status task: Show Containers Status
desc "Show Containers Status"
task :status do 
    puts "Show Containers Status"
    puts `docker-compose ps 2>&1`
end

# Build and push Apache Airflow Docker image
desc "Build and push Apache Airflow Docker image"
task :build_and_push_airflow_image do
  image_name = "ssanchez11/lyric_wave_apache_airflow:0.0.1"
  puts "Building Apache Airflow Docker image..."
  build_command = "docker build -t #{image_name} ./airflow"
  system(build_command)
  puts "Pushing Apache Airflow Docker image to DockerHub..."
  push_command = "docker push #{image_name}"
  system(push_command)
  puts "Apache Airflow image built and pushed successfully."
end

# Build and push LyricWave API Docker image
desc "Build and push LyricWave API Docker image"
task :build_and_push_api_image do
  api_image_name = "ssanchez11/lyric_wave_api:0.0.1"
  api_directory = "./api"
  puts "Building Flask API Docker image..."
  build_command = "docker build -t #{api_image_name} #{api_directory}"
  system(build_command)
  puts "Pushing Flask API Docker image to DockerHub..."
  push_command = "docker push #{api_image_name}"
  system(push_command)
  puts "Flask API image built and pushed successfully."
end

# Cleaning Environment task
desc "Cleaning Environment task"
task :clean_environment do 
    puts "Cleaning Environment"
    puts `docker image prune -af`
    puts `docker volume prune -f 2>&1`
end

# Check Docker and Docker Compose task
desc "Check Docker and Docker Compose task"
task :check_docker do
    puts "Check Docker and Docker Compose ..."
    if which('docker') && which('docker-compose')
        show_docker_version
        show_docker_compose_version
    else
        raise "Please check that Docker and Docker Compose are visible and accessible in the PATH"
    end
end

# Authenticating with existing credentials task
desc "Authenticating with existing credentials task"
task :login do
    puts `docker login 2>&1`
end

# Check Deployment File task
desc "Check Deployment File task"
task :check_deployment_file do
    puts "Check Deployment File ..."
    raise "Deployment file not found, please check availability" unless File.file?("docker-compose.yml")
    puts "Deployment File OK"
end

# MinIO Cluster namespace
namespace :minio do
  # Check MinIO Cluster Deployment File
  desc "Check MinIO Cluster Deployment File"
  task :check_deployment_file do
    puts "Check MinIO Cluster Deployment File ..."
    raise "Deployment file not found, please check availability" unless File.file?("./lyric_wave_minio_cluster/docker-compose.yml")
    puts "Platform Deployment File OK!"
  end

  # Start MinIO Cluster Containers
  desc "Start MinIO Cluster Containers"
  task :start => [ :check_docker, :login, :check_deployment_file ] do 
    puts "Start Cluster Containers"
    puts `docker-compose -f ./lyric_wave_minio_cluster/docker-compose.yml up -d`
  end 

  # Stop MinIO Cluster Containers
  desc "Stop MinIO Cluster Containers"
  task :stop => [ :check_docker, :login, :check_deployment_file ] do
    puts "Stop Cluster Containers"
    puts `docker-compose -f ./lyric_wave_minio_cluster/docker-compose.yml stop 2>&1`
  end
end

# Utility functions

def show_docker_version
    puts `docker version 2>&1`
end

def show_docker_compose_version
    puts `docker-compose version 2>&1`
end

# Cross-platform way of finding an executable in the $PATH.
def which(cmd)
    exts = ENV['PATHEXT'] ? ENV['PATHEXT'].split(';') : ['']
    ENV['PATH'].split(File::PATH_SEPARATOR).each do |path|
        exts.each { |ext|
            exe = File.join(path, "#{cmd}#{ext}")
            return exe if File.executable?(exe) && !File.directory?(exe)
        }
    end
    return nil
end
