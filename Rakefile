task default: %w[deploy]


desc "Deploys Architecture and launches all services and daemons needed to properly work"
task :deploy => [
	:cleaning_environment_task,
	:start,
	:status] do
    puts "Deploying services..."
end

desc "UnDeploy Architecture"
task :undeploy => [:status] do 
	puts "Undeploy Services"
	puts `docker-compose down -v 2>&1`
end

desc "Start Containers"
task :start => [ :check_docker_task, :login, :check_deployment_file_task ] do 
	puts "Start Containers"
	puts `docker-compose up -d --remove-orphans`
end 

desc "Stop Containers"
task :stop => [ :check_docker_task ] do
	puts "Stop Containers"
	puts `docker-compose stop 2>&1`
	puts `docker-compose rm -f 2>&1`
end


desc "Status Containers"
task :status do 
	puts "Show Containers Status"
	puts `docker-compose ps 2>&1`
end


desc "Cleaning Evironment Task"
task :cleaning_environment_task do 
	puts "Cleaning Environment"
	puts `docker image prune -af`
	puts `docker volume prune -f 2>&1`
end


desc "Check Docker and Docker Compose Task"
task :check_docker_task do
	puts "Check Docker and Docker Compose ..."
	if which('docker') && which('docker-compose')
		show_docker_version
		show_docker_compose_version
	else
		raise "Please check that Docker and Docker Compose are visible and accessible in the PATH"
	end
end


desc "Authenticating with existing credentials"
task :login do
	puts `docker login 2>&1`
end

desc "Check Deployment File"
task :check_deployment_file_task do
	puts "Check Deployment File ..."
    raise "Deployment file not found, please check availability" unless File.file?("docker-compose.yml")
    puts "Deployment File OK"
end



## Utils Functions

def show_docker_version
  puts `docker version 2>&1`
end

def show_docker_compose_version
  puts `docker-compose version 2>&1`
end

# Cross-platform way of finding an executable in the $PATH.
# which('ruby') #=> /usr/bin/ruby
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