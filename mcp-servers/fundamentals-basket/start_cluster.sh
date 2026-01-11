#!/bin/bash
#
# Financials Basket Cluster Startup Script
#
# Starts 3 instances of the HTTP server behind nginx load balancer.
#
# Usage:
#   ./start_cluster.sh         # Start cluster
#   ./start_cluster.sh stop    # Stop cluster
#   ./start_cluster.sh status  # Check status
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Configuration
PORTS=(8001 8002 8003)
NGINX_PORT=8080
PID_DIR="/tmp/financials-cluster"
LOG_DIR="/tmp/financials-cluster/logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create directories
mkdir -p "$PID_DIR" "$LOG_DIR"

start_instance() {
    local port=$1
    local instance_id="financials-$port"
    local pid_file="$PID_DIR/$instance_id.pid"
    local log_file="$LOG_DIR/$instance_id.log"

    if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
        echo -e "${YELLOW}Instance $instance_id already running (PID: $(cat "$pid_file"))${NC}"
        return 0
    fi

    echo -e "${GREEN}Starting $instance_id on port $port...${NC}"

    INSTANCE_ID="$instance_id" \
    HTTP_PORT="$port" \
    nohup python3 -m uvicorn http_server:app \
        --host 0.0.0.0 \
        --port "$port" \
        --log-level info \
        > "$log_file" 2>&1 &

    echo $! > "$pid_file"
    echo -e "${GREEN}  Started (PID: $!)${NC}"
}

stop_instance() {
    local port=$1
    local instance_id="financials-$port"
    local pid_file="$PID_DIR/$instance_id.pid"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${YELLOW}Stopping $instance_id (PID: $pid)...${NC}"
            kill "$pid" 2>/dev/null || true
            rm -f "$pid_file"
        else
            echo -e "${RED}$instance_id not running (stale PID file)${NC}"
            rm -f "$pid_file"
        fi
    else
        echo -e "${RED}$instance_id not running (no PID file)${NC}"
    fi
}

start_nginx() {
    local pid_file="$PID_DIR/nginx.pid"

    if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
        echo -e "${YELLOW}nginx already running (PID: $(cat "$pid_file"))${NC}"
        return 0
    fi

    echo -e "${GREEN}Starting nginx load balancer on port $NGINX_PORT...${NC}"

    # Check if nginx is available
    if ! command -v nginx &> /dev/null; then
        echo -e "${RED}nginx not found. Please install nginx.${NC}"
        echo -e "${YELLOW}You can still access instances directly on ports: ${PORTS[*]}${NC}"
        return 1
    fi

    # Start nginx with our config
    nginx -c "$SCRIPT_DIR/nginx.conf" -g "pid $pid_file;"
    echo -e "${GREEN}  Started nginx${NC}"
}

stop_nginx() {
    local pid_file="$PID_DIR/nginx.pid"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${YELLOW}Stopping nginx (PID: $pid)...${NC}"
            kill "$pid" 2>/dev/null || true
            rm -f "$pid_file"
        else
            rm -f "$pid_file"
        fi
    fi
}

check_status() {
    echo -e "\n${GREEN}=== Financials Cluster Status ===${NC}\n"

    # Check instances
    for port in "${PORTS[@]}"; do
        local instance_id="financials-$port"
        local pid_file="$PID_DIR/$instance_id.pid"

        if [ -f "$pid_file" ] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
            # Check if responding
            if curl -s "http://127.0.0.1:$port/health" > /dev/null 2>&1; then
                echo -e "${GREEN}[OK]${NC} $instance_id (port $port) - responding"
            else
                echo -e "${YELLOW}[STARTING]${NC} $instance_id (port $port) - process running, not responding yet"
            fi
        else
            echo -e "${RED}[DOWN]${NC} $instance_id (port $port)"
        fi
    done

    # Check nginx
    local nginx_pid_file="$PID_DIR/nginx.pid"
    if [ -f "$nginx_pid_file" ] && kill -0 "$(cat "$nginx_pid_file")" 2>/dev/null; then
        if curl -s "http://127.0.0.1:$NGINX_PORT/health" > /dev/null 2>&1; then
            echo -e "${GREEN}[OK]${NC} nginx (port $NGINX_PORT) - load balancer responding"
        else
            echo -e "${YELLOW}[STARTING]${NC} nginx (port $NGINX_PORT) - process running"
        fi
    else
        echo -e "${RED}[DOWN]${NC} nginx (port $NGINX_PORT)"
    fi

    echo ""
}

wait_for_ready() {
    echo -e "\n${YELLOW}Waiting for instances to be ready...${NC}"

    local max_wait=30
    local wait_time=0

    while [ $wait_time -lt $max_wait ]; do
        local ready=0
        for port in "${PORTS[@]}"; do
            if curl -s "http://127.0.0.1:$port/health" > /dev/null 2>&1; then
                ((ready++))
            fi
        done

        if [ $ready -eq ${#PORTS[@]} ]; then
            echo -e "${GREEN}All instances ready!${NC}"
            return 0
        fi

        echo -e "  $ready/${#PORTS[@]} instances ready..."
        sleep 2
        ((wait_time+=2))
    done

    echo -e "${YELLOW}Timeout waiting for all instances (some may still be starting)${NC}"
}

start_cluster() {
    echo -e "\n${GREEN}=== Starting Financials Cluster ===${NC}\n"

    # Start instances
    for port in "${PORTS[@]}"; do
        start_instance "$port"
    done

    # Wait for instances to be ready
    wait_for_ready

    # Start nginx
    start_nginx

    echo -e "\n${GREEN}=== Cluster Started ===${NC}"
    echo -e "Load balancer: http://127.0.0.1:$NGINX_PORT"
    echo -e "Instances: ${PORTS[*]}"
    echo ""
}

stop_cluster() {
    echo -e "\n${YELLOW}=== Stopping Financials Cluster ===${NC}\n"

    # Stop nginx first
    stop_nginx

    # Stop instances
    for port in "${PORTS[@]}"; do
        stop_instance "$port"
    done

    echo -e "\n${GREEN}Cluster stopped${NC}\n"
}

# Main
case "${1:-start}" in
    start)
        start_cluster
        ;;
    stop)
        stop_cluster
        ;;
    restart)
        stop_cluster
        sleep 2
        start_cluster
        ;;
    status)
        check_status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
