# Docker smoke test script (PowerShell)
# Task #7 from Phase 2 CTO review

$ErrorActionPreference = "Stop"

Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host "Docker Smoke Test - Voltcast AI" -ForegroundColor Cyan
Write-Host "========================================================================" -ForegroundColor Cyan

$IMAGE_NAME = "voltcast-api:phase2"
$CONTAINER_NAME = "voltcast-test"

# Step 1: Build Docker image
Write-Host "`n[1/5] Building Docker image..." -ForegroundColor Yellow
try {
    docker build -t $IMAGE_NAME .
    Write-Host "✓ Docker image built successfully" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker build failed" -ForegroundColor Red
    exit 1
}

# Step 2: Run verification inside container
Write-Host "`n[2/5] Running verification inside container..." -ForegroundColor Yellow
try {
    docker run --rm `
        -v "${PWD}/artifacts:/app/artifacts" `
        $IMAGE_NAME `
        python scripts/verify_run.py --golden artifacts/golden_samples.json
    Write-Host "✓ Verification passed inside container" -ForegroundColor Green
} catch {
    Write-Host "✗ Verification failed inside container" -ForegroundColor Red
    exit 1
}

# Step 3: Start container
Write-Host "`n[3/5] Starting API container..." -ForegroundColor Yellow
try {
    docker run -d `
        --name $CONTAINER_NAME `
        -p 8000:8000 `
        -v "${PWD}/artifacts:/app/artifacts" `
        -v "${PWD}/demand_forecast.db:/app/demand_forecast.db" `
        -e DATABASE_URL="sqlite:///./demand_forecast.db" `
        $IMAGE_NAME
    
    # Wait for container to be ready
    Write-Host "Waiting for API to be ready..."
    Start-Sleep -Seconds 10
    Write-Host "✓ Container started" -ForegroundColor Green
} catch {
    Write-Host "✗ Failed to start container" -ForegroundColor Red
    exit 1
}

# Step 4: Test health endpoint
Write-Host "`n[4/5] Testing health endpoint..." -ForegroundColor Yellow
try {
    $health = docker exec $CONTAINER_NAME curl -s http://localhost:8000/api/v1/health
    if ($health -match "healthy") {
        Write-Host "✓ Health check passed" -ForegroundColor Green
        Write-Host "Response: $health"
    } else {
        throw "Health check failed"
    }
} catch {
    Write-Host "✗ Health check failed" -ForegroundColor Red
    Write-Host "Response: $health"
    docker logs $CONTAINER_NAME
    docker stop $CONTAINER_NAME
    docker rm $CONTAINER_NAME
    exit 1
}

# Step 5: Test status endpoint
Write-Host "`n[5/5] Testing status endpoint..." -ForegroundColor Yellow
try {
    $status = docker exec $CONTAINER_NAME curl -s http://localhost:8000/api/v1/status
    if ($status -match "status") {
        Write-Host "✓ Status endpoint working" -ForegroundColor Green
        Write-Host "Response: $status"
    } else {
        throw "Status endpoint failed"
    }
} catch {
    Write-Host "✗ Status endpoint failed" -ForegroundColor Red
    Write-Host "Response: $status"
    docker logs $CONTAINER_NAME
    docker stop $CONTAINER_NAME
    docker rm $CONTAINER_NAME
    exit 1
}

# Cleanup
Write-Host "`nCleaning up..." -ForegroundColor Yellow
docker stop $CONTAINER_NAME
docker rm $CONTAINER_NAME

Write-Host "`n========================================================================" -ForegroundColor Cyan
Write-Host "✅ DOCKER SMOKE TEST PASSED" -ForegroundColor Green
Write-Host "========================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Summary:"
Write-Host "  ✓ Docker image built"
Write-Host "  ✓ Verification passed in container"
Write-Host "  ✓ API container started"
Write-Host "  ✓ Health endpoint working"
Write-Host "  ✓ Status endpoint working"
Write-Host ""
Write-Host "To run the container manually:"
Write-Host "  docker run -d -p 8000:8000 --name voltcast $IMAGE_NAME"
Write-Host ""
