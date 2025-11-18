# Start Redis using Docker
# This is the easiest way to run Redis on Windows

Write-Host "Starting Redis using Docker..." -ForegroundColor Green

# Check if Docker is running
$dockerRunning = docker ps 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Check if Redis container already exists
$existingContainer = docker ps -a --filter "name=voltcast-redis" --format "{{.Names}}"

if ($existingContainer -eq "voltcast-redis") {
    Write-Host "Redis container exists. Starting it..." -ForegroundColor Yellow
    docker start voltcast-redis
} else {
    Write-Host "Creating new Redis container..." -ForegroundColor Yellow
    docker run -d `
        --name voltcast-redis `
        -p 6379:6379 `
        redis:alpine
}

# Wait a moment for Redis to start
Start-Sleep -Seconds 2

# Test connection
Write-Host "`nTesting Redis connection..." -ForegroundColor Green
docker exec voltcast-redis redis-cli ping

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n[OK] Redis is running on localhost:6379" -ForegroundColor Green
    Write-Host "`nSet this in your .env file:" -ForegroundColor Cyan
    Write-Host "REDIS_URL=redis://localhost:6379" -ForegroundColor White
} else {
    Write-Host "`n[ERROR] Redis failed to start" -ForegroundColor Red
}
