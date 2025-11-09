#!/bin/bash
# Docker smoke test script
# Task #7 from Phase 2 CTO review

set -e  # Exit on error

echo "========================================================================"
echo "Docker Smoke Test - Voltcast AI"
echo "========================================================================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

IMAGE_NAME="voltcast-api:phase2"
CONTAINER_NAME="voltcast-test"

# Step 1: Build Docker image
echo -e "\n${YELLOW}[1/5] Building Docker image...${NC}"
docker build -t $IMAGE_NAME . || {
    echo -e "${RED}✗ Docker build failed${NC}"
    exit 1
}
echo -e "${GREEN}✓ Docker image built successfully${NC}"

# Step 2: Run verification inside container
echo -e "\n${YELLOW}[2/5] Running verification inside container...${NC}"
docker run --rm \
    -v "$(pwd)/artifacts:/app/artifacts" \
    $IMAGE_NAME \
    python scripts/verify_run.py --golden artifacts/golden_samples.json || {
    echo -e "${RED}✗ Verification failed inside container${NC}"
    exit 1
}
echo -e "${GREEN}✓ Verification passed inside container${NC}"

# Step 3: Start container
echo -e "\n${YELLOW}[3/5] Starting API container...${NC}"
docker run -d \
    --name $CONTAINER_NAME \
    -p 8000:8000 \
    -v "$(pwd)/artifacts:/app/artifacts" \
    -v "$(pwd)/demand_forecast.db:/app/demand_forecast.db" \
    -e DATABASE_URL="sqlite:///./demand_forecast.db" \
    $IMAGE_NAME || {
    echo -e "${RED}✗ Failed to start container${NC}"
    exit 1
}

# Wait for container to be ready
echo "Waiting for API to be ready..."
sleep 10

# Step 4: Test health endpoint
echo -e "\n${YELLOW}[4/5] Testing health endpoint...${NC}"
HEALTH_RESPONSE=$(docker exec $CONTAINER_NAME curl -s http://localhost:8000/api/v1/health)
if echo "$HEALTH_RESPONSE" | grep -q "healthy"; then
    echo -e "${GREEN}✓ Health check passed${NC}"
    echo "Response: $HEALTH_RESPONSE"
else
    echo -e "${RED}✗ Health check failed${NC}"
    echo "Response: $HEALTH_RESPONSE"
    docker logs $CONTAINER_NAME
    docker stop $CONTAINER_NAME
    docker rm $CONTAINER_NAME
    exit 1
fi

# Step 5: Test status endpoint
echo -e "\n${YELLOW}[5/5] Testing status endpoint...${NC}"
STATUS_RESPONSE=$(docker exec $CONTAINER_NAME curl -s http://localhost:8000/api/v1/status)
if echo "$STATUS_RESPONSE" | grep -q "status"; then
    echo -e "${GREEN}✓ Status endpoint working${NC}"
    echo "Response: $STATUS_RESPONSE"
else
    echo -e "${RED}✗ Status endpoint failed${NC}"
    echo "Response: $STATUS_RESPONSE"
    docker logs $CONTAINER_NAME
    docker stop $CONTAINER_NAME
    docker rm $CONTAINER_NAME
    exit 1
fi

# Cleanup
echo -e "\n${YELLOW}Cleaning up...${NC}"
docker stop $CONTAINER_NAME
docker rm $CONTAINER_NAME

echo -e "\n========================================================================"
echo -e "${GREEN}✅ DOCKER SMOKE TEST PASSED${NC}"
echo -e "========================================================================"
echo ""
echo "Summary:"
echo "  ✓ Docker image built"
echo "  ✓ Verification passed in container"
echo "  ✓ API container started"
echo "  ✓ Health endpoint working"
echo "  ✓ Status endpoint working"
echo ""
echo "To run the container manually:"
echo "  docker run -d -p 8000:8000 --name voltcast $IMAGE_NAME"
echo ""
